# 2026-07-22 — Leave / Time-Off Tracking

## What was built
- `LeaveRequest` model: employee, type (vacation/sick/unpaid/other), date
  range, optional reason, status (pending/approved/rejected), who
  reviewed it and when
- Employee side: `GET/POST /my/leave` — submit a request, see history of
  your own (in the new `self_service/leave.html`)
- Admin side: new `leave` blueprint at `/leave` — pending queue plus the
  last 20 reviewed, with approve/reject actions; re-reviewing an
  already-decided request is blocked with a flash message rather than
  silently overwriting it
- Nav links added both sides: "Leave Requests" for staff, "My Leave" for
  employees
- New migration `f3e10a571f27_add_leave_requests_table.py`

## Decision carried over from planning
- Approving a leave request is a record only — it does **not** affect
  payroll computation. Same deferred treatment as statutory deductions;
  `LeaveRequest` is unrelated to `Attendance`'s existing `'leave'`
  status. If you want approved leave to reduce a daily/hourly employee's
  pay (or count against a leave allowance), that's a deliberate decision
  to make later, not something this defaults to.

## Bug found and fixed along the way — this one's more serious
While building the approve/reject forms, testing with CSRF protection
actually turned on (rather than the test suite's `WTF_CSRF_ENABLED =
False`) surfaced that **three existing forms had no CSRF token at all**:
- "Log Attendance" (`attendance/log.html`)
- "New Payroll Run" (`payroll/new.html`)
- "Process Payroll Run" (`payroll/view.html`)

`CSRFProtect` is on globally (`app/extensions.py`), so outside of tests
every submit of those three forms would fail with `400 The CSRF token
is missing.` — this wasn't introduced by anything in this session, it's
been there since the original scaffold, just never exercised locally
before now (`seed_admin.py`/manual testing so far apparently hadn't hit
"Process Payroll Run" or "New Payroll Run" yet). Fixed by adding
`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` to
each. Confirmed all three submit correctly with CSRF protection on, in
addition to the new leave-request forms.

## Verified
- Employee submits a request, sees it in their own history; invalid
  date range (end before start) is rejected with a field error
- Admin sees it in the pending queue, approves it; re-approving the
  same request is blocked
- Employee blocked (403) from `/leave/` admin routes; staff with no
  linked employee record gets 404 on `/my/leave`, as expected
- All of the above tested with `WTF_CSRF_ENABLED = True` (Flask-WTF's
  actual default), not just the test suite's relaxed config — this is
  what caught the three-form bug above
- Existing `pytest` suite (3 tests) still passes

## Explicitly deferred
- All three originally-planned features are now built: employee
  self-service login, downloadable payslip PDFs, leave/time-off
  tracking
- Still open, same as before: statutory deductions (SSS, PhilHealth,
  Pag-IBIG, BIR), and whether approved leave should affect payroll
