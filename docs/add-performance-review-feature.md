# Add performance review feature

## What
New HRIS module: ad-hoc performance reviews created by admin/HR for an
employee. No manager role or fixed review cycle - staff creates a review
whenever needed.

## Data model
- `PerformanceReview` - one review: title, review_date, status
  (draft/finalized), overall_comments. Draft reviews are staff-only;
  finalizing makes the review visible in self-service and locks it.
- `ReviewRating` - one row per fixed category (job knowledge, quality of
  work, communication, teamwork, punctuality), each scored 1-5 with an
  optional comment. Every review gets all 5 categories.
- `PerformanceGoal` - belongs to the employee, optionally linked to the
  review that created it via `review_id` (nullable). Goals outlive the
  review - deleting a draft review unlinks its goals instead of deleting
  them.

## Routes
Nested under `employee_bp` (same pattern as documents):
- `GET /employees/<id>/performance` - review list + open goals
- `GET/POST /employees/<id>/performance/new` - create (draft)
- `GET /employees/<id>/performance/<review_id>` - detail, add goal, update
  goal status
- `POST .../finalize`, `POST .../delete` (draft only)
- `POST /employees/<id>/goals/<goal_id>/status` - update a goal's status

Self-service (`self_service_bp`):
- `GET /my/performance` - finalized reviews only
- `GET /my/performance/<review_id>` - detail, 403s on drafts or reviews
  belonging to another employee

## Notes
- No service layer added - logic is simple CRUD, same call as
  leave_routes.py (no dedicated service either).
- Fixed the `requests` local variable in `self_service.leave()` shadowing
  the `requests` module import at file scope - harmless today since
  nothing in that function used the module, but fragile. Renamed to
  `requests_`.
- Still need: `flask db migrate` + `flask db upgrade` to create
  `performance_reviews`, `review_ratings`, `performance_goals` tables.
