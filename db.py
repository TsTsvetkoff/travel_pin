"""SQLite working data; locations.json is the versioned public snapshot."""
import json
import sqlite3
from pathlib import Path
import tempfile
import os
ROOT=Path(__file__).resolve().parent
DB_NAME=str(ROOT/'locations.db')
JSON_NAME=str(ROOT/'locations.json')

def init_db(db_path=DB_NAME, seed_path=JSON_NAME):
    new=not Path(db_path).exists()
    with sqlite3.connect(db_path) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY AUTOINCREMENT, name_bg TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, category TEXT NOT NULL, sto_nto INTEGER NOT NULL)')
        if new and Path(seed_path).exists():
            items=json.loads(Path(seed_path).read_text(encoding='utf-8'))
            conn.executemany('INSERT INTO locations VALUES (:id,:name_bg,:latitude,:longitude,:category,:sto_nto)',items)

def all_locations(db_path=DB_NAME):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory=sqlite3.Row
        return [dict(r) for r in conn.execute('SELECT id,name_bg,latitude,longitude,category,sto_nto FROM locations ORDER BY id')]

def insert_location(name_bg,latitude,longitude,category,sto_nto,db_path=DB_NAME):
    with sqlite3.connect(db_path) as conn:
        return conn.execute('INSERT INTO locations (name_bg,latitude,longitude,category,sto_nto) VALUES (?,?,?,?,?)',(name_bg,latitude,longitude,category,sto_nto)).lastrowid

def export_locations(db_path=DB_NAME,out_path=JSON_NAME):
    data=all_locations(db_path); path=Path(out_path)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n'); temp=f.name
    os.replace(temp,path)
    return data
