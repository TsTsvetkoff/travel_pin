"""
Exports locations.db into locations.json for the static (GitHub Pages) site.

Run this locally after adding/editing locations, then commit + push
locations.json alongside your other GitHub Pages files.

Usage:
    python export_to_json.py
    python export_to_json.py --db locations.db --out locations.json
"""

import argparse
import json
import sqlite3


def export_locations(db_path, out_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT id, name_bg, latitude, longitude, category, sto_nto FROM locations')
    rows = c.fetchall()
    conn.close()

    locations = [
        {
            'id': row[0],
            'name_bg': row[1],
            'latitude': row[2],
            'longitude': row[3],
            'category': row[4],
            'sto_nto': row[5],
        }
        for row in rows
    ]

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(locations, f, ensure_ascii=False, indent=2)

    print(f'Exported {len(locations)} locations to {out_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='locations.db', help='Path to the SQLite database')
    parser.add_argument('--out', default='locations.json', help='Path to write the JSON file')
    args = parser.parse_args()

    export_locations(args.db, args.out)