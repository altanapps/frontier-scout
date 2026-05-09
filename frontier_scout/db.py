import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    lab TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT,
    profile_url TEXT,
    research_area TEXT,
    github_handle TEXT,
    twitter_handle TEXT,
    personal_site TEXT,
    email TEXT,
    enriched_at TEXT,
    UNIQUE(lab, name)
);

CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    arxiv_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,
    summary TEXT,
    published TEXT NOT NULL,
    pdf_url TEXT,
    matched_person TEXT,
    matched_lab TEXT,
    why_it_matters TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY,
    person_name TEXT NOT NULL,
    lab TEXT,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT,
    url TEXT,
    observed_at TEXT NOT NULL,
    UNIQUE(person_name, kind, url)
);

CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published);
CREATE INDEX IF NOT EXISTS idx_papers_lab ON papers(matched_lab);
CREATE INDEX IF NOT EXISTS idx_signals_observed ON signals(observed_at);
"""

MIGRATIONS = [
    "ALTER TABLE people ADD COLUMN github_handle TEXT",
    "ALTER TABLE people ADD COLUMN twitter_handle TEXT",
    "ALTER TABLE people ADD COLUMN personal_site TEXT",
    "ALTER TABLE people ADD COLUMN email TEXT",
    "ALTER TABLE people ADD COLUMN enriched_at TEXT",
    "ALTER TABLE papers ADD COLUMN doi TEXT",
    "ALTER TABLE papers ADD COLUMN venue TEXT",
    "ALTER TABLE papers ADD COLUMN openalex_id TEXT",
    "ALTER TABLE people ADD COLUMN openalex_id TEXT",
    "ALTER TABLE people ADD COLUMN h_index INTEGER",
    "ALTER TABLE people ADD COLUMN citation_count INTEGER",
    "ALTER TABLE signals ADD COLUMN score INTEGER DEFAULT 5",
    "ALTER TABLE people ADD COLUMN linkedin_url TEXT",
    "ALTER TABLE people ADD COLUMN verified_at TEXT",
]


def _migrate(con: sqlite3.Connection) -> None:
    for sql in MIGRATIONS:
        try:
            con.execute(sql)
        except sqlite3.OperationalError:
            pass


@contextmanager
def connect(path: Path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    try:
        yield con
        con.commit()
    finally:
        con.close()
