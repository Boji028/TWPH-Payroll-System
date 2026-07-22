# Payroll System

A Flask-based payroll system for a local business. Supports monthly, daily,
and hourly-rate employees with attendance tracking, payroll runs, and payslip
generation.

## Stack
Flask, SQLAlchemy, PostgreSQL, Flask-Login, Flask-WTF, Jinja2, Bootstrap 5.

## Setup

1. **Create a virtual environment and install dependencies:**
   ```
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up your environment file:**
   ```
   cp .env.example .env
   ```
   Then edit `.env` with your actual `SECRET_KEY` and `DATABASE_URL`.

3. **Create the PostgreSQL database**, then run migrations:
   ```
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

4. **Create your first login:**
   ```
   python seed_admin.py
   ```

5. **Run the app:**
   ```
   python run.py
   ```
   Visit `http://localhost:5000`

## Project Structure

See `CLAUDE.md` for architecture conventions and current implementation status.

## Status

Early scaffold — core CRUD, attendance logging, and payroll run processing
are implemented. Statutory deductions (SSS, PhilHealth, Pag-IBIG, BIR) are
intentionally not yet implemented; see `CLAUDE.md`.
