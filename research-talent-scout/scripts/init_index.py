#!/usr/bin/env python3
import argparse
import json
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    degree TEXT NOT NULL CHECK (degree IN ('phd', 'masters')),
    institution TEXT NOT NULL DEFAULT '',
    lab TEXT NOT NULL DEFAULT '',
    graduation_year INTEGER,
    graduation_state TEXT NOT NULL CHECK (
        graduation_state IN ('confirmed', 'likely_needs_verification', 'unknown', 'stale', 'conflict')
    ),
    identity_state TEXT NOT NULL CHECK (identity_state IN ('verified', 'ambiguous')),
    homepage TEXT NOT NULL DEFAULT '',
    verified_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_candidate_filter
ON candidates(degree, graduation_year, graduation_state);

CREATE TABLE IF NOT EXISTS publications (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER NOT NULL,
    normalized_venue TEXT NOT NULL,
    url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS authorships (
    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    publication_id TEXT NOT NULL REFERENCES publications(source_id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (
        category IN ('main_first', 'co_first', 'findings', 'workshop', 'short', 'demo', 'unclassified')
    ),
    PRIMARY KEY (candidate_id, publication_id, category)
);
CREATE INDEX IF NOT EXISTS idx_authorship_filter
ON authorships(candidate_id, category, publication_id);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    field TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN ('confirmed', 'likely_needs_verification', 'unknown', 'stale', 'conflict')
    ),
    source_type TEXT NOT NULL,
    url TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    UNIQUE(candidate_id, field, url, excerpt)
);

CREATE TABLE IF NOT EXISTS coverage (
    scope TEXT PRIMARY KEY,
    last_discovered_at TEXT,
    last_verified_at TEXT,
    source_status TEXT NOT NULL DEFAULT 'unknown',
    candidate_count INTEGER NOT NULL DEFAULT 0,
    publication_count INTEGER NOT NULL DEFAULT 0,
    gaps TEXT NOT NULL DEFAULT ''
);
"""


def connect(path: str) -> sqlite3.Connection:
    database = Path(path).expanduser().resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a researcher candidate index")
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    connection = connect(args.db)
    initialize(connection)
    print(json.dumps({"database": str(Path(args.db).expanduser().resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
