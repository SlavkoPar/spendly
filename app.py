import sqlite3
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import (get_user_by_id, get_summary_stats, get_recent_transactions,
                              get_category_breakdown, get_all_categories,
                              insert_expense, get_expense_by_id, update_expense, delete_expense,
                              get_category_by_id, insert_category, update_category, delete_category,
                              get_all_groups, get_group_by_id, insert_group, update_group, delete_group,
                              get_questions_by_group, get_question_by_id,
                              insert_question, update_question, delete_question,
                              get_all_answers, get_answer_by_id,
                              insert_answer, update_answer, delete_answer,
                              get_assigned_answers_for_question, get_unassigned_answers_for_question,
                              assign_answer, unassign_answer)

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
    all_cats     = get_all_categories()

    parts    = user_row["name"].split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    user     = {**user_row, "initials": initials}

    return render_template(
        "profile.html",
        user=user, stats=stats, transactions=transactions, categories=categories,
        date_from=df_str, date_to=dt_str,
        preset_ranges=preset_ranges, active_preset=active_preset,
        all_categories=all_cats,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    categories = get_all_categories()

    if request.method == "POST":
        raw_amount       = request.form.get("amount", "").strip()
        category_id_str  = request.form.get("category_id", "").strip()
        raw_date         = request.form.get("date", "").strip()
        description      = request.form.get("description", "").strip() or None

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "error")
            return render_template("add_expense.html", categories=categories,
                                   form=request.form)

        try:
            category_id = int(category_id_str)
        except ValueError:
            flash("Please select a valid category.", "error")
            return render_template("add_expense.html", categories=categories,
                                   form=request.form)

        valid_ids = {c["id"] for c in categories}
        if category_id not in valid_ids:
            flash("Please select a valid category.", "error")
            return render_template("add_expense.html", categories=categories,
                                   form=request.form)

        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            flash("Please enter a valid date.", "error")
            return render_template("add_expense.html", categories=categories,
                                   form=request.form)

        insert_expense(session["user_id"], amount, category_id, raw_date, description)
        flash("Expense added.", "success")
        return redirect(url_for("profile"))

    return render_template("add_expense.html", categories=categories,
                           form={}, today=date.today().isoformat())


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    categories = get_all_categories()

    if request.method == "POST":
        raw_amount      = request.form.get("amount", "").strip()
        category_id_str = request.form.get("category_id", "").strip()
        raw_date        = request.form.get("date", "").strip()
        description     = request.form.get("description", "").strip() or None

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "error")
            return render_template("edit_expense.html", expense=expense,
                                   categories=categories, form=request.form)

        try:
            category_id = int(category_id_str)
        except ValueError:
            flash("Please select a valid category.", "error")
            return render_template("edit_expense.html", expense=expense,
                                   categories=categories, form=request.form)

        valid_ids = {c["id"] for c in categories}
        if category_id not in valid_ids:
            flash("Please select a valid category.", "error")
            return render_template("edit_expense.html", expense=expense,
                                   categories=categories, form=request.form)

        try:
            datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            flash("Please enter a valid date.", "error")
            return render_template("edit_expense.html", expense=expense,
                                   categories=categories, form=request.form)

        update_expense(id, session["user_id"], amount, category_id, raw_date, description)
        flash("Expense updated.", "success")
        return redirect(url_for("profile"))

    return render_template("edit_expense.html", expense=expense,
                           categories=categories, form=dict(expense))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    delete_expense(id, session["user_id"])
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Categories                                                          #
# ------------------------------------------------------------------ #

@app.route("/categories")
def categories():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    all_cats = get_all_categories()
    return render_template("categories/list.html", categories=all_cats)


@app.route("/categories/add", methods=["GET", "POST"])
def add_category():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Category name is required.", "error")
            return redirect(url_for("categories"))

        insert_category(session["user_id"], name, description)
        flash("Category added.", "success")
        return redirect(url_for("categories"))

    return render_template("categories/add_category.html")


