import pytest
from app import app
from database.db import get_db
from database.queries import get_expense_by_id, update_expense


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
        ("Other User", "other@test.local", "hash"),
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
# Unit tests: get_expense_by_id                                       #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_valid():
    eid = _seed_expense_id()
    row = get_expense_by_id(eid, 1)
    assert row is not None
    assert row["id"] == eid
    assert row["user_id"] == 1


def test_get_expense_by_id_wrong_user():
    eid = _seed_expense_id()
    assert get_expense_by_id(eid, 999999) is None


def test_get_expense_by_id_nonexistent():
    assert get_expense_by_id(999999, 1) is None


# ------------------------------------------------------------------ #
# Unit tests: update_expense                                          #
# ------------------------------------------------------------------ #

def test_update_expense_valid():
    eid = _seed_expense_id()
    original = get_expense_by_id(eid, 1)
    original_amount = original["amount"]

    update_expense(eid, 1, 99.0, original["category"], original["date"], original["description"])
    updated = get_expense_by_id(eid, 1)
    assert updated["amount"] == 99.0

    # Restore original amount
    update_expense(eid, 1, original_amount, original["category"], original["date"], original["description"])


def test_update_expense_wrong_user():
    eid = _seed_expense_id()
    original_amount = get_expense_by_id(eid, 1)["amount"]

    update_expense(eid, 999999, 0.01, "Food", "2026-01-01", None)
    assert get_expense_by_id(eid, 1)["amount"] == original_amount


# ------------------------------------------------------------------ #
# Route: GET /expenses/<id>/edit                                      #
# ------------------------------------------------------------------ #

def test_get_edit_unauthenticated(client):
    eid = _seed_expense_id()
    r = client.get(f"/expenses/{eid}/edit", follow_redirects=False)
    assert r.status_code == 302
    assert "login" in r.headers["Location"]


def test_get_edit_authenticated_own(auth_client):
    eid = _seed_expense_id()
    r = auth_client.get(f"/expenses/{eid}/edit")
    assert r.status_code == 200
    html = r.data.decode("utf-8")
    assert "<form" in html
    assert "Save Changes" in html
    # Category pre-selected
    assert "selected" in html


def test_get_edit_other_users_expense(auth_client):
    other_uid = _make_other_user()
    try:
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (other_uid, 10.0, "Food", "2026-01-01"),
        )
        conn.commit()
        other_eid = cur.lastrowid
        conn.close()

        r = auth_client.get(f"/expenses/{other_eid}/edit")
        assert r.status_code == 404
    finally:
        _delete_user(other_uid)


def test_get_edit_nonexistent(auth_client):
    r = auth_client.get("/expenses/999999/edit")
    assert r.status_code == 404


# ------------------------------------------------------------------ #
# Route: POST /expenses/<id>/edit                                     #
# ------------------------------------------------------------------ #

def test_post_edit_unauthenticated(client):
    eid = _seed_expense_id()
    r = client.post(f"/expenses/{eid}/edit",
                    data={"amount": "50", "category": "Food", "date": "2026-03-20"},
                    follow_redirects=False)
    assert r.status_code == 302
    assert "login" in r.headers["Location"]


def test_post_edit_valid(auth_client):
    eid = _seed_expense_id()
    original = get_expense_by_id(eid, 1)

    r = auth_client.post(f"/expenses/{eid}/edit",
                         data={"amount": "77.77", "category": "Bills",
                               "date": "2026-04-01", "description": "Updated"},
                         follow_redirects=False)
    assert r.status_code == 302
    assert "/profile" in r.headers["Location"]

    updated = get_expense_by_id(eid, 1)
    assert updated["amount"] == 77.77
    assert updated["category"] == "Bills"

    # Restore
    update_expense(eid, 1, original["amount"], original["category"],
                   original["date"], original["description"])


def test_post_edit_other_users_expense(auth_client):
    other_uid = _make_other_user()
    try:
        conn = get_db()
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            (other_uid, 10.0, "Food", "2026-01-01"),
        )
        conn.commit()
        other_eid = cur.lastrowid
        conn.close()

        r = auth_client.post(f"/expenses/{other_eid}/edit",
                             data={"amount": "50", "category": "Food", "date": "2026-01-01"})
        assert r.status_code == 404
    finally:
        _delete_user(other_uid)


def test_post_edit_missing_amount(auth_client):
    eid = _seed_expense_id()
    r = auth_client.post(f"/expenses/{eid}/edit",
                         data={"amount": "", "category": "Food", "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_post_edit_zero_amount(auth_client):
    eid = _seed_expense_id()
    r = auth_client.post(f"/expenses/{eid}/edit",
                         data={"amount": "0", "category": "Food", "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_post_edit_nonnumeric_amount(auth_client):
    eid = _seed_expense_id()
    r = auth_client.post(f"/expenses/{eid}/edit",
                         data={"amount": "abc", "category": "Food", "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_post_edit_invalid_category(auth_client):
    eid = _seed_expense_id()
    r = auth_client.post(f"/expenses/{eid}/edit",
                         data={"amount": "50", "category": "Gambling", "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"valid category" in r.data


def test_post_edit_invalid_date(auth_client):
    eid = _seed_expense_id()
    r = auth_client.post(f"/expenses/{eid}/edit",
                         data={"amount": "50", "category": "Food", "date": "not-a-date"})
    assert r.status_code == 200
    assert b"valid date" in r.data


def test_post_edit_no_description(auth_client):
    eid = _seed_expense_id()
    original = get_expense_by_id(eid, 1)

    r = auth_client.post(f"/expenses/{eid}/edit",
                         data={"amount": "55.0", "category": "Food",
                               "date": "2026-05-01", "description": ""},
                         follow_redirects=False)
    assert r.status_code == 302
    updated = get_expense_by_id(eid, 1)
    assert updated["description"] is None

    # Restore
    update_expense(eid, 1, original["amount"], original["category"],
                   original["date"], original["description"])
