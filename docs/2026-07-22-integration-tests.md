# 2026-07-22 — Integration Tests for Self-Service, Leave, PDFs, CSRF

## What was built
Four new files under `tests/integration/` (new folder), covering
everything built this session that had zero automated coverage before:

- `test_self_service_access.py` — staff vs employee access control,
  role-aware login redirect, ownership check on another employee's
  payslip, staff-with-no-employee-link 404 on `/my/`
- `test_leave_requests.py` — submit, invalid date range rejected, admin
  approve, re-approving an already-reviewed request is blocked,
  employee blocked from admin leave routes
- `test_payslip_pdf.py` — PDF downloads, and (if `pypdf` is installed)
  extracts the PDF text to check actual values, not just that a PDF
  came out. Skips itself with `pytest.importorskip("weasyprint")` if
  WeasyPrint's native dependency isn't set up — won't fail the suite
  on a machine that hasn't done the MSYS2/Pango steps yet
- `test_csrf.py` — runs with `WTF_CSRF_ENABLED = True` (Flask-WTF's
  actual default), unlike the rest of the suite. Exists specifically
  to catch a repeat of the missing-CSRF-token bug found last session
  (log attendance, new payroll run, process payroll run, employee
  login — all four confirmed to actually submit with a token present)

## Decision made
- Left `conftest.py`'s existing `WTF_CSRF_ENABLED = False` alone rather
  than flipping it globally — that would touch every other test's
  setup. `test_csrf.py` opts into a real config instead, scoped to
  just the forms that matter.

## Verified
- Full suite: 21 passed (3 original + 18 new), 0 failed
