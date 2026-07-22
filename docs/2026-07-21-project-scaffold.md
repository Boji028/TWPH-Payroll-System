# 2026-07-21 — Initial Project Scaffold

## What was built
- Full Flask app factory structure (`app/__init__.py`, `config.py`, `extensions.py`)
- Models: `User` (staff login), `Employee`, `Attendance`, `PayrollRun`, `Payslip`, `Deduction`
- Blueprints: `auth`, `main`, `employee`, `attendance`, `payroll`
- Core payroll computation in `services/payroll_service.py` — supports monthly,
  daily, and hourly pay types with overtime calculation
- Jinja2 templates styled with Bootstrap 5 (CDN, no build step)
- `seed_admin.py` script to create the first login
- `CLAUDE.md` conventions file

## Decisions made
- Stack: Flask + Jinja2 + SQLAlchemy + PostgreSQL + Bootstrap, matching Travel Worthy PH conventions
- No separate REST API layer — server-rendered HTML throughout
- No JS framework — vanilla JS added only where needed later

## Explicitly deferred
- Statutory deductions (SSS, PhilHealth, Pag-IBIG, BIR withholding tax) — not yet
  confirmed whether in scope. `Deduction` model is generic enough to support this
  later without a schema change.
- Deployment target not yet chosen

## Next steps
- Set up PostgreSQL database and run first migration
- Run `seed_admin.py` to create first login
- Test the employee → attendance → payroll run → payslip flow end to end
