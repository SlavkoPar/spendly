"""Import rows from database/export/<table>.json back into the database.

Reads each JSON file (a list of row dicts) and inserts the rows, preserving
ids and all columns present. Tables are loaded in FK-safe order. Run with:
  py import_db.py
"""
import json
import os
import sqlite3

DB_PATH    = os.path.join(os.path.dirname(__file__), "spendly.db")
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "database", "export")
# FK-safe order: parents before children.
TABLES     = ["groups", "answers", "questions", "question_answers"]


def import_table(conn, table):
    path = os.path.join(EXPORT_DIR, f"{table}.json")
    if not os.path.exists(path):
        print(f"Skipped {table:<16} (no {os.path.relpath(path)})")
        return
    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not rows:
        print(f"Imported {0:>4} rows -> {table}")
        return
    for row in rows:
        cols = list(row.keys())
        placeholders = ", ".join("?" for _ in cols)
        col_list = ", ".join(cols)
        conn.execute(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
            [row[c] for c in cols],
        )
    conn.commit()
    print(f"Imported {len(rows):>4} rows -> {table}")


def main():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        for table in TABLES:
            import_table(conn, table)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
