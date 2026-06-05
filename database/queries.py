from datetime import datetime
from database.db import get_db


def _date_clause(date_from, date_to):
    if date_from and date_to:
        return " AND e.date BETWEEN ? AND ?", [date_from, date_to]
    return "", []


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    dt = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": dt.strftime("%B %Y"),
    }


def get_all_categories():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, description FROM categories ORDER BY name"
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "name": r["name"], "description": r["description"]} for r in rows]


def get_summary_stats(user_id, date_from=None, date_to=None):
    clause, extra = _date_clause(date_from, date_to)
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(SUM(e.amount), 0) AS total, COUNT(*) AS cnt "
        "FROM expenses e WHERE e.user_id = ?" + clause,
        [user_id] + extra,
    ).fetchone()
    top = conn.execute(
        "SELECT c.name AS category "
        "FROM expenses e JOIN categories c ON e.category_id = c.id "
        "WHERE e.user_id = ?" + clause +
        " GROUP BY e.category_id ORDER BY SUM(e.amount) DESC LIMIT 1",
        [user_id] + extra,
    ).fetchone()
    conn.close()
    return {
        "total_spent": round(row["total"], 2),
        "transaction_count": row["cnt"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    clause, extra = _date_clause(date_from, date_to)
    conn = get_db()
    rows = conn.execute(
        "SELECT e.id, e.date, e.description, c.name AS category, e.category_id, e.amount "
        "FROM expenses e JOIN categories c ON e.category_id = c.id "
        "WHERE e.user_id = ?" + clause + " ORDER BY e.date DESC, e.id DESC LIMIT ?",
        [user_id] + extra + [limit],
    ).fetchall()
    conn.close()
    return [
        {"id": r["id"], "date": r["date"], "description": r["description"],
         "category": r["category"], "category_id": r["category_id"], "amount": r["amount"]}
        for r in rows
    ]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    clause, extra = _date_clause(date_from, date_to)
    conn = get_db()
    rows = conn.execute(
        "SELECT c.name AS category, SUM(e.amount) AS total "
        "FROM expenses e JOIN categories c ON e.category_id = c.id "
        "WHERE e.user_id = ?" + clause + " GROUP BY e.category_id ORDER BY total DESC",
        [user_id] + extra,
    ).fetchall()
    conn.close()
    if not rows:
        return []
    grand = sum(r["total"] for r in rows)
    result = [
        {"name": r["category"], "amount": round(r["total"], 2),
         "pct": int(round(r["total"] / grand * 100))}
        for r in rows
    ]
    result[0]["pct"] += 100 - sum(c["pct"] for c in result)
    return result


def insert_expense(user_id, amount, category_id, date_str, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category_id, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category_id, date_str, description or None),
    )
    conn.commit()
    conn.close()


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT e.*, c.name AS category_name "
        "FROM expenses e JOIN categories c ON e.category_id = c.id "
        "WHERE e.id = ? AND e.user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    conn.close()
    return row


def update_expense(expense_id, user_id, amount, category_id, date_str, description):
    conn = get_db()
    conn.execute(
        "UPDATE expenses SET amount=?, category_id=?, date=?, description=? "
        "WHERE id=? AND user_id=?",
        (amount, category_id, date_str, description or None, expense_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    conn.commit()
    conn.close()


def get_category_by_id(category_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, description FROM categories WHERE id = ?",
        (category_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_category(user_id, name, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO categories (user_id, name, description) VALUES (?, ?, ?)",
        (user_id, name, description or None),
    )
    conn.commit()
    conn.close()


def update_category(category_id, name, description):
    conn = get_db()
    conn.execute(
        "UPDATE categories SET name=?, description=? WHERE id=?",
        (name, description or None, category_id),
    )
    conn.commit()
    conn.close()


def delete_category(category_id):
    conn = get_db()
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
