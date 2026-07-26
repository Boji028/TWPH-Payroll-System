from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db as _db
from app.models.user import User
from app.models.employee import Employee
from app.models.schedule import ScheduledShift, ShiftType, WeeklyShiftAssignment
from app.services.schedule_rotation_service import generate_week

WEEK_1 = date(2026, 7, 27)  # a Monday
WEEK_2 = WEEK_1 + timedelta(days=7)


def _staff():
    user = User(full_name="Owner Admin", email="owner@example.com", role="owner")
    user.set_password("ownerpass1")
    return user


def _employee(code, first_name, rest_day=6):
    return Employee(
        employee_code=code, first_name=first_name, last_name="Test",
        pay_type="hourly", hourly_rate=Decimal("95"), date_hired=date(2025, 1, 1),
        rest_day=rest_day,
    )


def _employee_with_login(email="maria@example.com", rest_day=6):
    emp = _employee("EMP-001", "Maria", rest_day=rest_day)
    _db.session.add(emp)
    _db.session.commit()
    user = User(full_name=emp.full_name, email=email, role="employee", employee_id=emp.id)
    user.set_password("mariapass1")
    _db.session.add(user)
    _db.session.commit()
    return emp, user


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password})


def test_new_hire_is_balanced_to_the_less_populated_shift(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    # Continuing employee: was OPENING last week, so this week they flip to
    # CLOSING, leaving OPENING under-populated for the new hire below.
    continuing = _employee("EMP-001", "Continuing")
    db.session.add(continuing)
    db.session.commit()
    db.session.add(WeeklyShiftAssignment(
        employee_id=continuing.id, week_start_date=WEEK_1 - timedelta(days=7),
        shift_type=ShiftType.OPENING, rest_day=6, created_by_id=staff.id,
    ))
    new_hire = _employee("EMP-002", "NewHire", rest_day=3)
    db.session.add(new_hire)
    db.session.commit()

    generate_week(WEEK_1, created_by_id=staff.id)

    assert WeeklyShiftAssignment.query.filter_by(
        employee_id=continuing.id, week_start_date=WEEK_1
    ).first().shift_type == ShiftType.CLOSING

    assignment = WeeklyShiftAssignment.query.filter_by(employee_id=new_hire.id, week_start_date=WEEK_1).first()
    assert assignment.shift_type == ShiftType.OPENING  # fewer people on Opening (0 vs 1) after the flip above
    assert assignment.rest_day == 3  # employee's fixed default, since no override exists


def test_multiple_new_hires_split_evenly(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    employees = [_employee(f"EMP-00{i}", f"Emp{i}") for i in range(1, 5)]
    db.session.add_all(employees)
    db.session.commit()

    generate_week(WEEK_1, created_by_id=staff.id)

    assignments = WeeklyShiftAssignment.query.filter_by(week_start_date=WEEK_1).all()
    openings = sum(1 for a in assignments if a.shift_type == ShiftType.OPENING)
    closings = sum(1 for a in assignments if a.shift_type == ShiftType.CLOSING)
    assert openings == 2 and closings == 2


def test_shift_flips_week_over_week(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp = _employee("EMP-001", "Maria")
    db.session.add(emp)
    db.session.commit()

    generate_week(WEEK_1, created_by_id=staff.id)
    first = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first().shift_type

    generate_week(WEEK_2, created_by_id=staff.id)
    second = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_2).first().shift_type

    assert first != second


def test_rerun_for_same_week_is_idempotent(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp = _employee("EMP-001", "Maria")
    db.session.add(emp)
    db.session.commit()

    generate_week(WEEK_1, created_by_id=staff.id)
    first = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first().shift_type
    generate_week(WEEK_1, created_by_id=staff.id)
    second = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first().shift_type

    assert first == second
    assert WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).count() == 1


def test_override_is_never_touched_by_a_later_rotation_run(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp = _employee("EMP-001", "Maria")
    db.session.add(emp)
    db.session.commit()

    generate_week(WEEK_1, created_by_id=staff.id)
    override = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first()
    override.shift_type = ShiftType.OPENING
    override.is_override = True
    db.session.commit()

    generate_week(WEEK_1, created_by_id=staff.id)

    unchanged = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first()
    assert unchanged.shift_type == ShiftType.OPENING
    assert unchanged.is_override is True


def test_rest_day_gets_no_scheduled_shift_row_and_a_stale_one_is_removed(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp = _employee("EMP-001", "Maria", rest_day=2)  # Wednesday
    db.session.add(emp)
    db.session.commit()

    rest_date = WEEK_1 + timedelta(days=2)
    # stale row from the old daily tool, as if the employee used to work Wednesdays
    db.session.add(ScheduledShift(
        employee_id=emp.id, date=rest_date, shift_type=ShiftType.OPENING, created_by_id=staff.id,
    ))
    db.session.commit()

    generate_week(WEEK_1, created_by_id=staff.id)

    assert ScheduledShift.query.filter_by(employee_id=emp.id, date=rest_date).count() == 0
    working_days = ScheduledShift.query.filter_by(employee_id=emp.id).filter(
        ScheduledShift.date >= WEEK_1, ScheduledShift.date < WEEK_1 + timedelta(days=7)
    ).count()
    assert working_days == 6


def test_weekly_view_shows_generated_assignment(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp = _employee("EMP-001", "Maria")
    db.session.add(emp)
    db.session.commit()
    generate_week(WEEK_1, created_by_id=staff.id)

    login(client, "owner@example.com", "ownerpass1")
    body = client.get(f"/schedule/weekly?week={WEEK_1.isoformat()}").get_data(as_text=True)
    assert "Maria" in body


def test_admin_edit_sets_override_and_survives_next_rotation(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp = _employee("EMP-001", "Maria", rest_day=6)
    db.session.add(emp)
    db.session.commit()
    generate_week(WEEK_1, created_by_id=staff.id)

    login(client, "owner@example.com", "ownerpass1")
    r = client.post(
        f"/schedule/weekly/{emp.id}/edit?week={WEEK_1.isoformat()}",
        data={"shift_type": "opening", "rest_day": "2"},
        follow_redirects=True,
    )
    assert r.status_code == 200

    assignment = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first()
    assert assignment.is_override is True
    assert assignment.shift_type == ShiftType.OPENING
    assert assignment.rest_day == 2

    generate_week(WEEK_1, created_by_id=staff.id)
    unchanged = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first()
    assert unchanged.shift_type == ShiftType.OPENING and unchanged.rest_day == 2


def test_export_returns_xlsx(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp = _employee("EMP-001", "Maria")
    db.session.add(emp)
    db.session.commit()
    generate_week(WEEK_1, created_by_id=staff.id)

    login(client, "owner@example.com", "ownerpass1")
    r = client.get(f"/schedule/weekly/export?week={WEEK_1.isoformat()}")
    assert r.status_code == 200
    assert r.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_employee_blocked_from_admin_weekly_routes(db, client):
    emp, _ = _employee_with_login()
    login(client, "maria@example.com", "mariapass1")
    assert client.get("/schedule/weekly").status_code == 403
    assert client.get(f"/schedule/weekly/{emp.id}/edit").status_code == 403
    assert client.get("/schedule/weekly/export").status_code == 403


def test_self_service_dashboard_shows_current_week_banner(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    emp, _ = _employee_with_login()
    generate_week(WEEK_1, created_by_id=staff.id)
    # Force the assignment onto "this week" so the dashboard (which looks up
    # today's week) actually finds it, regardless of what today's date is.
    from app.models.schedule import week_start_for
    assignment = WeeklyShiftAssignment.query.filter_by(employee_id=emp.id, week_start_date=WEEK_1).first()
    assignment.week_start_date = week_start_for(date.today())
    db.session.commit()

    login(client, "maria@example.com", "mariapass1")
    body = client.get("/my/").get_data(as_text=True)
    assert "This week's schedule" in body


def test_daily_tool_hides_dropdown_and_warns_for_rotation_managed_week(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    managed = _employee("EMP-001", "Managed")
    free = _employee("EMP-002", "Free")
    db.session.add_all([managed, free])
    db.session.commit()
    # Only "managed" has a WeeklyShiftAssignment this week - "free" has none,
    # e.g. because their week hasn't been generated yet.
    db.session.add(WeeklyShiftAssignment(
        employee_id=managed.id, week_start_date=WEEK_1, shift_type=ShiftType.OPENING,
        rest_day=6, created_by_id=staff.id,
    ))
    db.session.commit()

    login(client, "owner@example.com", "ownerpass1")
    monday = WEEK_1.isoformat()
    body = client.get(f"/schedule/log?date={monday}").get_data(as_text=True)

    assert "managed by" in body.lower()
    assert f"shift_{managed.id}" not in body  # no editable dropdown for the rotation-managed employee
    assert f"shift_{free.id}" in body  # employees with no assignment this week are still editable


def test_daily_tool_post_never_touches_rotation_managed_employees(db, client):
    staff = _staff()
    db.session.add(staff)
    db.session.commit()
    managed = _employee("EMP-001", "Managed", rest_day=2)
    db.session.add(managed)
    db.session.commit()
    generate_week(WEEK_1, created_by_id=staff.id)

    monday = WEEK_1.isoformat()
    original = ScheduledShift.query.filter_by(employee_id=managed.id, date=WEEK_1).first()
    assert original is not None

    login(client, "owner@example.com", "ownerpass1")
    # Even a crafted POST trying to blank out (delete) the managed employee's
    # shift for this date must be ignored server-side, not just hidden in the UI.
    client.post("/schedule/log", data={"date": monday, f"shift_{managed.id}": ""})

    unchanged = ScheduledShift.query.filter_by(employee_id=managed.id, date=WEEK_1).first()
    assert unchanged is not None
    assert unchanged.shift_type == original.shift_type
