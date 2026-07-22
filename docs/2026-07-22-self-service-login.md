# 2026-07-22 — Employee Self-Service Login

## What was built
- `User` model extended with a nullable, unique `employee_id` FK to `Employee`
  (`role` gains `"employee"` as a fourth value, alongside `owner`/`hr`/`staff`)
- New `app/decorators.py` — `staff_required` (login + role check in one
  decorator), applied across `employee`, `attendance`, `payroll`, and the
  admin `dashboard` route in place of plain `login_required`
- New `self_service` blueprint at `/my` — dashboard, attendance history,
  payslip list, and a single-payslip view, all scoped to
  `current_user.employee` with an ownership check on the payslip detail
  route (403 if the payslip belongs to someone else)
- Admin-side "manage login" flow: `/employees/<id>/login` creates or
  updates the `User` account linked to an employee (no email invite —
  the password is shared directly), with a duplicate-email check before
  saving
- `base.html` nav is now role-aware: staff roles see the existing admin
  nav (plus a "My Payslips" link if they're also linked to an employee
  record); `employee` role sees a simplified self-service nav
- New migration `b95954536efa_add_employee_id_to_users.py`

## Bug found and fixed along the way
- The login route always redirected to `/dashboard` regardless of role.
  Once `dashboard` became `staff_required`, that meant every employee
  login landed on a 403 immediately after a correct password. Fixed by
  branching the post-login redirect on `user.role`.

## Decisions made
- Reused the existing `User`/Flask-Login setup instead of a second login
  system — `User.employee_id` links a login to the employee it belongs
  to, matching the model's own docstring ("an owner or HR staffer would
  have both")
- No email-sending in this codebase, so employee logins are handed to
  staff to share directly rather than an invite flow

## Explicitly deferred
- Downloadable payslip PDFs (self-service payslip view is HTML-only for now)
- Leave/time-off tracking
- Employees cannot self-log their own attendance yet — logging stays an
  admin-only action in `attendance.log_attendance`

## Verified
- Ran the full flow locally (SQLite, in-memory): staff login → admin
  routes; employee login → `/my/` routes; employee blocked (403) from
  admin routes and from another employee's payslip; admin create-login
  flow creates a working employee account; existing `pytest` suite
  (3 tests) still passes
