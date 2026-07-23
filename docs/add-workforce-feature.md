# Add Workforce live roster feature

## What
New "Workforce" section: a live, read-only roster of active employees
showing today's attendance status, inspired by a competitor product
screenshot (MAO Workforce) Boji shared. Two surfaces share one data
source and one polling script:
- Full page at `/workforce/` (new sidebar nav item, staff-only)
- A 6-row preview embedded on the main Dashboard, linking to the full page

Scheduling (forward-looking shift assignment, also seen in the reference
screenshot) was explicitly deferred - it needs a new data model with no
existing equivalent, unlike Workforce which is a live view over data
already tracked (Employee + Attendance).

## How "status" is derived
There's no clock-in/out event stream in this app - `log_attendance`
(existing) only ever sets `hours_worked` and `status` in bulk, `time_in`/
`time_out` on Attendance are unused columns. So "real-time" here means:
whatever's been logged in today's Attendance row so far.
- No Attendance row yet for today -> "Not Logged Yet" (gray)
- status == present/absent/leave/holiday -> mapped 1:1 to a colored badge

As staff fill in the attendance log throughout the day, the roster
picks it up on the next poll tick - no new attendance-logging UI needed.

## New files
- `app/services/workforce_service.py` - `get_workforce_roster(target_date=None, limit=None)`,
  returns JSON-serializable dicts (also used directly as the page's initial
  server-rendered rows, so first paint doesn't wait on JS)
- `app/routes/workforce_routes.py` - `GET /workforce/` (page), `GET /workforce/data`
  (JSON, `?limit=N` supported)
- `app/static/js/workforce.js` - vanilla JS (no framework, per CLAUDE.md), polls
  `/workforce/data` every 20s and re-renders the table body in place
- `app/templates/workforce/list.html`
- `tests/unit/test_workforce_service.py` - 7 tests, all passing

## Modified files
- `app/templates/main/dashboard.html` - added the Workforce widget section,
  extended the existing `scripts` block to init the poller
- `app/routes/main_routes.py` - passes `workforce_preview` (limit=6) into
  the dashboard template
- `app/__init__.py` - registered `workforce_bp` at `/workforce`
- `app/templates/base.html` - added "Workforce" to the staff sidebar nav,
  right after Attendance

## Access control
`workforce_bp` routes use the existing `staff_required` decorator - same
as Employees/Attendance/Payroll/Leave. Confirmed an `employee`-role login
gets 403 on both `/workforce/` and `/workforce/data` (no cross-employee
data leak via the roster).

## Testing
- 7 new unit tests for `workforce_service.get_workforce_roster` (empty
  state, not-logged default, status reflection, cross-day isolation,
  inactive-employee exclusion, limit, department/name ordering) - all pass
- Full existing suite re-run after the change: 15 unit + 16 integration
  passed, 1 skipped (payslip PDF, pre-existing WeasyPrint/Pango gap on
  this machine, unrelated to this change)
- Manual HTTP smoke test: dashboard widget and full page both render with
  real data, JSON endpoint returns correct per-employee status and
  respects `?limit=`, unauthenticated and employee-role requests are
  correctly blocked

## Still to do
- Run `flask db migrate` - not needed, no schema change this time
- Eyeball the widget placement/spacing on the actual Option K dashboard
  styling in a browser (only checked via test client here, not visually)
