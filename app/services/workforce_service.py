# app/services/workforce_service.py
"""Aggregation for the live Workforce roster - today's attendance status
per active employee. Separate from attendance_routes.py (which handles
logging attendance) - this only reads and derives a display status.

'Real-time' here means: reflects whatever has been logged in Attendance
so far today, picked up by the polling JS on the Workforce page and
dashboard widget. There is no clock-in/out event stream - time_in and
time_out on Attendance are unused by log_attendance today, so status is
derived purely from whether a row exists yet and its status field."""
from datetime import date as date_cls

from app.models.employee import Employee
from app.models.attendance import Attendance

STATUS_LABELS = {
    "present": "Present",
    "absent": "Absent",
    "leave": "On Leave",
    "holiday": "Holiday",
    "not_logged": "Not Logged Yet",
}

STATUS_BADGE_CLASSES = {
    "present": "bg-success",
    "absent": "bg-danger",
    "leave": "bg-warning text-dark",
    "holiday": "bg-info text-dark",
    "not_logged": "bg-secondary",
}


def get_workforce_roster(target_date=None, limit=None):
    """Active employees with target_date's (default: today) attendance
    status. Returns a list of plain dicts - JSON-serializable as-is, so
    the same function backs both the JSON polling endpoint and the
    server-rendered initial page load."""
    target_date = target_date or date_cls.today()

    employees = (
        Employee.query.filter_by(status="active")
        .order_by(Employee.department, Employee.last_name)
        .all()
    )
    if limit:
        employees = employees[:limit]

    employee_ids = [e.id for e in employees]
    records = (
        Attendance.query.filter(
            Attendance.employee_id.in_(employee_ids), Attendance.date == target_date
        ).all()
        if employee_ids
        else []
    )
    record_by_employee = {r.employee_id: r for r in records}

    roster = []
    for employee in employees:
        record = record_by_employee.get(employee.id)
        status = record.status if record else "not_logged"
        roster.append(
            {
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "department": employee.department or "Unassigned",
                "position": employee.position or "-",
                "status": status,
                "status_label": STATUS_LABELS.get(status, status.title()),
                "badge_class": STATUS_BADGE_CLASSES.get(status, "bg-secondary"),
            }
        )
    return roster
