from datetime import date
from decimal import Decimal
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.services.payroll_service import calculate_gross_pay


def test_monthly_employee_gross_pay(db):
    emp = Employee(
        employee_code="EMP-001", first_name="Ana", last_name="Cruz",
        pay_type="monthly", monthly_rate=Decimal("25000"), date_hired=date(2024, 1, 1),
    )
    db.session.add(emp)
    db.session.commit()

    result = calculate_gross_pay(emp, date(2026, 7, 1), date(2026, 7, 15))
    assert result["gross_pay"] == Decimal("25000")
    assert result["overtime_pay"] == Decimal("0")


def test_hourly_employee_gross_pay_with_overtime(db):
    emp = Employee(
        employee_code="EMP-002", first_name="Ben", last_name="Reyes",
        pay_type="hourly", hourly_rate=Decimal("75"), date_hired=date(2024, 1, 1),
    )
    db.session.add(emp)
    db.session.commit()

    db.session.add(Attendance(
        employee_id=emp.id, date=date(2026, 7, 1),
        hours_worked=Decimal("8"), overtime_hours=Decimal("2"),
    ))
    db.session.add(Attendance(
        employee_id=emp.id, date=date(2026, 7, 2), hours_worked=Decimal("8"),
    ))
    db.session.commit()

    result = calculate_gross_pay(emp, date(2026, 7, 1), date(2026, 7, 15))
    assert result["base_pay"] == Decimal("75") * 16
    assert result["overtime_pay"] == Decimal("75") * 2 * Decimal("1.25")


def test_daily_employee_gross_pay(db):
    emp = Employee(
        employee_code="EMP-003", first_name="Cara", last_name="Santos",
        pay_type="daily", daily_rate=Decimal("600"), date_hired=date(2024, 1, 1),
    )
    db.session.add(emp)
    db.session.commit()

    for d in [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)]:
        db.session.add(Attendance(employee_id=emp.id, date=d, status="present"))
    db.session.commit()

    result = calculate_gross_pay(emp, date(2026, 7, 1), date(2026, 7, 15))
    assert result["base_pay"] == Decimal("600") * 3