@app.route("/categories/<int:id>/edit", methods=["GET", "POST"])
def edit_category(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    cat = get_category_by_id(id)
    if cat is None:
        abort(404)

    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Category name is required.", "error")
            return redirect(url_for("categories"))

        update_category(id, name, description)
        flash("Category updated.", "success")
        return redirect(url_for("categories"))

    return render_template("categories/edit_category.html", category=cat)


@app.route("/categories/<int:id>/delete", methods=["GET", "POST"])
def delete_category_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    cat = get_category_by_id(id)
    if cat is None:
        abort(404)

    if request.method == "POST":
        delete_category(id)
        flash("Category deleted.", "success")
        return redirect(url_for("categories"))

    return render_template("categories/delete_category.html", category=cat)


# ------------------------------------------------------------------ #
# Groups                                                              #
# ------------------------------------------------------------------ #

@app.route("/groups")
def groups():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    all_groups = get_all_groups(session["user_id"])
    return render_template("groups/list.html", groups=all_groups)


@app.route("/groups/add", methods=["GET", "POST"])
def add_group():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Group name is required.", "error")
            return redirect(url_for("groups"))

        insert_group(session["user_id"], name, description)
        flash("Group added.", "success")
        return redirect(url_for("groups"))

    return render_template("groups/add_group.html")


@app.route("/groups/<int:id>/edit", methods=["GET", "POST"])
def edit_group(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    group = get_group_by_id(id, session["user_id"])
    if group is None:
        abort(404)

    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip() or None

        if not name:
            flash("Group name is required.", "error")
            return redirect(url_for("edit_group", id=id))

        update_group(id, session["user_id"], name, description)
        flash("Group updated.", "success")
        return redirect(url_for("groups"))

    questions   = get_questions_by_group(id, session["user_id"])
    all_answers = get_all_answers(session["user_id"])
    return render_template("groups/edit_group.html", group=group, questions=questions,
                           all_answers=all_answers)


@app.route("/groups/<int:id>/delete", methods=["GET", "POST"])
def delete_group_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    group = get_group_by_id(id, session["user_id"])
    if group is None:
        abort(404)

    if request.method == "POST":
        delete_group(id, session["user_id"])
        flash("Group deleted.", "success")
        return redirect(url_for("groups"))

    return render_template("groups/delete_group.html", group=group)


# ------------------------------------------------------------------ #
# Questions                                                           #
# ------------------------------------------------------------------ #

@app.route("/groups/<int:group_id>/questions/add", methods=["POST"])
def add_question(group_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    group = get_group_by_id(group_id, session["user_id"])
    if group is None:
        abort(404)

    text        = request.form.get("text", "").strip()
    description = request.form.get("description", "").strip() or None

    if not text:
        flash("Question text is required.", "error")
    else:
        insert_question(session["user_id"], group_id, text, description)
        flash("Question added.", "success")

    return redirect(url_for("edit_group", id=group_id))


@app.route("/groups/<int:group_id>/questions/<int:q_id>/edit", methods=["GET", "POST"])
def edit_question_route(group_id, q_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    question = get_question_by_id(q_id, session["user_id"])
    if question is None or question["group_id"] != group_id:
        abort(404)

    group = get_group_by_id(group_id, session["user_id"])
    if group is None:
        abort(404)

    if request.method == "POST":
        text        = request.form.get("text", "").strip()
        description = request.form.get("description", "").strip() or None

        if not text:
            flash("Question text is required.", "error")
            return redirect(url_for("edit_question_route", group_id=group_id, q_id=q_id))

        update_question(q_id, session["user_id"], text, description)
        flash("Question updated.", "success")
        return redirect(url_for("edit_group", id=group_id))

    assigned   = get_assigned_answers_for_question(q_id, session["user_id"])
    unassigned = get_unassigned_answers_for_question(q_id, session["user_id"])
    return render_template("groups/edit_question.html",
                           group=group, question=question,
                           assigned_answers=assigned, unassigned_answers=unassigned)


@app.route("/groups/<int:group_id>/questions/<int:q_id>/delete", methods=["POST"])
def delete_question_route(group_id, q_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    question = get_question_by_id(q_id, session["user_id"])
    if question is None:
        abort(404)

    delete_question(q_id, group_id, session["user_id"])
    return redirect(url_for("edit_group", id=group_id))


# ------------------------------------------------------------------ #
# Question assignment (fetch-based JSON)                              #
# ------------------------------------------------------------------ #

@app.route("/groups/<int:group_id>/questions/<int:q_id>/assign", methods=["POST"])
def assign_answer_route(group_id, q_id):
    if not session.get("user_id"):
        return jsonify({"ok": False}), 401
    question = get_question_by_id(q_id, session["user_id"])
    if question is None or question["group_id"] != group_id:
        return jsonify({"ok": False}), 404
    answer_id_str = request.form.get("answer_id", "")
    if not answer_id_str.isdigit():
        return jsonify({"ok": False}), 400
    assign_answer(q_id, int(answer_id_str), session["user_id"])
    return jsonify({"ok": True})


@app.route("/groups/<int:group_id>/questions/<int:q_id>/unassign", methods=["POST"])
def unassign_answer_route(group_id, q_id):
    if not session.get("user_id"):
        return jsonify({"ok": False}), 401
    question = get_question_by_id(q_id, session["user_id"])
    if question is None or question["group_id"] != group_id:
        return jsonify({"ok": False}), 404
    answer_id_str = request.form.get("answer_id", "")
    if not answer_id_str.isdigit():
        return jsonify({"ok": False}), 400
    unassign_answer(q_id, int(answer_id_str), session["user_id"])
    return jsonify({"ok": True})


# ------------------------------------------------------------------ #
# Answers                                                             #
# ------------------------------------------------------------------ #

@app.route("/answers")
def answers():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("answers/list.html", answers=get_all_answers(session["user_id"]))


@app.route("/answers/add", methods=["GET", "POST"])
def add_answer():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        short_desc  = request.form.get("short_desc", "").strip()
        description = request.form.get("description", "").strip() or None
        link        = request.form.get("link", "").strip() or None

        if not short_desc:
            flash("Short description is required.", "error")
            return redirect(url_for("answers"))

        insert_answer(session["user_id"], short_desc, description, link)
        flash("Answer added.", "success")
        return redirect(url_for("answers"))

    return render_template("answers/add_answer.html")


@app.route("/answers/<int:id>/edit", methods=["GET", "POST"])
def edit_answer(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    answer = get_answer_by_id(id, session["user_id"])
    if answer is None:
        abort(404)

    if request.method == "POST":
        short_desc  = request.form.get("short_desc", "").strip()
        description = request.form.get("description", "").strip() or None
        link        = request.form.get("link", "").strip() or None

        if not short_desc:
            flash("Short description is required.", "error")
            return redirect(url_for("answers"))

        update_answer(id, session["user_id"], short_desc, description, link)
        flash("Answer updated.", "success")
        return redirect(url_for("answers"))

    return render_template("answers/edit_answer.html", answer=answer)


@app.route("/answers/<int:id>/delete", methods=["GET", "POST"])
def delete_answer_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    answer = get_answer_by_id(id, session["user_id"])
    if answer is None:
        abort(404)

    if request.method == "POST":
        delete_answer(id, session["user_id"])
        flash("Answer deleted.", "success")
        return redirect(url_for("answers"))

    return render_template("answers/delete_answer.html", answer=answer)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
