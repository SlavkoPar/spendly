# Spec: Edit Expense

## Overview
Edit expense in modal
## Depends on
- Step 1: Database setup (`expenses` table exists with all required columns)
- Step 3: Login / Logout (`session["user_id"]` is set and enforced)
- Step 5: Profile page renders transactions (the edit link lives there)
- Step 7: Add Expense (establishes the form pattern this step follows)

## Routes


## Database changes

## Templates

- **Modify**: `templates/profile.html`
  - Open Modal when click od "Edit" 
  - Modal width: 60% height: 80%
  - keep vertical scroll position after update

## Files to change

- `templates/profile.html`
  - make button instead of link to edit expense

## Files to create

## New dependencies
No new dependencies.

## Rules for implementation
- After a successful update, redirect to `url_for("profile")` — do NOT render
  the form again
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ — never £ or $

## Tests to write
File: `tests/test_edit_expense.py`

### Unit tests

### Route tests


## Definition of done
