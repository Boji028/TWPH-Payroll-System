# Add Scheduling Automation

## What
Extends the existing forward-looking Scheduling feature (per-day
`ScheduledShift`/`ShiftType`) with a weekly rotation layer, matching how
shifts actually work: each employee has a fixed Opening/Closing shift for
a whole week that flips the next week, plus a fixed weekly rest day that
never flips. Adds: a permanent rest-day attribute on Employee, a weekly
auto-rotation script, a one-row-per-employee weekly view, per-week admin
overrides that survive the next rotation, a self-service "this week"
banner, and an Excel export.

## Data model
- `Employee.rest_day` (`app/models/employee.py`): `db.Integer`, 0=Monday
  ..6=Sunday (`date.weekday()` convention), default 6 (Sunday). Fixed
  default - does not flip weekly.
- `WeeklyShiftAssignment` (`app/models/schedule.py`): one row per employee
  per Monday-start week - `employee_id, week_start_date, shift_type
  (OPENING/CLOSING only), rest_day, is_override, created_by_id,
  created_at, updated_at`. Unique constraint `(employee_id,
  week_start_date)`. Source of truth for the weekly view and for durable
  per-week overrides.
- `ShiftType` is unchanged (still just `OPENING`/`CLOSING`) - no `REST`
  member was added. **A rest day is represented purely as the absence of
  a `ScheduledShift` row for that date.** This reuses the exact mechanism
  `biometric_import_service._derive_status` already has for "no schedule
  data" (`shift is None` -> never scored `"absent"`), so the "a rest day
  must never be an absence" requirement needed zero logic changes there -
  only clarifying comments (see that file and `payroll_service.py`).
  Adding a `ShiftType.REST` member instead was considered and rejected: it
  would have required a Postgres `ALTER TYPE ... ADD VALUE` migration,
  `None`-safe guards everywhere `shift.start_time` is used, and a new
  guarded branch in `_derive_status` - all to reimplement a guarantee the
  codebase already had for free.
- `WEEKDAY_LABELS` and `week_start_for(d)` live in `schedule.py` (not
  duplicated in `employee.py`).

## Services
- `app/services/schedule_rotation_service.py` - `generate_week(week_start_date,
  created_by_id)`. Two-phase, deterministic (ordered by employee id):
  phase 1 flips continuing employees' Opening/Closing from the prior week
  (skipping - but still counting - any week already marked
  `is_override=True`); phase 2 balances new hires (no prior-week row) to
  whichever shift has fewer people so far, tie-break Opening, updating the
  running count immediately so several new hires in one run split evenly.
  Then expands each employee's assignment into 7 `ScheduledShift` rows via
  `sync_scheduled_shifts_for_week` - 6 working days upserted, the rest-day
  date's row deleted if one exists (handles a stale row from the old daily
  tool or a prior week's different rest day). Idempotent - safe to re-run
  for the same week before it starts.
- `app/services/schedule_export_service.py` - `render_weekly_schedule_xlsx(assignments)`,
  `openpyxl.Workbook()` -> bytes, mirrors `pdf_service.py`'s
  bytes-returning-function pattern.

## Routes
`schedule_bp`:
- `GET /schedule/weekly?week=YYYY-MM-DD` - one row per active employee
  (shift + rest day for that week; "Not yet generated" if no row exists).
- `GET/POST /schedule/weekly/<employee_id>/edit?week=...` - admin override
  for one employee/one week (`WeeklyAssignmentForm`, real WTForms CSRF).
  Always sets `is_override=True` and re-syncs that employee's 7
  `ScheduledShift` rows for the week.
- `GET /schedule/weekly/export?week=...` - streams the `.xlsx`.

`self_service_bp.dashboard()` now also looks up the employee's current-week
`WeeklyShiftAssignment` and shows it as a Bootstrap alert banner if found -
no seen/unseen tracking, deliberately simple; it always reflects the
latest rotation or override with no extra schema.

