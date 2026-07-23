from datetime import date, timedelta
from decimal import Decimal
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.services.workforce_service import get_workforce_roster


def _make_employee(code, department="Ops", position="Staff", status="active"):
    return Employee(
        employee_code=code, first_name=code, last_name="Test", department=department,
        position=position, pay_type="monthly", monthly_rate=Decimal("20000"),
        date_hired=date(2024, 1, 1), status=status,
    )


def test_empty_state(db):
    assert get_workforce_roster() == []


def test_not_logged_when_no_attendance_row_today(db):
    db.session.add(_make_employee("EMP-1"))
    db.session.commit()

    roster = get_workforce_roster()
    assert len(roster) == 1
    assert roster[0]["status"] == "not_logged"
    assert roster[0]["status_label"] == "Not Logged Yet"
    assert roster[0]["badge_class"] == "bg-secondary"


def test_reflects_todays_attendance_status(db):
    emp = _make_employee("EMP-1")
    db.session.add(emp)
    db.session.commit()

    db.session.add(Attendance(employee_id=emp.id, date=date.today(), status="present", hours_worked=8))
    db.session.commit()

    roster = get_workforce_roster()
    assert roster[0]["status"] == "present"
    assert roster[0]["badge_class"] == "bg-success"


def test_ignores_attendance_from_other_days(db):
    emp = _make_employee("EMP-1")
    db.session.add(emp)
    db.session.commit()

    yesterday = date.today() - timedelta(days=1)
    db.session.add(Attendance(employee_id=emp.id, date=yesterday, status="present", hours_worked=8))
    db.session.commit()

    roster = get_workforce_roster()
    assert roster[0]["status"] == "not_logged"


def test_inactive_employees_excluded(db):
    db.session.add(_make_employee("EMP-1", status="inactive"))
    db.session.commit()
    assert get_workforce_roster() == []


def test_limit_caps_roster_size(db):
    db.session.add_all([_make_employee(f"EMP-{i}") for i in range(5)])
    db.session.commit()

    assert len(get_workforce_roster()) == 5
    assert len(get_workforce_roster(limit=2)) == 2


def test_ordered_by_department_then_last_name(db):
    db.session.add_all([
        _make_employee("EMP-1", department="Sales"),
        _make_employee("EMP-2", department="Kitchen"),
    ])
    db.session.commit()

    roster = get_workforce_roster()
    assert [row["department"] for row in roster] == ["Kitchen", "Sales"]
