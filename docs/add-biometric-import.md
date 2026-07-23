# Add biometric scanner attendance import

## What
Staff can upload the .xls export from the fingerprint scanner and have it
derive Present/Late/Absent per employee per day automatically, instead of
typing attendance in by hand. Built and tested against a real sample
export Boji provided (`tests/fixtures/sample_biometric_export.xls`,
9 employees x 16 days, May 26-June 10 2026 period).

## The file format (why the parser looks the way it does)
The vendor's report buckets each punch into "Before Noon / After Noon /
Overtime" In/Out columns using its own internal logic, and that
categorization is inconsistent - the real sample file has a punch sitting
in "Before Noon Out" with no matching "In" on the same day, and single
stray punches landing under "Overtime Out". Replicating that vendor
logic exactly would be fragile. Instead the parser ignores which bucket
a punch landed in: for each employee/day it collects every punch present
and takes the earliest as time_in, latest as time_out - matches what
actually matters here (one effective arrival, one effective departure).

Employee/column positions are located by searching cell text ("Dept.",
"Name", "User ID", "Time Card", "In"/"Out") rather than hardcoded column
numbers, so a future export with a different employee count or grouping
should still parse correctly.

## Status derivation
For each parsed employee/date, looks up that employee's ScheduledShift
(from the Scheduling feature) for that date:
- No ScheduledShift + no punch -> skipped entirely, nothing recorded
  (no basis to judge anything)
- No ScheduledShift + has a punch -> "present" (can't judge lateness
  without an expected start time, but we know they worked)
- Has ScheduledShift + no punch -> "absent"
- Has ScheduledShift + has a punch -> compare time_in to
  shift.start_time + 15 min grace (GRACE_MINUTES in
  biometric_import_service.py) -> "present" or "late"

A day with only one punch (ambiguous - can't tell if it's an arrival or
departure) still gets a status from the logic above, but hours_worked is
forced to 0 and the day is listed under "Needs manual review" on the
results page rather than silently trusted.

Added "late" as a new valid Attendance.status value (was
present/absent/leave/holiday) - updated the manual Log Attendance
dropdown, the Attendance list badge, and workforce_service's status
labels/colors to match, so Late shows consistently everywhere status is
displayed.

## New: Employee.biometric_id
The scanner identifies people with a numeric User ID that has nothing to
do with employee_code. Added a nullable, unique `biometric_id` string
column to Employee, exposed on the existing Add/Edit Employee form (no
new page) - **this needs to be filled in per employee before an import
will match anything.** Testing used made-up placeholder mappings; real
values still need to be set through the Employee edit form.

## Import route
`GET/POST /attendance/import` (staff_required), linked from the
Attendance list page next to "Log Attendance". Upload form is a small
new FlaskForm (`BiometricImportForm`, `.xls` only - that's the confirmed
real format, `.xlsx` isn't handled since xlrd 2.x dropped that support
and it isn't needed for now). Results page shows created/updated counts,
unmatched scanner User IDs (punches with no matching employee), and the
needs-review list.

Re-running the same file is safe - upserts by (employee_id, date), not
insert-only.

## New dependency
`xlrd` - needed because `.xls` (legacy Excel/OLE2 format) isn't readable
by openpyxl, which only handles `.xlsx`. Not in requirements.txt yet.

## Testing
- `tests/unit/test_biometric_import_service.py` (11 tests) - parser
  correctness against the real fixture file (all 9 users x 16 days
  parsed, dates in order, the inconsistent-bucketing case specifically
  verified against known values from the real file, zero-punch users
  handled), plus `_derive_status` logic in isolation including the exact
  15-minute grace boundary for both shift types
- `tests/integration/test_biometric_import.py` (3 tests) - full HTTP
  route against the real fixture: derived statuses cross-checked against
  hand-verified values from the actual file (present/absent/late all
  hit), re-running doesn't duplicate, employee role blocked
- Added `test_biometric_import_form_submits_with_csrf_token` to
  `test_csrf.py`, matching established precedent
- Full suite re-run: 53 passed, 1 skipped (pre-existing WeasyPrint gap,
  unrelated)

## Modified files
- `app/models/employee.py` - added `biometric_id`
- `app/forms/employee_forms.py`, `app/templates/employees/form.html` -
  expose it on the existing form
- `app/models/attendance.py` - documented `late` as a valid status
- `app/templates/attendance/log.html` - added Late to the manual dropdown
- `app/templates/attendance/list.html` - added the Import link, and
  upgraded the status cell to a colored badge (was plain text before -
  every other status display in the app uses badges, and it matters more
  now that Late exists)
- `app/services/workforce_service.py` - added late to STATUS_LABELS/
  STATUS_BADGE_CLASSES
- `app/routes/attendance_routes.py` - full file (added the import route)

## Still to do
- **Add `xlrd` to requirements.txt and `pip install` it**
- **Run `flask db migrate` and `flask db upgrade`** - new `biometric_id`
  column on `employees`
- **Set real `biometric_id` values** for each employee via Edit Employee
  before importing real data
- Peso-deduction math (lateness/absence reducing the semi-monthly
  ₱7,500) is intentionally not part of this - separate next step per
  Boji's staging decision