## Script
`weekly_shift_rotation.py` (repo root) - run weekly via Windows Task
Scheduler. No reference Task Scheduler script existed anywhere in this
repo (confirmed by search), so this establishes a fresh convention:
`argparse` for an optional `--week` override, `create_app()` +
`app.app_context()` (matching `seed_admin.py`), `try/except` with
`db.session.rollback()` and `sys.exit(1)` on failure. Attributes each run
to the first `User` with `role="owner"`. Docstring includes the `schtasks`
registration command. Manually smoke-tested against the dev database:
new-hire balancing, week-over-week flipping, idempotent re-run, and
override survival all confirmed directly against Postgres before writing
automated tests.

## Testing
- `tests/integration/test_weekly_schedule.py` (11 tests): new-hire
  balancing (single and multiple), week-over-week flip, idempotent re-run,
  override survives a later rotation run, rest day never gets a
  `ScheduledShift` row (and a stale one is removed), weekly view/edit/export
  routes, employee role blocked from admin weekly routes, self-service
  dashboard banner.
- Existing `test_derive_status_no_shift_and_no_punch_is_none_caller_skips`
  (`tests/unit/test_biometric_import_service.py`) already covers the exact
  rest-day-safety contract this feature depends on - no changes needed
  there since the behavior itself didn't change, only the comment
  explaining why it matters.
- Full suite re-run after the change: 77 passed, 1 skipped (pre-existing
  WeasyPrint/Pango gap, unrelated).

## Modified files
- `app/models/employee.py` - `rest_day` column.
- `app/models/schedule.py` - `WEEKDAY_LABELS`, `week_start_for`,
  `WeeklyShiftAssignment`.
- `app/forms/employee_forms.py`, `app/templates/employees/form.html` -
  `rest_day` field, same row as `biometric_id`.
- `app/forms/schedule_forms.py` (new) - `WeeklyAssignmentForm`.
- `app/services/schedule_rotation_service.py`,
  `app/services/schedule_export_service.py` (new).
- `app/routes/schedule_routes.py` - weekly view/edit/export routes.
- `app/routes/self_service_routes.py` - dashboard banner lookup.
- `app/templates/schedule/weekly.html`, `weekly_edit.html` (new),
  `app/templates/self_service/dashboard.html`, `app/templates/base.html`
  (new "Weekly Schedule" sidebar link).
