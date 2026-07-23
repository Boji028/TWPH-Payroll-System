from datetime import date, timedelta
from decimal import Decimal
import io
from app.extensions import db as _db
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.schedule import ScheduledShift

FIXTURE = "tests/fixtures/sample_biometric_export.xls"


def _staff():
    user = User(full_name="Owner Admin", email="owner@example.com", role="owner")
    user.set_password("ownerpass1")
    return user


def _employee(code, biometric_id, first_name):
    return Employee(
        employee_code=code, biometric_id=biometric_id, first_name=first_name, last_name="Test",
        pay_type="monthly", monthly_rate=Decimal("15000"), date_hired=date(2024, 1, 1),
    )


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password})


def _upload(client):
    with open(FIXTURE, "rb") as f:
        data = {"file": (io.BytesIO(f.read()), "sample.xls")}
        return client.post("/attendance/import", data=data, content_type="multipart/form-data",
                            follow_redirects=True)


def test_full_import_derives_present_late_absent_from_real_export(db, client):
    staff = _staff()
    # User 1 ("tinay" in the file): punched 11:26 in / 20:01 out on 2026-05-27,
    # zero punches on 2026-05-26.
    emp1 = _employee("EMP-001", "1", "Tinay")
    # User 3 ("jia"): punched exactly 08:15:00 in on 2026-05-28 (grace boundary),
    # and 08:17:59 in on 2026-05-29 (past grace).
    emp3 = _employee("EMP-003", "3", "Jia")
    db.session.add_all([staff, emp1, emp3])
    db.session.commit()

    db.session.add_all([
        ScheduledShift(employee_id=emp1.id, date=date(2026, 5, 27), shift_type="closing", created_by_id=staff.id),
        ScheduledShift(employee_id=emp1.id, date=date(2026, 5, 26), shift_type="closing", created_by_id=staff.id),
        ScheduledShift(employee_id=emp3.id, date=date(2026, 5, 28), shift_type="opening", created_by_id=staff.id),
        ScheduledShift(employee_id=emp3.id, date=date(2026, 5, 29), shift_type="opening", created_by_id=staff.id),
    ])
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    r = _upload(client)
    assert r.status_code == 200

    a = Attendance.query.filter_by(employee_id=emp1.id, date=date(2026, 5, 27)).first()
    assert a.status == "present"  # 11:26 punch, closing shift starts 11:30 (before start entirely)

    absent = Attendance.query.filter_by(employee_id=emp1.id, date=date(2026, 5, 26)).first()
    assert absent.status == "absent"  # scheduled, zero punches that day

    on_time = Attendance.query.filter_by(employee_id=emp3.id, date=date(2026, 5, 28)).first()
    assert on_time.status == "present"  # 08:15:00 exactly at the 15-min grace boundary

    late = Attendance.query.filter_by(employee_id=emp3.id, date=date(2026, 5, 29)).first()
    assert late.status == "late"  # 08:17:59, past the grace boundary

    body = r.get_data(as_text=True)
    # Users 2, 4, 6, 7 have real punches in the file but no matching employee here
    for uid in ("2", "4", "6", "7"):
        assert uid in body
    # Users 5, 8, 9 have zero punches in the file, so they're never flagged as unmatched
    import re
    unmatched_section = body.split("Unmatched scanner User IDs")[1].split("</div>")[0]
    for uid in ("5", "8", "9"):
        assert uid not in unmatched_section


def test_running_import_twice_updates_not_duplicates(db, client):
    staff = _staff()
    emp = _employee("EMP-001", "1", "Tinay")
    db.session.add_all([staff, emp])
    db.session.commit()
    db.session.add(ScheduledShift(employee_id=emp.id, date=date(2026, 5, 27), shift_type="closing", created_by_id=staff.id))
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    _upload(client)
    _upload(client)

    assert Attendance.query.filter_by(employee_id=emp.id, date=date(2026, 5, 27)).count() == 1


def test_import_route_blocked_for_employee_role(db, client):
    emp = _employee("EMP-001", "1", "Tinay")
    db.session.add(emp)
    db.session.commit()
    user = User(full_name="Tinay", email="tinay@example.com", role="employee", employee_id=emp.id)
    user.set_password("tinaypass1")
    db.session.add(user)
    db.session.commit()

    login(client, "tinay@example.com", "tinaypass1")
    assert client.get("/attendance/import").status_code == 403
