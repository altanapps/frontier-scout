"""V0 web app — single test user, reads from existing frontier.db.

Run:
    .venv/bin/flask --app web.app run --debug --port 5050
"""

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, jsonify

from frontier_scout import db, extract


DB_PATH = Path(__file__).resolve().parent.parent / "frontier.db"
TEST_USER_ID = 1


def _ensure_user_tables(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS user_actions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        paper_id INTEGER,
        person_id INTEGER,
        kind TEXT NOT NULL,
        body TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, paper_id, kind),
        UNIQUE(user_id, person_id, kind)
    );
    CREATE TABLE IF NOT EXISTS drafts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        paper_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)


app = Flask(__name__)


@app.route("/")
def dashboard():
    with db.connect(DB_PATH) as con:
        _ensure_user_tables(con)
        hidden = {
            r["paper_id"]
            for r in con.execute(
                "SELECT paper_id FROM user_actions WHERE user_id = ? AND kind = 'hidden'",
                (TEST_USER_ID,),
            ).fetchall()
        }
        sent = {
            r["paper_id"]
            for r in con.execute(
                "SELECT paper_id FROM user_actions WHERE user_id = ? AND kind = 'sent'",
                (TEST_USER_ID,),
            ).fetchall()
        }
        saved = {
            r["paper_id"]
            for r in con.execute(
                "SELECT paper_id FROM user_actions WHERE user_id = ? AND kind = 'saved'",
                (TEST_USER_ID,),
            ).fetchall()
        }
        rows = con.execute(
            "SELECT * FROM papers ORDER BY published DESC LIMIT 200"
        ).fetchall()
        papers_by_lab = defaultdict(list)
        for r in rows:
            if r["id"] in hidden:
                continue
            d = dict(r)
            d["is_saved"] = r["id"] in saved
            d["is_sent"] = r["id"] in sent
            papers_by_lab[r["matched_lab"] or "Unattributed"].append(d)

        people_count = con.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        labs_count = con.execute("SELECT COUNT(DISTINCT lab) FROM people").fetchone()[0]
        signals = con.execute(
            "SELECT * FROM signals ORDER BY observed_at DESC LIMIT 20"
        ).fetchall()

    return render_template(
        "dashboard.html",
        papers_by_lab=dict(sorted(papers_by_lab.items())),
        people_count=people_count,
        labs_count=labs_count,
        signals=[dict(s) for s in signals],
        today=datetime.now(timezone.utc).strftime("%A %d %B %Y"),
    )


@app.route("/papers")
def papers_index():
    from datetime import timedelta
    since = request.args.get("since", "30d")
    lab_filter = request.args.get("lab", "").strip()
    status = request.args.get("status", "active")

    if since == "all":
        cutoff = "0000-00-00"
    else:
        try:
            n = int(since[:-1])
            unit = since[-1]
            delta = timedelta(days=n) if unit == "d" else timedelta(hours=n)
            cutoff = (datetime.now(timezone.utc) - delta).isoformat()
        except (ValueError, IndexError):
            cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    with db.connect(DB_PATH) as con:
        _ensure_user_tables(con)
        actions = {
            r["paper_id"]: r["kind"]
            for r in con.execute(
                "SELECT paper_id, kind FROM user_actions WHERE user_id = ?",
                (TEST_USER_ID,),
            ).fetchall()
        }
        sql = "SELECT * FROM papers WHERE published >= ?"
        args: list = [cutoff]
        if lab_filter:
            sql += " AND matched_lab = ?"
            args.append(lab_filter)
        sql += " ORDER BY published DESC LIMIT 500"
        rows = [dict(r) for r in con.execute(sql, args).fetchall()]
        for r in rows:
            r["action"] = actions.get(r["id"])
        if status == "active":
            rows = [r for r in rows if r["action"] not in ("hidden", "sent")]
        elif status in ("saved", "sent", "hidden"):
            rows = [r for r in rows if r["action"] == status]
        labs = [
            r["matched_lab"] for r in con.execute(
                "SELECT DISTINCT matched_lab FROM papers WHERE matched_lab IS NOT NULL ORDER BY matched_lab"
            ).fetchall()
        ]

    return render_template(
        "papers.html",
        papers=rows, labs=labs,
        since=since, lab_filter=lab_filter, status=status,
    )


@app.route("/papers/<int:paper_id>")
def paper_detail(paper_id: int):
    with db.connect(DB_PATH) as con:
        _ensure_user_tables(con)
        paper = con.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if not paper:
            return "Not found", 404
        action_row = con.execute(
            "SELECT kind FROM user_actions WHERE user_id = ? AND paper_id = ?",
            (TEST_USER_ID, paper_id),
        ).fetchone()
        drafts = con.execute(
            "SELECT * FROM drafts WHERE paper_id = ? ORDER BY created_at DESC",
            (paper_id,),
        ).fetchall()
        person = con.execute(
            "SELECT * FROM people WHERE name = ? AND lab = ?",
            (paper["matched_person"], paper["matched_lab"]),
        ).fetchone()
    return render_template(
        "paper.html",
        paper=dict(paper),
        action=action_row["kind"] if action_row else None,
        drafts=[dict(d) for d in drafts],
        person=dict(person) if person else None,
    )


