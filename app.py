import sqlite3
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import (get_user_by_id, get_summary_stats, get_recent_transactions,
                              get_category_breakdown, insert_expense, CATEGORIES,
                              get_expense_by_id, update_expense, delete_expense)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        email            = request.form.get("email", "").strip()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("All fields are required.")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return render_template("register.html")

        flash("Account created — please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("landing"))

    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    def parse_date(key):
        val = request.args.get(key, "").strip()
        try:
            return datetime.strptime(val, "%Y-%m-%d").date() if val else None
        except ValueError:
            return None

    date_from = parse_date("date_from")
    date_to   = parse_date("date_to")

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = date_to = None

    df_str = date_from.isoformat() if date_from else None
    dt_str = date_to.isoformat()   if date_to   else None

    today = date.today()

    def first_of_month_n_ago(n):
        m = today.month - n
        y = today.year + m // 12 - (1 if m % 12 == 0 and m < 0 else 0)
        m = m % 12 or 12
        return date(y, m, 1)

    preset_ranges = [
        {"label": "This Month",    "slug": "this_month",
         "date_from": date(today.year, today.month, 1).isoformat(), "date_to": today.isoformat()},
        {"label": "Last 3 Months", "slug": "last_3_months",
         "date_from": first_of_month_n_ago(3).isoformat(), "date_to": today.isoformat()},
        {"label": "Last 6 Months", "slug": "last_6_months",
         "date_from": first_of_month_n_ago(6).isoformat(), "date_to": today.isoformat()},
    ]

    active_preset = "all_time"
    if df_str and dt_str:
        for p in preset_ranges:
            if df_str == p["date_from"] and dt_str == p["date_to"]:
                active_preset = p["slug"]
                break
        else:
            active_preset = "custom"

    user_id      = session["user_id"]
    user_row     = get_user_by_id(user_id)
    stats        = get_summary_stats(user_id, df_str, dt_str)
    transactions = get_recent_transactions(user_id, date_from=df_str, date_to=dt_str)
    categories   = get_category_breakdown(user_id, df_str, dt_str)

    parts    = user_row["name"].split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    user     = {**user_row, "initials": initials}

    return render_template(
        "profile.html",
        user=user, stats=stats, transactions=transactions, categories=categories,
        date_from=df_str, date_to=dt_str,
        preset_ranges=preset_ranges, active_preset=active_preset,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        raw_amount  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        raw_date    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip() or None

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "error")
            return render_template("add_expense.html", categories=CATEGORIES,
                                   form=request.form)

        if category not in CATEGORIES:
            flash("Please select a valid category.", "error")
            return render_template("add_expense.html", categories=CATEGORIES,
                                   form=request.form)

        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            flash("Please enter a valid date.", "error")
            return render_template("add_expense.html", categories=CATEGORIES,
                                   form=request.form)

        insert_expense(session["user_id"], amount, category, raw_date, description)
        flash("Expense added.", "success")
        return redirect(url_for("profile"))

    return render_template("add_expense.html", categories=CATEGORIES,
                           form={}, today=date.today().isoformat())


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    if request.method == "POST":
        raw_amount  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        raw_date    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip() or None

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "error")
            return render_template("edit_expense.html", expense=expense,
                                   categories=CATEGORIES, form=request.form)

        if category not in CATEGORIES:
            flash("Please select a valid category.", "error")
            return render_template("edit_expense.html", expense=expense,
                                   categories=CATEGORIES, form=request.form)

        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            flash("Please enter a valid date.", "error")
            return render_template("edit_expense.html", expense=expense,
                                   categories=CATEGORIES, form=request.form)

        update_expense(id, session["user_id"], amount, category, raw_date, description)
        flash("Expense updated.", "success")
        return redirect(url_for("profile"))

    return render_template("edit_expense.html", expense=expense,
                           categories=CATEGORIES, form=dict(expense))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    delete_expense(id, session["user_id"])
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
