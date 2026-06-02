import re
import pytest
from app import app
from database.db import get_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _make_empty_user():
    """Insert a user with no expenses; return their id."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty@test.local", "hash"),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return uid


def _delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid():
    user = get_user_by_id(1)
    assert user is not None
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert re.match(r"[A-Z][a-z]+ \d{4}", user["member_since"])


def test_get_user_by_id_nonexistent():
    assert get_user_by_id(999999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_get_summary_stats_seed_user():
    stats = get_summary_stats(1)
    assert stats["total_spent"] == 346.24
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses():
    uid = _make_empty_user()
    try:
        stats = get_summary_stats(uid)
        assert stats["total_spent"] == 0
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"
    finally:
        _delete_user(uid)


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_seed_user():
    txns = get_recent_transactions(1)
    assert len(txns) == 8
    dates = [t["date"] for t in txns]
    assert dates == sorted(dates, reverse=True)
    for t in txns:
        assert {"date", "description", "category", "amount"} <= t.keys()


def test_get_recent_transactions_no_expenses():
    uid = _make_empty_user()
    try:
        assert get_recent_transactions(uid) == []
    finally:
        _delete_user(uid)


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_seed_user():
    cats = get_category_breakdown(1)
    assert len(cats) == 7
    assert sum(c["pct"] for c in cats) == 100
    amounts = [c["amount"] for c in cats]
    assert amounts == sorted(amounts, reverse=True)
    assert cats[0]["name"] == "Bills"


def test_get_category_breakdown_no_expenses():
    uid = _make_empty_user()
    try:
        assert get_category_breakdown(uid) == []
    finally:
        _delete_user(uid)


# ------------------------------------------------------------------ #
# Route: GET /profile                                                 #
# ------------------------------------------------------------------ #

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_profile_unauthenticated(client):
    r = client.get("/profile", follow_redirects=False)
    assert r.status_code == 302
    assert "login" in r.headers["Location"]


def test_profile_authenticated_seed_user(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    r = client.get("/profile")
    assert r.status_code == 200
    html = r.data.decode("utf-8")
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "&#8377;346.24" in html
    assert "Bills" in html
    assert html.count("<tr>") >= 9          # thead tr + 8 data rows
    assert html.count("category-row") >= 7
