"""These tests run with CSRF protection actually ON, unlike the rest of
the suite (conftest.py's TestingConfig sets WTF_CSRF_ENABLED = False).
That relaxed default is why three existing forms shipped with no CSRF
token at all and nobody noticed until testing manually with a real
config — see docs/2026-07-22-leave-tracking.md. These tests exist so
that class of bug can't silently come back."""
import re
from datetime import date
from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.employee import Employee
from app.models.payroll import PayrollRun


@pytest.fixture
def csrf_app():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def csrf_client(csrf_app):
    return csrf_app.test_client()


def _token(html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m, "no csrf_token field found on the page — form is missing csrf_token()"
    return m.group(1)


def _login(csrf_app, client, role="owner"):
    with csrf_app.app_context():
        user = User(full_name="Owner Admin", email="owner@example.com", role=role)
        user.set_password("ownerpass1")
        _db.session.add(user)
        _db.session.commit()
    token = _token(client.get("/auth/login").get_data(as_text=True))
    client.post("/auth/login", data={"csrf_token": token, "email": "owner@example.com", "password": "ownerpass1"})


def test_login_form_has_csrf_token(csrf_client):
    _token(csrf_client.get("/auth/login").get_data(as_text=True))


def test_log_attendance_form_submits_with_csrf_token(csrf_app, csrf_client):
    _login(csrf_app, csrf_client)
    token = _token(csrf_client.get("/attendance/log").get_data(as_text=True))
    r = csrf_client.post("/attendance/log", data={"csrf_token": token, "date": "2026-07-22"})
    assert r.status_code == 302


def test_new_payroll_run_form_submits_with_csrf_token(csrf_app, csrf_client):
    _login(csrf_app, csrf_client)
    token = _token(csrf_client.get("/payroll/new").get_data(as_text=True))
    r = csrf_client.post("/payroll/new", data={
        "csrf_token": token, "period_start": "2026-08-01", "period_end": "2026-08-15",
    })
    assert r.status_code == 302


def test_process_payroll_run_form_submits_with_csrf_token(csrf_app, csrf_client):
    with csrf_app.app_context():
        run = PayrollRun(
            period_start=date(2026, 7, 1), period_end=date(2026, 7, 15), status="draft",
        )
        _db.session.add(run)
        _db.session.commit()
        run_id = run.id

    _login(csrf_app, csrf_client)
    token = _token(csrf_client.get(f"/payroll/{run_id}").get_data(as_text=True))
    r = csrf_client.post(f"/payroll/{run_id}/process", data={"csrf_token": token})
    assert r.status_code == 302


def test_employee_login_form_submits_with_csrf_token(csrf_app, csrf_client):
    with csrf_app.app_context():
        emp = Employee(
            employee_code="EMP-001", first_name="Maria", last_name="Santos",
            pay_type="hourly", hourly_rate=Decimal("95"), date_hired=date(2025, 1, 1),
        )
        _db.session.add(emp)
        _db.session.commit()
        emp_id = emp.id

    _login(csrf_app, csrf_client)
    token = _token(csrf_client.get(f"/employees/{emp_id}/login").get_data(as_text=True))
    r = csrf_client.post(f"/employees/{emp_id}/login", data={
        "csrf_token": token, "email": "maria@example.com", "password": "mariapass1",
    })
    assert r.status_code == 302
