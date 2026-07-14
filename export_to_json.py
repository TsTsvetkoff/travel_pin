"""
CLI shim over db.export_locations().

Kept as a separate script so the existing workflow
(`python export_to_json.py --db ... --out ...`) still works.
The real implementation lives in db.py so the auto-export on /add
and this manual export can't drift apart.

Usage:
    python export_to_json.py
    python export_to_json.py --db locations.db --out locations.json
"""

import argparse

import db


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=db.DB_NAME, help='Path to the SQLite database')
    parser.add_argument('--out', default=db.JSON_NAME, help='Path to write the JSON file')
    args = parser.parse_args()

    locations = db.export_locations(args.db, args.out)
    print(f'Exported {len(locations)} locations to {args.out}')


if __name__ == '__main__':
    main()
