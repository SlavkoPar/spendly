# Spec: Profile Page

## Overview
put hard coded categories to SQL table

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/categories` must be a protected route)

## Routes
- GET /categories — render the categories page

## Database changes

- in table expenses replace field category with 
     category_id | INTEGER | Foreign key → categories.id, not null |


## Create table
### categories

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → users.id, not null |
| name | TEXT | Not null |
| description | TEXT | Nullable |
| created_at | TEXT | Default datetime('now') |

## 12. Expected Behavior

- `seed_db()`:
    - inserts categories data only once, set user_id equal to 1
      -- Food
      -- Transport
      -- Bills
      -- Health
      -- Entertainment
      -- Shopping
      -- Other
    - does not duplicate records on multiple runs
- Database enforces:
    - valid foreign key relationships

## Templates
- Create: `templates/categories.html`
- All templates as we did for expenses
- Open Modal when click od "Edit" 
- Modal width: 60% height: 80%
- keep vertical scroll position after update

## Files to change
- `app.py` 
 
- `database\queries.py` add queries for categories, get ALL categories

## Files to create
- `templates/categories/list.html`
- `templates/categories/add_category.html`
- `templates/categories/edit_category.html`
- `templates/categories/delete_category.html`

## New dependencies
No new dependencies.

## Rules for implementation
- remove hardcoded CATEGORIES, use all categories from SQL table, use field 'name'
- display all categories, regardless of user
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` if any DB call is ever needed
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- All data passed to the template must be hardcoded Python dicts/lists in `app.py` — no DB queries in this step
- Category badges must use a CSS class, not inline colour styles

## Definition of done
- [ ] Visiting `/categories` without being logged in redirects to `/login`
