"""Export the groups, questions and answers tables to JSON files.

Each table is written to database/export/<table>.json as a list of row
objects (one dict per row, keyed by column name). Run with:  py export_db.py
"""
import json
import os
import sqlite3

DB_PATH     = os.path.join(os.path.dirname(__file__), "spendly.db")
EXPORT_DIR  = os.path.join(os.path.dirname(__file__), "database", "export")
TABLES      = ["groups", "questions", "answers"]


def export_table(conn, table):
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY id")]
    path = os.path.join(EXPORT_DIR, f"{table}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return len(rows), path


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        for table in TABLES:
            count, path = export_table(conn, table)
            print(f"Exported {count:>4} rows -> {os.path.relpath(path)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
