# app/services/attendance_service.py
"""Travel Worthy PH runs fixed semi-monthly cutoffs: the 26th-10th is
paid on the 15th, the 11th-25th is paid on the 30th. The Attendance page
shows one full cutoff at a time (a grid of employee x day) instead of a
single day, so HR can review the whole period before payday."""
from datetime import date, timedelta

from app.models.employee import Employee
from app.models.attendance import Attendance, STATUS_LABELS, STATUS_BADGE_CLASSES

# Kept distinct from STATUS_LABELS on purpose - Late/Leave would both
# abbreviate to "L" from the first letter, so this is spelled out
# explicitly rather than derived.
STATUS_ABBR = {
    "present": "P",
    "late": "L",
    "absent": "A",
    "leave": "LV",
    "holiday": "H",
}


def get_pay_period(for_date):
    """Returns (period_start, period_end, payday) for the cutoff that
    for_date falls in."""
    d, y, m = for_date.day, for_date.year, for_date.month
    if d <= 10:
        prev_m, prev_y = (12, y - 1) if m == 1 else (m - 1, y)
        return date(prev_y, prev_m, 26), date(y, m, 10), date(y, m, 15)
    elif d <= 25:
        return date(y, m, 11), date(y, m, 25), date(y, m, 30)
    else:
        next_m, next_y = (1, y + 1) if m == 12 else (m + 1, y)
        return date(y, m, 26), date(next_y, next_m, 10), date(next_y, next_m, 15)


def build_attendance_grid(period_start, period_end):
    """Returns (dates, rows). dates is the list of dates in the period.
    rows is a list of {"employee": Employee, "cells": [...]}, one entry
    per active employee, cells aligned 1:1 with dates - each cell is
    either None (no Attendance row that day) or a dict with status,
    abbr, and badge_class ready to render directly."""
    dates = []
    d = period_start
    while d <= period_end:
        dates.append(d)
        d += timedelta(days=1)

    employees = Employee.query.filter_by(status="active").order_by(Employee.last_name).all()
    records = Attendance.query.filter(
        Attendance.date >= period_start, Attendance.date <= period_end
    ).all()
    by_key = {(r.employee_id, r.date): r.status for r in records}

    rows = []
    for employee in employees:
        cells = []
        for d in dates:
            status = by_key.get((employee.id, d))
            if status:
                cells.append({
                    "status": status,
                    "abbr": STATUS_ABBR.get(status, status[:1].upper()),
                    "badge_class": STATUS_BADGE_CLASSES.get(status, "bg-secondary"),
                    "label": STATUS_LABELS.get(status, status),
                })
            else:
                cells.append(None)
        rows.append({"employee": employee, "cells": cells})
    return dates, rows
