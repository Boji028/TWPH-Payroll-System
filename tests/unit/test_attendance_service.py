from datetime import date
from decimal import Decimal
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.services.attendance_service import get_pay_period, build_attendance_grid, STATUS_ABBR


def _employee(code, last_name):
    return Employee(
        employee_code=code, first_name="Test", last_name=last_name,
        pay_type="monthly", monthly_rate=Decimal("15000"), date_hired=date(2024, 1, 1),
    )


def test_period_for_early_month_day():
    start, end, payday = get_pay_period(date(2026, 7, 5))
    assert (start, end, payday) == (date(2026, 6, 26), date(2026, 7, 10), date(2026, 7, 15))


def test_period_for_mid_month_day():
    start, end, payday = get_pay_period(date(2026, 7, 18))
    assert (start, end, payday) == (date(2026, 7, 11), date(2026, 7, 25), date(2026, 7, 30))


def test_period_for_late_month_day():
    start, end, payday = get_pay_period(date(2026, 7, 28))
    assert (start, end, payday) == (date(2026, 7, 26), date(2026, 8, 10), date(2026, 8, 15))


def test_period_boundary_day_10_belongs_to_early_period():
    start, end, payday = get_pay_period(date(2026, 7, 10))
    assert (start, end) == (date(2026, 6, 26), date(2026, 7, 10))


def test_period_boundary_day_26_belongs_to_late_period():
    start, end, payday = get_pay_period(date(2026, 7, 26))
    assert (start, end) == (date(2026, 7, 26), date(2026, 8, 10))


def test_period_rollover_into_january():
    # Jan 5 2027 -> period started Dec 26 2026
    start, end, payday = get_pay_period(date(2027, 1, 5))
    assert (start, end, payday) == (date(2026, 12, 26), date(2027, 1, 10), date(2027, 1, 15))


def test_period_rollover_out_of_december():
    # Dec 27 2026 -> period ends Jan 10 2027
    start, end, payday = get_pay_period(date(2026, 12, 27))
    assert (start, end, payday) == (date(2026, 12, 26), date(2027, 1, 10), date(2027, 1, 15))


def test_grid_has_one_column_per_day_in_period(db):
    dates, rows = build_attendance_grid(date(2026, 6, 26), date(2026, 7, 10))
    assert len(dates) == 15  # June has 30 days: 26-30 (5) + July 1-10 (10)
    assert dates[0] == date(2026, 6, 26)
    assert dates[-1] == date(2026, 7, 10)


def test_grid_only_includes_active_employees(db):
    db.session.add_all([
        _employee("EMP-1", "Active"),
        Employee(employee_code="EMP-2", first_name="Test", last_name="Inactive",
                  pay_type="monthly", monthly_rate=Decimal("15000"), date_hired=date(2024, 1, 1),
                  status="inactive"),
    ])
    db.session.commit()

    dates, rows = build_attendance_grid(date(2026, 7, 1), date(2026, 7, 3))
    assert len(rows) == 1
    assert rows[0]["employee"].last_name == "Active"


def test_grid_cells_reflect_attendance_and_blank_when_missing(db):
    emp = _employee("EMP-1", "Cruz")
    db.session.add(emp)
    db.session.commit()
    db.session.add(Attendance(employee_id=emp.id, date=date(2026, 7, 2), status="late"))
    db.session.commit()

    dates, rows = build_attendance_grid(date(2026, 7, 1), date(2026, 7, 3))
    cells = rows[0]["cells"]
    assert cells[0] is None  # July 1, no record
    assert cells[1]["status"] == "late"
    assert cells[1]["abbr"] == STATUS_ABBR["late"]
    assert cells[1]["badge_class"] == "bg-warning text-dark"
    assert cells[2] is None  # July 3, no record


def test_late_and_leave_have_distinct_abbreviations():
    # both start with "L" - must not collide
    assert STATUS_ABBR["late"] != STATUS_ABBR["leave"]
