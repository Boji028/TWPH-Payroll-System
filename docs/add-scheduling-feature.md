# Add Scheduling feature

## What
Forward-looking shift scheduling: staff assign one of two fixed shifts
(Opening 8:00 AM-6:00 PM, Closing 11:30 AM-8:00 PM) to an employee for a
given date. Deliberately independent of Attendance (what happened) and
Payroll (no automatic effect - same treatment as LeaveRequest).

## Data model
`ScheduledShift` (`app/models/schedule.py`): employee_id, date, shift_type
(Enum: opening/closing), created_by_id, created_at. One shift per
employee per day, enforced with a DB-level unique constraint
(`uq_employee_schedule_date`) - confirmed with a test that inserting a
second row for the same employee/date raises IntegrityError.

Shift hours (8:00-18:00 / 11:30-20:00) are fixed Python constants in the
model file (`SHIFT_HOURS`), not a separate editable lookup table - there
are only two shift types and they rarely change, so a full CRUD table
would be over-engineering for now. Add an entry to `SHIFT_HOURS` and to
the `<select>` in `schedule/log.html` if a third shift type is ever needed.

## Routes
Admin (`schedule_bp`, mirrors `attendance_routes.py` exactly):
- `GET /schedule/` - view a date's schedule (defaults to today, `?date=`
  to view another day, plus a small date-jump form since Attendance's
  equivalent page has no way to change the date from the UI at all)
- `GET/POST /schedule/log` - bulk per-employee shift assignment for one
  date, same plain-`<form>` + manual `csrf_token` input pattern as
  `attendance/log.html` (not a WTForms class, matching that file).
  Picking "-- Not scheduled --" for someone who already has a shift that
  day deletes their existing assignment - Attendance's version doesn't
  do this (blank hours are just skipped, not cleared), but scheduling
  needs an explicit way to unassign someone, so this diverges slightly
  on purpose.

Self-service (`self_service_bp`):
- `GET /my/schedule` - read-only list of the employee's own upcoming
  shifts (date >= today), sorted ascending. Plain table, not a calendar
  widget - matches every other self-service list page (payslips, leave,
  documents, performance), and nothing else in the app uses a calendar
  UI.

## Testing
- `tests/integration/test_schedule.py` (6 tests): staff can schedule a
  shift, re-submitting updates rather than duplicates, blank selection
  clears an existing shift, the DB-level unique constraint actually
  fires on a direct double-insert, an employee only sees their own
  future (not past) shifts, employee role is blocked from admin routes
- Added `test_log_schedule_form_submits_with_csrf_token` to the existing
  `test_csrf.py` (real CSRF enabled), matching the precedent set after
  the missing-CSRF-token bug class found in log_attendance/payroll forms
- Full suite re-run after the change: 38 passed, 1 skipped (pre-existing
  WeasyPrint/Pango gap, unrelated)

## Modified files
- `app/routes/self_service_routes.py` - added the `/my/schedule` route
  and its imports (full file - already grown large across sessions, full
  swap avoids ambiguity about where to insert)
- `app/models/__init__.py`, `app/__init__.py` - registered the new model
  and blueprint (`/schedule` prefix)
- `app/templates/base.html` - added "Scheduling" to the staff sidebar
  (after Workforce) and "My Schedule" to the self-service sidebar (after
  My Attendance)

## Still to do
- **Run `flask db migrate` and `flask db upgrade`** - this one DOES add a
  new table (`scheduled_shifts`), unlike the Workforce feature
- Manually check the new pages render correctly with your actual Option K
  styling in a browser (only verified via test client here)
