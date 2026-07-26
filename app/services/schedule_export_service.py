# app/services/schedule_export_service.py
"""Renders a week's WeeklyShiftAssignment rows to an .xlsx file for admin
download. openpyxl is pure-Python so a top-level import is fine here,
unlike weasyprint's inside-the-function guard in pdf_service.py."""
from io import BytesIO

from openpyxl import Workbook


def render_weekly_schedule_xlsx(assignments):
    wb = Workbook()
    ws = wb.active
    ws.title = "Weekly Schedule"
    ws.append(["Employee", "Department", "Shift", "Rest Day"])
    for a in assignments:
        ws.append([a.employee.full_name, a.employee.department or "", a.shift_label, a.rest_day_label])

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
