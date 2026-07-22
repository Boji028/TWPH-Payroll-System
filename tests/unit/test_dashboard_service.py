from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models.employee import Employee
from app.models.payroll import PayrollRun, Payslip
from app.models.leave import LeaveRequest
from app.services.dashboard_service import get_dashboard_stats


def test_empty_state(db):
    stats = get_dashboard_stats()
    assert stats["active_employee_count"] == 0
    assert stats["department_breakdown"] == []
    assert stats["avg_tenure_years"] == 0
    assert stats["on_leave_count"] == 0
    assert stats["pay_trend"] == []


def test_department_breakdown_groups_by_department(db):
    db.session.add_all([
        Employee(employee_code="EMP-1", first_name="A", last_name="A", department="Warehouse",
                 pay_type="monthly", monthly_rate=Decimal("20000"), date_hired=date(2024, 1, 1)),
        Employee(employee_code="EMP-2", first_name="B", last_name="B", department="Warehouse",
                 pay_type="monthly", monthly_rate=Decimal("20000"), date_hired=date(2024, 1, 1)),
        Employee(employee_code="EMP-3", first_name="C", last_name="C", department="Sales",
                 pay_type="monthly", monthly_rate=Decimal("20000"), date_hired=date(2024, 1, 1)),
    ])
    db.session.commit()

    stats = get_dashboard_stats()
    counts = {row["label"]: row["count"] for row in stats["department_breakdown"]}
    assert counts == {"Warehouse": 2, "Sales": 1}
    assert stats["active_employee_count"] == 3


def test_inactive_employees_excluded(db):
    db.session.add(Employee(
        employee_code="EMP-1", first_name="A", last_name="A", department="Sales",
        pay_type="monthly", monthly_rate=Decimal("20000"), date_hired=date(2024, 1, 1), status="inactive",
    ))
    db.session.commit()

    stats = get_dashboard_stats()
    assert stats["active_employee_count"] == 0
    assert stats["department_breakdown"] == []


def test_on_leave_count_only_counts_approved_and_current(db):
    emp = Employee(employee_code="EMP-1", first_name="A", last_name="A",
                    pay_type="monthly", monthly_rate=Decimal("20000"), date_hired=date(2024, 1, 1))
    db.session.add(emp)
    db.session.commit()

    today = date.today()
    db.session.add_all([
        LeaveRequest(employee_id=emp.id, leave_type="vacation",
                     start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
                     status="approved"),
        LeaveRequest(employee_id=emp.id, leave_type="sick",
                     start_date=today, end_date=today, status="pending"),  # not approved yet
        LeaveRequest(employee_id=emp.id, leave_type="vacation",
                     start_date=today - timedelta(days=30), end_date=today - timedelta(days=25),
                     status="approved"),  # approved but already over
    ])
    db.session.commit()

    stats = get_dashboard_stats()
    assert stats["on_leave_count"] == 1


def test_pay_trend_sums_net_pay_per_run_chronologically(db):
    emp = Employee(employee_code="EMP-1", first_name="A", last_name="A",
                    pay_type="monthly", monthly_rate=Decimal("20000"), date_hired=date(2024, 1, 1))
    db.session.add(emp)
    db.session.commit()

    run1 = PayrollRun(period_start=date(2026, 6, 1), period_end=date(2026, 6, 15), status="processed")
    run2 = PayrollRun(period_start=date(2026, 7, 1), period_end=date(2026, 7, 15), status="processed")
    db.session.add_all([run1, run2])
    db.session.commit()

    db.session.add_all([
        Payslip(payroll_run_id=run1.id, employee_id=emp.id, gross_pay=1000, total_deductions=0, net_pay=Decimal("1000")),
        Payslip(payroll_run_id=run2.id, employee_id=emp.id, gross_pay=1200, total_deductions=0, net_pay=Decimal("1200")),
    ])
    db.session.commit()

    stats = get_dashboard_stats()
    assert stats["pay_trend"] == [
        {"label": "Jun 01", "total": 1000.0},
        {"label": "Jul 01", "total": 1200.0},
    ]
