from datetime import date
from decimal import Decimal
from app.extensions import db as _db
from app.models.user import User
from app.models.employee import Employee
from app.models.leave import LeaveRequest


def _staff():
    user = User(full_name="Owner Admin", email="owner@example.com", role="owner")
    user.set_password("ownerpass1")
    return user


def _employee_with_login():
    emp = Employee(
        employee_code="EMP-001", first_name="Maria", last_name="Santos",
        pay_type="hourly", hourly_rate=Decimal("95"), date_hired=date(2025, 1, 1),
    )
    _db.session.add(emp)
    _db.session.commit()
    user = User(full_name=emp.full_name, email="maria@example.com", role="employee", employee_id=emp.id)
    user.set_password("mariapass1")
    _db.session.add(user)
    _db.session.commit()
    return emp, user


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password})


def test_employee_can_submit_leave_request(db, client):
    _employee_with_login()
    login(client, "maria@example.com", "mariapass1")
    r = client.post("/my/leave", data={
        "leave_type": "vacation", "start_date": "2026-08-01",
        "end_date": "2026-08-03", "reason": "Family trip",
    })
    assert r.status_code == 302
    assert LeaveRequest.query.count() == 1
    assert LeaveRequest.query.first().status == "pending"


def test_invalid_date_range_rejected(db, client):
    _employee_with_login()
    login(client, "maria@example.com", "mariapass1")
    r = client.post("/my/leave", data={
        "leave_type": "sick", "start_date": "2026-08-05",
        "end_date": "2026-08-01", "reason": "x",
    })
    assert r.status_code == 200  # re-renders the form, doesn't redirect
    assert LeaveRequest.query.count() == 0


def test_admin_sees_pending_and_can_approve(db, client):
    emp, _ = _employee_with_login()
    db.session.add(_staff())
    db.session.commit()

    leave = LeaveRequest(
        employee_id=emp.id, leave_type="vacation",
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 3),
    )
    db.session.add(leave)
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    body = client.get("/leave/").get_data(as_text=True)
    assert "Maria Santos" in body

    r = client.post(f"/leave/{leave.id}/approve", follow_redirects=True)
    assert db.session.get(LeaveRequest, leave.id).status == "approved"
    assert "Approved" in r.get_data(as_text=True)


def test_cannot_reapprove_already_reviewed_request(db, client):
    emp, _ = _employee_with_login()
    db.session.add(_staff())
    db.session.commit()

    leave = LeaveRequest(
        employee_id=emp.id, leave_type="sick",
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 1), status="approved",
    )
    db.session.add(leave)
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    r = client.post(f"/leave/{leave.id}/reject", follow_redirects=True)
    assert "already been reviewed" in r.get_data(as_text=True)
    assert db.session.get(LeaveRequest, leave.id).status == "approved"  # unchanged


def test_employee_blocked_from_admin_leave_routes(db, client):
    _employee_with_login()
    login(client, "maria@example.com", "mariapass1")
    assert client.get("/leave/").status_code == 403
