# CLAUDE.md — Payroll System Conventions

This file defines the working standard for all contributions to this project,
following the same convention as Travel Worthy PH.

## Stack
- Flask + SQLAlchemy + PostgreSQL + Flask-Login + Flask-WTF
- Jinja2 templates + Bootstrap 5 (CDN, no build step)
- No JS framework — vanilla JS only where it earns its place

## Architecture
- `routes/` — Blueprints; thin, handle request/response only
- `services/` — business logic (payroll math, payslip generation); testable independently of Flask
- `models/` — SQLAlchemy models; the data-access layer, no separate repository layer
- `forms/` — Flask-WTF form classes; validation lives here, not in routes

## Conventions
- Every implementation task gets a `docs/` activity log entry
- Commit format: three separate commands, never chained with `&&`:
  ```
  git add .
  git commit -m "..."
  git push origin main
  ```
- Small code changes: send replacement code inline in chat rather than as a zip
- Statutory deductions (SSS, PhilHealth, Pag-IBIG, BIR withholding tax) are
  NOT implemented — deferred until confirmed with the business owner. See
  the note at the top of `app/services/payroll_service.py` before adding them.

## Not yet decided
- Whether statutory deductions are in scope
- Deployment target (TWP uses Render — likely candidate but not confirmed for this project)

## General Principles
- Generate concise, short solutions for new modules or code.
- Watch for over-engineering, oversized files needing refactor.
- Watch for weird syntax/style mismatching rest of codebase.
- Watch for obvious bugs.
- Prioritize concise, precise code and docs changes.
- No emojis or special characters in comments.
- Write activity-log.md in docs to refer back if confused.
- Make to-do list, run major changes by user first.
- Review existing files before refactor and change.
- Markdown files use kebab naming (ex. some-description-changes.md).
- Don't auto-commit activity logs and docs.
- Comments: one-liner, one sentence.

## Code Quality
- Right data structures and algorithms for problems.
- Don't expose data needlessly (least privilege).
- No external libraries unless absolutely necessary.
- Use project dependency file for correct versions.
- Avoid redundancy unless improves usability.

## Version Control
- Commit after significant changes with clear messages.
- Keep commits focused, atomic.
- No auto-push any branch.

## AI Restrictions
- No customer personal data - names, contacts, account numbers, transactions (unless approved exemptions).
- No credentials - passwords, API keys, tokens, connection strings.