@app.route("/labs")
def labs_index():
    with db.connect(DB_PATH) as con:
        rows = con.execute("""
            SELECT
                p.lab,
                COUNT(DISTINCT p.id) AS people_count,
                (SELECT COUNT(*) FROM papers WHERE matched_lab = p.lab) AS paper_count,
                (SELECT MAX(published) FROM papers WHERE matched_lab = p.lab) AS last_paper
            FROM people p
            GROUP BY p.lab
            ORDER BY p.lab
        """).fetchall()
    return render_template("labs.html", labs=[dict(r) for r in rows])


@app.route("/labs/<path:lab_name>")
def lab_detail(lab_name: str):
    with db.connect(DB_PATH) as con:
        people_rows = con.execute(
            "SELECT * FROM people WHERE lab = ? ORDER BY name", (lab_name,)
        ).fetchall()
        if not people_rows:
            return "Lab not found", 404
        papers_rows = con.execute(
            "SELECT * FROM papers WHERE matched_lab = ? ORDER BY published DESC LIMIT 50",
            (lab_name,),
        ).fetchall()
    return render_template(
        "lab.html",
        lab_name=lab_name,
        people=[dict(p) for p in people_rows],
        papers=[dict(p) for p in papers_rows],
    )


@app.route("/people")
def people_list():
    q = request.args.get("q", "").strip()
    lab = request.args.get("lab", "").strip()
    with db.connect(DB_PATH) as con:
        sql = "SELECT * FROM people WHERE 1=1"
        args: list = []
        if q:
            sql += " AND (name LIKE ? OR research_area LIKE ?)"
            args.extend([f"%{q}%", f"%{q}%"])
        if lab:
            sql += " AND lab LIKE ?"
            args.append(f"%{lab}%")
        sql += " ORDER BY lab, name LIMIT 200"
        rows = [dict(r) for r in con.execute(sql, args).fetchall()]
        labs = [r["lab"] for r in con.execute("SELECT DISTINCT lab FROM people ORDER BY lab").fetchall()]
    return render_template("people.html", people=rows, labs=labs, q=q, current_lab=lab)


@app.route("/people/<int:person_id>")
def person_detail(person_id: int):
    with db.connect(DB_PATH) as con:
        person = con.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        if not person:
            return "Not found", 404
        papers = con.execute(
            "SELECT * FROM papers WHERE matched_person = ? OR authors LIKE ? ORDER BY published DESC LIMIT 20",
            (person["name"], f'%{person["name"]}%'),
        ).fetchall()
        signals = con.execute(
            "SELECT * FROM signals WHERE person_name = ? ORDER BY observed_at DESC LIMIT 10",
            (person["name"],),
        ).fetchall()
    return render_template(
        "person.html",
        person=dict(person),
        papers=[dict(p) for p in papers],
        signals=[dict(s) for s in signals],
    )


@app.route("/papers/<int:paper_id>/draft", methods=["POST"])
def draft_outreach(paper_id: int):
    intro = request.form.get("intro") or "Investor at MoreMarkets, previously built NEAR DA."
    with db.connect(DB_PATH) as con:
        _ensure_user_tables(con)
        paper = con.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if not paper:
            return jsonify({"error": "paper not found"}), 404
        try:
            body = extract.draft_outreach(
                person_name=paper["matched_person"] or "there",
                paper_title=paper["title"],
                paper_summary=paper["summary"] or "",
                sender_intro=intro,
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        con.execute(
            "INSERT INTO drafts (user_id, paper_id, body, created_at) VALUES (?, ?, ?, ?)",
            (TEST_USER_ID, paper_id, body, datetime.now(timezone.utc).isoformat()),
        )
    return jsonify({"draft": body})


@app.route("/papers/<int:paper_id>/<action>", methods=["POST"])
def paper_action(paper_id: int, action: str):
    if action not in ("save", "hide", "sent", "unsave", "unhide", "unsent"):
        return jsonify({"error": "bad action"}), 400
    kind = action.replace("un", "") + ("ed" if action.endswith("save") or action.endswith("unsave") else "")
    kind_map = {"save": "saved", "hide": "hidden", "sent": "sent",
                "unsave": "saved", "unhide": "hidden", "unsent": "sent"}
    kind = kind_map[action]
    is_undo = action.startswith("un")
    with db.connect(DB_PATH) as con:
        _ensure_user_tables(con)
        if is_undo:
            con.execute(
                "DELETE FROM user_actions WHERE user_id = ? AND paper_id = ? AND kind = ?",
                (TEST_USER_ID, paper_id, kind),
            )
        else:
            con.execute(
                """INSERT OR REPLACE INTO user_actions
                   (user_id, paper_id, kind, created_at)
                   VALUES (?, ?, ?, ?)""",
                (TEST_USER_ID, paper_id, kind, datetime.now(timezone.utc).isoformat()),
            )
    return jsonify({"ok": True, "action": action})


@app.route("/health")
def health():
    return {"status": "ok", "user": TEST_USER_ID}


if __name__ == "__main__":
    app.run(debug=True, port=5050)
