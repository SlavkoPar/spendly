# Spec: Answers

## Overview

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/answers` must be a protected route)

## Routes
- GET /answers — render the answer list page

## Database changes


## Create table
### answers

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| user_id | INTEGER | Foreign key → users.id, not null |
| short_desc | TEXT | Not null |
| description | TEXT | Nullable |
| link | TEXT | Nullable |
| created_at | TEXT | Default datetime('now') |

### question-answers

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | Primary key, autoincrement |
| question_id | INTEGER | Foreign key → questions.id, not null |
| answer_id | INTEGER | Foreign key → answers.id, not null |
| future | TEXT | Nullable |
| user_id | INTEGER | Foreign key → users.id, not null |
| created_at | TEXT | Default datetime('now') |


## 12. Expected Behavior


## Templates
- Create templates for answers 
   -- `templates/answers/list.html`
   -- `templates/answers/add_answer.html`
   -- `templates/answers/edit_answer.html`
   -- `templates/answers/delete_answer.html`

## Files to change
- `app.py` 
- `database\queries.py`

## Files to create
   - `templates/answers/list.html`
   - `templates/answers/add_answer.html`
   - `templates/answers/edit_answer.html`
   - `templates/answers/delete_answer.html`

## New dependencies
No new dependencies.

## Rules for implementation

- add field number of `assigned answers` in table `questions`
- for question row display number of assigned answers
- create section `Assigned answers' in question form
- create modal for selections of answers which are not already assigned


- for answers, and aswers in modal for selection of unassigned answers,  enable autocomplete filter by name
- put link answers in 'base' html
- for answers, set top and bottom paddings to: 3px 
- give differnet styles (background, color, borders, filters) for groups, questions and answers
- set styles:
   .form-input { padding: 0.3rem 0.875rem; }
   .transactions-table td { padding: 0.15rem; }



## Definition of done
- [x] Visiting `/answers` without being logged in redirects to `/login`
