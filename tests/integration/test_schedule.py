from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db as _db
from app.models.user import User
from app.models.employee import Employee
from app.models.schedule import ScheduledShift


def _staff():
    user = User(full_name="Owner Admin", email="owner@example.com", role="owner")
    user.set_password("ownerpass1")
    return user


def _employee_with_login(email="maria@example.com"):
    emp = Employee(
        employee_code="EMP-001", first_name="Maria", last_name="Santos",
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


def test_staff_can_schedule_a_shift(db, client):
    emp, _ = _employee_with_login()
    db.session.add(_staff())
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    r = client.post("/schedule/log", data={
        "date": "2026-08-10",
        f"shift_{emp.id}": "opening",
    }, follow_redirects=True)
    assert r.status_code == 200
    shift = ScheduledShift.query.filter_by(employee_id=emp.id).first()
    assert shift is not None
    assert shift.shift_type.value == "opening"
    assert shift.date == date(2026, 8, 10)


def test_second_submit_updates_not_duplicates(db, client):
    emp, _ = _employee_with_login()
    db.session.add(_staff())
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    client.post("/schedule/log", data={"date": "2026-08-10", f"shift_{emp.id}": "opening"})
    client.post("/schedule/log", data={"date": "2026-08-10", f"shift_{emp.id}": "closing"})

    assert ScheduledShift.query.filter_by(employee_id=emp.id).count() == 1
    assert ScheduledShift.query.first().shift_type.value == "closing"


def test_blank_selection_clears_existing_shift(db, client):
    emp, _ = _employee_with_login()
    db.session.add(_staff())
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    client.post("/schedule/log", data={"date": "2026-08-10", f"shift_{emp.id}": "opening"})
    assert ScheduledShift.query.count() == 1

    client.post("/schedule/log", data={"date": "2026-08-10", f"shift_{emp.id}": ""})
    assert ScheduledShift.query.count() == 0


def test_one_shift_per_employee_per_day_enforced_at_db_level(db, client):
    emp, _ = _employee_with_login()
    db.session.add(ScheduledShift(
        employee_id=emp.id, date=date(2026, 8, 10), shift_type="opening", created_by_id=1,
    ))
    db.session.commit()
    # a second row for the same employee/date should violate the unique constraint
    import pytest
    from sqlalchemy.exc import IntegrityError
    db.session.add(ScheduledShift(
        employee_id=emp.id, date=date(2026, 8, 10), shift_type="closing", created_by_id=1,
    ))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_employee_sees_own_upcoming_shifts_only(db, client):
    emp, _ = _employee_with_login()
    staff = _staff()
    db.session.add(staff)
    db.session.commit()

    today = date.today()
    db.session.add_all([
        ScheduledShift(employee_id=emp.id, date=today + timedelta(days=2), shift_type="opening", created_by_id=staff.id),
        ScheduledShift(employee_id=emp.id, date=today - timedelta(days=2), shift_type="closing", created_by_id=staff.id),  # past
    ])
    db.session.commit()

    login(client, "maria@example.com", "mariapass1")
    body = client.get("/my/schedule").get_data(as_text=True)
    assert "Opening" in body
    assert "Closing" not in body  # past shift excluded


def test_employee_blocked_from_admin_schedule_routes(db, client):
    _employee_with_login()
    login(client, "maria@example.com", "mariapass1")
    assert client.get("/schedule/").status_code == 403
    assert client.get("/schedule/log").status_code == 403