- `app/templates/schedule/log.html` - date now picked via a GET reload
  (like `list.html`'s date-jump form), rotation-managed employees show as
  read-only text + a link instead of an editable dropdown, warning banner
  when applicable. `app/templates/schedule/list.html` - "Schedule Shifts"
  link now carries the currently-viewed date through.
- `app/services/biometric_import_service.py`,
  `app/services/payroll_service.py` - comments only, flagging the rest-day
  safety guarantee for whoever builds absence-proration/statutory
  deductions later.
- `weekly_shift_rotation.py` (new, repo root).
- `migrations/versions/788a7835d775_add_employee_rest_day_and_weekly_shift_.py` -
  hand-edited to add `server_default=sa.text('6')` on `rest_day` (so the
  `NOT NULL` add backfills existing employee rows atomically) and to use
  `sqlalchemy.dialects.postgresql.ENUM(..., create_type=False)` for
  `shift_type` (the generic `sa.Enum` doesn't forward `create_type`, and
  without it Alembic tried to `CREATE TYPE shifttype` again and failed with
  `DuplicateObject` since that type already exists from the original
  `scheduled_shifts` migration).

## Daily tool vs. weekly rotation - resolved
The old daily bulk tool (`schedule/log.html` / `log_schedule`) originally
had no knowledge of `WeeklyShiftAssignment`, so an admin could hand-edit a
single day there for an employee whose whole week is actually managed by
rotation, and that edit would silently get overwritten the next time the
week resynced. Fixed:
- `log_schedule` now checks, per selected date, which employees already
  have a `WeeklyShiftAssignment` for that week (auto-generated or
  override) via `_rotation_controlled_employee_ids`.
- Those employees' rows in `schedule/log.html` no longer show an editable
  dropdown - just their rotation-assigned shift as text and a link to
  `/schedule/weekly/<id>/edit` for that week.
- The `POST` handler skips those employee IDs entirely regardless of what
  was submitted for them, so this is enforced server-side, not just
  hidden in the UI (a hand-crafted POST can't bypass it either).
- A warning banner explains why when any employees on the selected date
  are rotation-managed.
- Employees with no `WeeklyShiftAssignment` for that week (e.g. their week
  hasn't been generated yet) remain freely editable via the daily tool, as
  before.

Covered by `test_daily_tool_hides_dropdown_and_warns_for_rotation_managed_week`
and `test_daily_tool_post_never_touches_rotation_managed_employees` in
`tests/integration/test_weekly_schedule.py`.

## Task Scheduler registration
Same setup as Travel Worthy PH's inquiry-cleanup task (found in the
sibling `TravelWorthyPH` project - `run_inquiry_cleanup.bat` /
`setup_inquiry_cleanup_scheduler.ps1`): a `.bat` wrapper plus a PowerShell
registration script, rather than a raw `schtasks` one-liner.
- `run_weekly_rotation.bat` (repo root) - activates the venv, runs
  `weekly_shift_rotation.py`, checks `%errorlevel%` for success/failure.
  Deliberately drops the trailing `pause` that the inquiry-cleanup
  `.bat` has - that's fine for a manual double-click test, but would hang
  forever waiting for a keypress when Task Scheduler runs it unattended.
- `setup_weekly_rotation_scheduler.ps1` - registers `run_weekly_rotation.bat`
  as a weekly Task Scheduler task via `Register-ScheduledTask` (default:
  Sunday 10:00 PM). Must run as Administrator; same admin-check/
  `New-ScheduledTask*` structure as the reference script, `-Weekly
  -DaysOfWeek` instead of `-Daily`. Fixed after the first real run: the
  reference script's `New-ScheduledTaskSettingsSet` call included
  `-RunWithoutNetwork`, which doesn't exist as a parameter on this
  system's `ScheduledTasks` module (`Get-Command
  New-ScheduledTaskSettingsSet -Syntax` confirms it). Removed it - no
  replacement needed, since the task already runs regardless of network
  availability by default as long as `-RunOnlyIfNetworkAvailable` (which
  we don't want) isn't set. Verified the corrected
  trigger/action/settings/principal object construction succeeds without
  actually calling `Register-ScheduledTask` (that step needs a real
  Administrator run to test, left to the user).
- `setup_weekly_rotation_scheduler.bat` - elevates and runs the `.ps1`
  above, so no manual "Run as Administrator" PowerShell window is needed.
  Fixed after the first real run: it originally called `powershell` bare
  (relying on PATH) and used `Start-Process` without `-Wait -PassThru`, so
  it printed "Setup complete!" unconditionally even when PowerShell
  wasn't found on PATH and the elevated script never ran at all. Now
  calls `powershell.exe` by its full path
  (`%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`) and
  waits for the elevated process, checking its actual exit code
  (`$p.ExitCode`) before printing success - a genuine failure now prints
  a clear "Setup FAILED" message with the error code instead. Verified
  both branches with a throwaway test harness mimicking the same nested
  `powershell.exe` structure (inner process exiting 0 vs. 1) before
  applying the fix to the real script, without triggering an actual UAC
  prompt.

## Still to do
- Run `setup_weekly_rotation_scheduler.bat` on the production machine to
  actually register the task (not done as part of this change - creating
  a real Task Scheduler entry is a system-level action, left for the user
  to run deliberately) and confirm the day/time (default Sunday 10:00 PM).
- Set each existing employee's real `rest_day` in the UI - the migration
  defaulted everyone to Sunday (6), which is very likely wrong for some
  employees.
- Manually check the new pages (`/schedule/weekly`, the edit form, the
  `.xlsx` download, the self-service banner) render correctly with the
  actual Option K styling in a browser (only verified via test client and
  direct DB inspection here).
