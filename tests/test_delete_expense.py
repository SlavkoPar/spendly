import pytest
from app import app
from database.db import get_db
from database.queries import get_expense_by_id, delete_expense


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _seed_expense_id():
    """Return the id of the first expense owned by the seed user (id=1)."""
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM expenses WHERE user_id = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    conn.close()
    return row["id"]


def _make_other_user():
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other2@test.local", "hash"),
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


def _insert_expense(user_id):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
        (user_id, 25.0, "Food", "2026-01-15"),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def _expense_exists(expense_id):
    conn = get_db()
    row = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return row is not None


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    yield client


# ------------------------------------------------------------------ #
# Unit tests: delete_expense                                          #
# ------------------------------------------------------------------ #

def test_delete_expense_valid():
    eid = _insert_expense(1)
    assert _expense_exists(eid)
    delete_expense(eid, 1)
    assert not _expense_exists(eid)


def test_delete_expense_wrong_user():
    eid = _insert_expense(1)
    delete_expense(eid, 999999)
    assert _expense_exists(eid)
    # Cleanup
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ?", (eid,))
    conn.commit()
    conn.close()


def test_delete_expense_nonexistent():
    delete_expense(999999, 1)  # must not raise


# ------------------------------------------------------------------ #
# Route: POST /expenses/<id>/delete                                   #
# ------------------------------------------------------------------ #

def test_post_delete_unauthenticated(client):
    eid = _seed_expense_id()
    r = client.post(f"/expenses/{eid}/delete", follow_redirects=False)
    assert r.status_code == 302
    assert "login" in r.headers["Location"]


def test_post_delete_own_expense(auth_client):
    eid = _insert_expense(1)
    r = auth_client.post(f"/expenses/{eid}/delete", follow_redirects=False)
    assert r.status_code == 302
    assert "/profile" in r.headers["Location"]
    assert not _expense_exists(eid)


def test_post_delete_other_users_expense(auth_client):
    other_uid = _make_other_user()
    try:
        eid = _insert_expense(other_uid)
        r = auth_client.post(f"/expenses/{eid}/delete")
        assert r.status_code == 404
        assert _expense_exists(eid)
    finally:
        _delete_user(other_uid)


def test_post_delete_nonexistent(auth_client):
    r = auth_client.post("/expenses/999999/delete")
    assert r.status_code == 404


def test_get_delete_returns_405(client):
    eid = _seed_expense_id()
    r = client.get(f"/expenses/{eid}/delete")
    assert r.status_code == 405
