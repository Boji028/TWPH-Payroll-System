from datetime import date
from decimal import Decimal
from app.extensions import db as _db
from app.models.user import User
from app.models.employee import Employee


def _staff(email="owner@example.com", role="owner"):
    user = User(full_name="Owner Admin", email=email, role=role)
    user.set_password("ownerpass1")
    return user


def _employee_with_login(code="EMP-001", email="maria@example.com"):
    emp = Employee(
        employee_code=code, first_name="Maria", last_name="Santos",
        pay_type="hourly", hourly_rate=Decimal("95"), date_hired=date(2025, 1, 1),
    )
    _db.session.add(emp)
    _db.session.commit()
    user = User(full_name=emp.full_name, email=email, role="employee", employee_id=emp.id)
    user.set_password("mariapass1")
    _db.session.add(user)
    _db.session.commit()
    return emp, user


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password})


def test_staff_can_access_admin_routes(db, client):
    db.session.add(_staff())
    db.session.commit()
    login(client, "owner@example.com", "ownerpass1")
    assert client.get("/employees/").status_code == 200


def test_employee_blocked_from_admin_routes(db, client):
    _employee_with_login()
    login(client, "maria@example.com", "mariapass1")
    assert client.get("/employees/").status_code == 403


def test_login_redirects_by_role(db, client):
    db.session.add(_staff())
    _employee_with_login()
    db.session.commit()

    r = login(client, "owner@example.com", "ownerpass1")
    assert r.headers["Location"] == "/dashboard"
    client.get("/auth/logout")

    r = login(client, "maria@example.com", "mariapass1")
    assert r.headers["Location"] == "/my/"


def test_employee_can_view_own_dashboard_and_attendance(db, client):
    _employee_with_login()
    login(client, "maria@example.com", "mariapass1")
    assert client.get("/my/").status_code == 200
    assert client.get("/my/attendance").status_code == 200
    assert client.get("/my/payslips").status_code == 200


def test_staff_without_employee_link_gets_404_on_self_service(db, client):
    db.session.add(_staff())
    db.session.commit()
    login(client, "owner@example.com", "ownerpass1")
    assert client.get("/my/").status_code == 404


def test_employee_cannot_view_another_employees_payslip(db, client):
    from app.models.payroll import PayrollRun, Payslip

    emp1, _ = _employee_with_login(code="EMP-001", email="maria@example.com")
    emp2 = Employee(
        employee_code="EMP-002", first_name="Jose", last_name="Reyes",
        pay_type="monthly", monthly_rate=Decimal("25000"), date_hired=date(2025, 1, 1),
    )
    db.session.add(emp2)
    db.session.commit()

    run = PayrollRun(period_start=date(2026, 7, 1), period_end=date(2026, 7, 15), status="processed")
    db.session.add(run)
    db.session.commit()

    own_slip = Payslip(payroll_run_id=run.id, employee_id=emp1.id, gross_pay=1000, total_deductions=0, net_pay=1000)
    other_slip = Payslip(payroll_run_id=run.id, employee_id=emp2.id, gross_pay=2000, total_deductions=0, net_pay=2000)
    db.session.add_all([own_slip, other_slip])
    db.session.commit()

    login(client, "maria@example.com", "mariapass1")
    assert client.get(f"/my/payslips/{own_slip.id}").status_code == 200
    assert client.get(f"/my/payslips/{other_slip.id}").status_code == 403
