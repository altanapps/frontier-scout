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

CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published);
CREATE INDEX IF NOT EXISTS idx_papers_lab ON papers(matched_lab);
"""


@contextmanager
def connect(path: Path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()
