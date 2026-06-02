import pytest
from app import app
from database.db import get_db
from database.queries import insert_expense, CATEGORIES


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _get_expenses_for_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def _cleanup_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
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
# Unit tests: insert_expense                                          #
# ------------------------------------------------------------------ #

def test_insert_expense_with_description():
    before = _get_expenses_for_user(1)
    insert_expense(1, 50.0, "Food", "2026-03-20", "Lunch")
    after = _get_expenses_for_user(1)
    assert len(after) == len(before) + 1
    new = after[0]
    assert new["amount"] == 50.0
    assert new["category"] == "Food"
    assert new["date"] == "2026-03-20"
    assert new["description"] == "Lunch"
    _cleanup_expense(new["id"])


def test_insert_expense_null_description():
    before = _get_expenses_for_user(1)
    insert_expense(1, 25.0, "Transport", "2026-03-21", None)
    after = _get_expenses_for_user(1)
    assert len(after) == len(before) + 1
    new = after[0]
    assert new["description"] is None
    _cleanup_expense(new["id"])


# ------------------------------------------------------------------ #
# Route: GET /expenses/add                                            #
# ------------------------------------------------------------------ #

def test_get_add_expense_unauthenticated(client):
    r = client.get("/expenses/add", follow_redirects=False)
    assert r.status_code == 302
    assert "login" in r.headers["Location"]


def test_get_add_expense_authenticated(auth_client):
    r = auth_client.get("/expenses/add")
    assert r.status_code == 200
    html = r.data.decode("utf-8")
    assert "<form" in html
    assert 'method="post"' in html.lower()
    for cat in CATEGORIES:
        assert cat in html


# ------------------------------------------------------------------ #
# Route: POST /expenses/add                                           #
# ------------------------------------------------------------------ #

def test_post_add_expense_unauthenticated(client):
    r = client.post("/expenses/add",
                    data={"amount": "50", "category": "Food",
                          "date": "2026-03-20", "description": "Lunch"},
                    follow_redirects=False)
    assert r.status_code == 302
    assert "login" in r.headers["Location"]


def test_post_add_expense_valid(auth_client):
    before = _get_expenses_for_user(1)
    r = auth_client.post("/expenses/add",
                         data={"amount": "50.0", "category": "Food",
                               "date": "2026-03-20", "description": "Lunch"},
                         follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/profile") or "/profile" in r.headers["Location"]
    after = _get_expenses_for_user(1)
    assert len(after) == len(before) + 1
    _cleanup_expense(after[0]["id"])


def test_post_add_expense_missing_amount(auth_client):
    r = auth_client.post("/expenses/add",
                         data={"amount": "", "category": "Food",
                               "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"positive number" in r.data or b"error" in r.data.lower()


def test_post_add_expense_zero_amount(auth_client):
    r = auth_client.post("/expenses/add",
                         data={"amount": "0", "category": "Food",
                               "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_post_add_expense_nonnumeric_amount(auth_client):
    r = auth_client.post("/expenses/add",
                         data={"amount": "abc", "category": "Food",
                               "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_post_add_expense_invalid_category(auth_client):
    r = auth_client.post("/expenses/add",
                         data={"amount": "50", "category": "Gambling",
                               "date": "2026-03-20"})
    assert r.status_code == 200
    assert b"valid category" in r.data


def test_post_add_expense_invalid_date(auth_client):
    r = auth_client.post("/expenses/add",
                         data={"amount": "50", "category": "Food",
                               "date": "not-a-date"})
    assert r.status_code == 200
    assert b"valid date" in r.data


def test_post_add_expense_no_description(auth_client):
    before = _get_expenses_for_user(1)
    r = auth_client.post("/expenses/add",
                         data={"amount": "30", "category": "Transport",
                               "date": "2026-03-22", "description": ""},
                         follow_redirects=False)
    assert r.status_code == 302
    after = _get_expenses_for_user(1)
    assert len(after) == len(before) + 1
    assert after[0]["description"] is None
    _cleanup_expense(after[0]["id"])
