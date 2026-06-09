import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "spendly.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            email        TEXT    UNIQUE NOT NULL,
            password_hash TEXT   NOT NULL,
            created_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            name        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS groups (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL REFERENCES users(id),
            name             TEXT    NOT NULL,
            description      TEXT,
            num_of_questions INTEGER DEFAULT 0,
            created_at       TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS questions (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id                 INTEGER NOT NULL REFERENCES users(id),
            group_id                INTEGER NOT NULL REFERENCES groups(id),
            text                    TEXT    NOT NULL,
            description             TEXT,
            num_of_assigned_answers INTEGER DEFAULT 0,
            created_at              TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS answers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            short_desc  TEXT    NOT NULL,
            description TEXT,
            link        TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS question_answers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL REFERENCES questions(id),
            answer_id   INTEGER NOT NULL REFERENCES answers(id),
            future      TEXT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)

    cols = {row["name"] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()}
    if not cols:
        conn.executescript("""
            CREATE TABLE expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL    NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            );
        """)
    elif "category" in cols and "category_id" not in cols:
        conn.executescript("""
            DROP TABLE expenses;
            CREATE TABLE expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL    NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            );
        """)

    q_cols = {r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()}
    if "num_of_assigned_answers" not in q_cols:
        conn.execute(
            "ALTER TABLE questions ADD COLUMN num_of_assigned_answers INTEGER DEFAULT 0"
        )

    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    hashed = generate_password_hash(password)
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, hashed),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user


def seed_db():
    conn = get_db()

    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        conn.commit()

    row = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()
    if row is None:
        conn.close()
        return
    user_id = row[0]

    if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO categories (user_id, name) VALUES (?, ?)",
            [(user_id, name) for name in
             ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]],
        )
        conn.commit()

    if conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0:
        cats = {r["name"]: r["id"] for r in
                conn.execute("SELECT id, name FROM categories WHERE user_id = ?", (user_id,)).fetchall()}
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category_id, date, description) VALUES (?, ?, ?, ?, ?)",
            [
                (user_id, 45.50,  cats["Food"],          "2026-06-01", "Weekly groceries"),
                (user_id, 32.00,  cats["Transport"],     "2026-06-02", "Monthly bus pass top-up"),
                (user_id, 120.00, cats["Bills"],         "2026-06-03", "Electricity bill"),
                (user_id, 20.00,  cats["Health"],        "2026-06-05", "Pharmacy"),
                (user_id, 25.00,  cats["Entertainment"], "2026-06-08", "Cinema tickets"),
                (user_id, 69.99,  cats["Shopping"],      "2026-06-10", "New trainers"),
                (user_id, 15.00,  cats["Other"],         "2026-06-12", "Charity donation"),
                (user_id, 18.75,  cats["Food"],          "2026-06-14", "Lunch out"),
            ],
        )
        conn.commit()

    conn.close()
