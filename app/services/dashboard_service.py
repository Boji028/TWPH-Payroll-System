"""Aggregation queries for the admin dashboard. Kept separate from the
route (same reasoning as payroll_service.py) so the numbers can be
tested without a request context."""
from datetime import date
from sqlalchemy import func
from app.extensions import db
from app.models.employee import Employee
from app.models.payroll import PayrollRun, Payslip
from app.models.leave import LeaveRequest
from app.models.attendance import Attendance


def get_dashboard_stats():
    today = date.today()

    active_employees = Employee.query.filter_by(status="active").all()
    active_employee_count = len(active_employees)

    dept_counts = (
        db.session.query(Employee.department, func.count(Employee.id))
        .filter(Employee.status == "active")
        .group_by(Employee.department)
        .all()
    )
    department_breakdown = [
        {"label": dept or "Unassigned", "count": count} for dept, count in dept_counts
    ]

    if active_employees:
        tenures = [(today - e.date_hired).days / 365.25 for e in active_employees]
        avg_tenure_years = round(sum(tenures) / len(tenures), 1)
    else:
        avg_tenure_years = 0

    on_leave_count = LeaveRequest.query.filter(
        LeaveRequest.status == "approved",
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today,
    ).count()

    recent_hires = (
        Employee.query.filter(Employee.status == "active")
        .order_by(Employee.date_hired.desc())
        .limit(5)
        .all()
    )

    recent_runs_chrono = (
        PayrollRun.query.order_by(PayrollRun.period_start.desc()).limit(6).all()
    )
    recent_runs_chrono.reverse()
    pay_trend = []
    for run in recent_runs_chrono:
        total = (
            db.session.query(func.coalesce(func.sum(Payslip.net_pay), 0))
            .filter(Payslip.payroll_run_id == run.id)
            .scalar()
        )
        pay_trend.append({"label": run.period_start.strftime("%b %d"), "total": float(total)})

    # Dashboard hero: the most recent payroll run's period + net total.
    # Reuses the last entry already computed above rather than re-querying.
    latest_run = recent_runs_chrono[-1] if recent_runs_chrono else None
    latest_run_total = pay_trend[-1]["total"] if pay_trend else 0

    # "X of Y in today" — active employees whose attendance today is
    # present or late (i.e. actually clocked in), out of all active
    # employees. Employees with no attendance row yet, on leave, or
    # marked absent are not counted as "in".
    present_today_count = (
        Attendance.query.join(Employee, Attendance.employee_id == Employee.id)
        .filter(
            Employee.status == "active",
            Attendance.date == today,
            Attendance.status.in_(("present", "late")),
        )
        .count()
    )

    return {
        "active_employee_count": active_employee_count,
        "department_breakdown": department_breakdown,
        "avg_tenure_years": avg_tenure_years,
        "on_leave_count": on_leave_count,
        "recent_hires": recent_hires,
        "pay_trend": pay_trend,
        "latest_run": latest_run,
        "latest_run_total": latest_run_total,
        "present_today_count": present_today_count,
    }