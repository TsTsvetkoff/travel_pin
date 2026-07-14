"""
Single source of truth for SQLite I/O and locations.json export.

Used by:
- app.py (Flask) for reads and inserts.
- export_to_json.py (CLI shim) for the manual one-off export.
- /add endpoint, which calls export_locations() after a successful insert
  so locations.json is always in sync with locations.db.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

# Resolve the data files to absolute paths anchored at the repo root (the
# directory containing this module). This way `python app.py` and
# `python scripts/build_static.py` find the same files regardless of the
# caller's CWD — a previous version used bare relative names and broke when
# the script was launched from anywhere but the repo root.
_REPO_ROOT = Path(__file__).resolve().parent
DB_NAME = str(_REPO_ROOT / 'locations.db')
JSON_NAME = str(_REPO_ROOT / 'locations.json')

# Keep the column order aligned with the SELECT in all_locations / export_locations.
_COLUMNS = ('id', 'name_bg', 'latitude', 'longitude', 'category', 'sto_nto')


def _connect(db_path: str = DB_NAME) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def init_db(db_path: str = DB_NAME) -> None:
    """Create the locations table if it doesn't already exist."""
    conn = _connect(db_path)
    try:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_bg TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                category TEXT NOT NULL,
                sto_nto INTEGER NOT NULL
            )
            '''
        )
        conn.commit()
    finally:
        conn.close()


def insert_location(
    name_bg: str,
    latitude: float,
    longitude: float,
    category: str,
    sto_nto: int,
    db_path: str = DB_NAME,
) -> int:
    """Insert a row and return the new id."""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            '''
            INSERT INTO locations (name_bg, latitude, longitude, category, sto_nto)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (name_bg, latitude, longitude, category, sto_nto),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def all_locations(db_path: str = DB_NAME) -> list[dict[str, Any]]:
    """Return every location as a list of dicts."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            'SELECT id, name_bg, latitude, longitude, category, sto_nto FROM locations'
        ).fetchall()
    finally:
        conn.close()
    return [dict(zip(_COLUMNS, row)) for row in rows]


def export_locations(
    db_path: str = DB_NAME,
    out_path: str = JSON_NAME,
) -> list[dict[str, Any]]:
    """Read every row from the DB and write them to a JSON file.

    Returns the list of locations written, so callers can log/use the result
    if they want.
    """
    locations = all_locations(db_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(locations, f, ensure_ascii=False, indent=2)
    return locations
