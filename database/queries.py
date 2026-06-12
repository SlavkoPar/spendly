from datetime import datetime
from database.db import get_db


# ------------------------------------------------------------------ #
# Answers & assignments                                               #
# ------------------------------------------------------------------ #

def get_all_answers(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, short_desc, description, link FROM answers "
        "WHERE user_id = ? ORDER BY short_desc",
        (user_id,),
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "short_desc": r["short_desc"],
             "description": r["description"], "link": r["link"]} for r in rows]


def get_answer_by_id(answer_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, short_desc, description, link FROM answers WHERE id = ? AND user_id = ?",
        (answer_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_answer(user_id, short_desc, description, link):
    conn = get_db()
    conn.execute(
        "INSERT INTO answers (user_id, short_desc, description, link) VALUES (?, ?, ?, ?)",
        (user_id, short_desc, description or None, link or None),
    )
    conn.commit()
    conn.close()


def update_answer(answer_id, user_id, short_desc, description, link):
    conn = get_db()
    conn.execute(
        "UPDATE answers SET short_desc=?, description=?, link=? WHERE id=? AND user_id=?",
        (short_desc, description or None, link or None, answer_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_answer(answer_id, user_id):
    conn = get_db()
    for row in conn.execute(
        "SELECT question_id FROM question_answers WHERE answer_id = ?", (answer_id,)
    ).fetchall():
        conn.execute(
            "UPDATE questions "
            "SET num_of_assigned_answers = MAX(0, num_of_assigned_answers - 1) "
            "WHERE id = ?", (row["question_id"],)
        )
    conn.execute("DELETE FROM question_answers WHERE answer_id = ?", (answer_id,))
    conn.execute("DELETE FROM answers WHERE id = ? AND user_id = ?", (answer_id, user_id))
    conn.commit()
    conn.close()


def get_assigned_answers_for_question(question_id, user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT a.id, a.short_desc, a.description FROM answers a "
        "JOIN question_answers qa ON qa.answer_id = a.id "
        "WHERE qa.question_id = ? AND a.user_id = ? ORDER BY a.short_desc",
        (question_id, user_id),
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "short_desc": r["short_desc"], "description": r["description"]}
            for r in rows]


def get_unassigned_answers_for_question(question_id, user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, short_desc, description FROM answers "
        "WHERE user_id = ? AND id NOT IN "
        "(SELECT answer_id FROM question_answers WHERE question_id = ?) "
        "ORDER BY short_desc",
        (user_id, question_id),
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "short_desc": r["short_desc"], "description": r["description"]}
            for r in rows]


def assign_answer(question_id, answer_id, user_id):
    conn = get_db()
    exists = conn.execute(
        "SELECT 1 FROM question_answers WHERE question_id = ? AND answer_id = ?",
        (question_id, answer_id),
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO question_answers (question_id, answer_id, user_id) VALUES (?, ?, ?)",
            (question_id, answer_id, user_id),
        )
        conn.execute(
            "UPDATE questions SET num_of_assigned_answers = num_of_assigned_answers + 1 "
            "WHERE id = ?", (question_id,)
        )
    conn.commit()
    conn.close()


def unassign_answer(question_id, answer_id, user_id):
    conn = get_db()
    deleted = conn.execute(
        "DELETE FROM question_answers WHERE question_id = ? AND answer_id = ? AND user_id = ?",
        (question_id, answer_id, user_id),
    ).rowcount
    if deleted:
        conn.execute(
            "UPDATE questions "
            "SET num_of_assigned_answers = MAX(0, num_of_assigned_answers - 1) "
            "WHERE id = ?", (question_id,)
        )
    conn.commit()
    conn.close()


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


# ------------------------------------------------------------------ #
# Groups                                                              #
# ------------------------------------------------------------------ #

def get_all_groups(user_id):
    """Return groups in pre-order (parents before their children) with a
    ``depth`` key so the list page can render them as an indented tree."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, parent_id, name, description, num_of_questions FROM groups "
        "WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()
    conn.close()

    groups = [{"id": r["id"], "parent_id": r["parent_id"], "name": r["name"],
               "description": r["description"], "num_of_questions": r["num_of_questions"]}
              for r in rows]

    children = {}
    for g in groups:
        children.setdefault(g["parent_id"], []).append(g)

    ordered = []

    def walk(parent_id, depth):
        for g in children.get(parent_id, []):
            g["depth"] = depth
            ordered.append(g)
            walk(g["id"], depth + 1)

    walk(None, 0)

    # Any group whose parent was deleted becomes a root so it is never hidden.
    seen = {g["id"] for g in ordered}
    for g in groups:
        if g["id"] not in seen:
            g["depth"] = 0
            ordered.append(g)
    return ordered


def get_group_by_id(group_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, parent_id, name, description, num_of_questions "
        "FROM groups WHERE id = ? AND user_id = ?",
        (group_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_group(user_id, name, description, parent_id=None):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO groups (user_id, name, description, parent_id) VALUES (?, ?, ?, ?)",
        (user_id, name, description or None, parent_id),
    )
    conn.commit()
    group_id = cursor.lastrowid
    conn.close()
    return group_id


def update_group(group_id, user_id, name, description):
    conn = get_db()
    conn.execute(
        "UPDATE groups SET name=?, description=? WHERE id=? AND user_id=?",
        (name, description or None, group_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_group(group_id, user_id):
    conn = get_db()
    conn.execute("DELETE FROM questions WHERE group_id = ?", (group_id,))
    conn.execute("DELETE FROM groups WHERE id = ? AND user_id = ?", (group_id, user_id))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Questions                                                           #
# ------------------------------------------------------------------ #

def get_questions_by_group(group_id, user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT q.id, q.text, q.description, q.num_of_assigned_answers, "
        "GROUP_CONCAT(qa.answer_id) AS assigned_ids "
        "FROM questions q "
        "LEFT JOIN question_answers qa ON qa.question_id = q.id "
        "WHERE q.group_id = ? AND q.user_id = ? "
        "GROUP BY q.id ORDER BY q.id",
        (group_id, user_id),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        ids = [int(x) for x in r["assigned_ids"].split(",")] if r["assigned_ids"] else []
        result.append({"id": r["id"], "text": r["text"], "description": r["description"],
                       "num_of_assigned_answers": r["num_of_assigned_answers"],
                       "assigned_answer_ids": ids})
    return result


def get_question_by_id(question_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, group_id, text, description FROM questions WHERE id = ? AND user_id = ?",
        (question_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_question(user_id, group_id, text, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO questions (user_id, group_id, text, description) VALUES (?, ?, ?, ?)",
        (user_id, group_id, text, description or None),
    )
    conn.execute(
        "UPDATE groups SET num_of_questions = num_of_questions + 1 WHERE id = ?",
        (group_id,),
    )
    conn.commit()
    conn.close()


def update_question(question_id, user_id, text, description):
    conn = get_db()
    conn.execute(
        "UPDATE questions SET text=?, description=? WHERE id=? AND user_id=?",
        (text, description or None, question_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_question(question_id, group_id, user_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM questions WHERE id = ? AND user_id = ?",
        (question_id, user_id),
    )
    conn.execute(
        "UPDATE groups SET num_of_questions = MAX(0, num_of_questions - 1) WHERE id = ?",
        (group_id,),
    )
    conn.commit()
    conn.close()
