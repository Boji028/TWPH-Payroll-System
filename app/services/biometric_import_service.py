# app/services/biometric_import_service.py
"""Parses .xls attendance exports from the fingerprint scanner and
imports them into Attendance, deriving Present/Late/Absent by comparing
each punch against the employee's ScheduledShift for that date.

The export format (a specific vendor's fixed report template) lays
employees out 3-per-sheet, side by side, with punch times bucketed into
"Before Noon / After Noon / Overtime" In/Out columns. That bucketing is
inconsistent in practice (a single stray punch can land in any of those
columns depending on the vendor software's own logic) so this parser
deliberately ignores which bucket a punch landed in: for each employee
and day, it collects every punch in that row and takes the earliest as
time_in and the latest as time_out. See docs/add-biometric-import.md.

Locating employee blocks and columns is done by searching cell text
("Dept.", "Name", "User ID", "Time Card", "In"/"Out") rather than
hardcoding column numbers, so it isn't tied to exactly 3 employees per
sheet or a fixed column count per block.
"""
import re
from datetime import timedelta, datetime as dt, time as time_cls

import xlrd
from xlrd.xldate import xldate_as_datetime

from app.extensions import db
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.schedule import ScheduledShift

SUMMARY_SHEET_NAMES = {"Shift Setting Table", "Attendance Statistic Table"}
PERIOD_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})")
GRACE_MINUTES = 15


class BiometricImportError(Exception):
    pass


def _cellval(sh, r, c):
    if r < 0 or r >= sh.nrows or c < 0 or c >= sh.ncols:
        return None
    return sh.cell(r, c).value


def _find_period(sh):
    for r in range(sh.nrows):
        for c in range(sh.ncols):
            v = sh.cell(r, c).value
            if isinstance(v, str) and "~" in v:
                m = PERIOD_RE.search(v)
                if m:
                    start = dt.strptime(m.group(1), "%Y-%m-%d").date()
                    end = dt.strptime(m.group(2), "%Y-%m-%d").date()
                    return start, end
    return None, None


def _parse_punch_sheet(sh, book):
    """Returns a list of dicts: user_id, date, time_in, time_out, punch_count."""
    period_start, period_end = _find_period(sh)
    if not period_start:
        return []

    header_row = None
    block_start_cols = []
    for r in range(min(10, sh.nrows)):
        cols = [c for c in range(sh.ncols) if str(_cellval(sh, r, c)).strip() == "Dept."]
        if cols:
            header_row, block_start_cols = r, cols
            break
    if header_row is None:
        return []
    block_end_cols = block_start_cols[1:] + [sh.ncols]

    time_card_row = None
    for r in range(header_row, sh.nrows):
        if any(str(_cellval(sh, r, c)).strip() == "Time Card" for c in range(sh.ncols)):
            time_card_row = r
            break
    if time_card_row is None:
        return []

    inout_row = time_card_row + 2
    data_start_row = time_card_row + 3
    num_days = (period_end - period_start).days + 1

    results = []
    for start_col, end_col in zip(block_start_cols, block_end_cols):
        user_id = None
        for r in (header_row, header_row + 1):
            for c in range(start_col, end_col):
                if str(_cellval(sh, r, c)).strip() == "User ID":
                    raw = _cellval(sh, r, c + 1)
                    user_id = str(int(raw)) if isinstance(raw, float) else str(raw)
        if user_id is None:
            continue

        punch_cols = [
            c for c in range(start_col, end_col)
            if str(_cellval(sh, inout_row, c)).strip() in ("In", "Out")
        ]

        for day_offset in range(num_days):
            r = data_start_row + day_offset
            if r >= sh.nrows:
                break
            the_date = period_start + timedelta(days=day_offset)
            times = []
            for c in punch_cols:
                cell = sh.cell(r, c)
                if cell.ctype == 3:  # xlrd date/time cell
                    times.append(xldate_as_datetime(cell.value, book.datemode).time())
            results.append({
                "user_id": user_id,
                "date": the_date,
                "time_in": min(times) if times else None,
                "time_out": max(times) if times else None,
                "punch_count": len(times),
            })
    return results


def parse_biometric_export(file_bytes):
    """file_bytes: raw bytes of an uploaded .xls file."""
    try:
        book = xlrd.open_workbook(file_contents=file_bytes)
    except Exception as e:
        raise BiometricImportError(f"Couldn't read this as an .xls file: {e}")

    rows = []
    for sheet_name in book.sheet_names():
        if sheet_name in SUMMARY_SHEET_NAMES:
            continue
        rows.extend(_parse_punch_sheet(book.sheet_by_name(sheet_name), book))
    return rows


def _minutes_between(a, b):
    return (dt.combine(dt.today(), b) - dt.combine(dt.today(), a)).total_seconds() / 60


def _derive_status(time_in, shift):
    """shift is a ScheduledShift or None. Returns 'present', 'late', or 'absent'."""
    if shift is None:
        return "present" if time_in else None  # None = no basis to judge, caller skips the row
    if time_in is None:
        return "absent"
    grace_end_minutes = shift.start_time.hour * 60 + shift.start_time.minute + GRACE_MINUTES
    arrival_minutes = time_in.hour * 60 + time_in.minute
    return "present" if arrival_minutes <= grace_end_minutes else "late"


def import_attendance(file_bytes):
    """Parses the file and upserts Attendance rows. Returns a summary dict
    with counts and lists for the results page - does not raise on
    per-row problems (unmatched IDs, single-punch days), only on a file
    that can't be parsed at all."""
    parsed_rows = parse_biometric_export(file_bytes)

    employees_by_biometric_id = {
        e.biometric_id: e for e in Employee.query.filter(Employee.biometric_id.isnot(None)).all()
    }

    created = 0
    updated = 0
    skipped_no_shift_no_punch = 0
    needs_review = []  # single-punch days - time_in == time_out, hours can't be trusted
    unmatched_ids = set()

    for row in parsed_rows:
        employee = employees_by_biometric_id.get(row["user_id"])
        if employee is None:
            if row["punch_count"] > 0:
                unmatched_ids.add(row["user_id"])
            continue

        shift = ScheduledShift.query.filter_by(employee_id=employee.id, date=row["date"]).first()
        status = _derive_status(row["time_in"], shift)
        if status is None:
            skipped_no_shift_no_punch += 1
            continue

        hours_worked = 0
        if row["time_in"] and row["time_out"] and row["time_in"] != row["time_out"]:
            hours_worked = round(_minutes_between(row["time_in"], row["time_out"]) / 60, 2)
        if row["punch_count"] == 1:
            needs_review.append({"employee": employee.full_name, "date": row["date"]})

        existing = Attendance.query.filter_by(employee_id=employee.id, date=row["date"]).first()
        if existing:
            existing.status = status
            existing.hours_worked = hours_worked
            existing.notes = "Imported from biometric scanner"
            updated += 1
        else:
            db.session.add(Attendance(
                employee_id=employee.id, date=row["date"], status=status,
                hours_worked=hours_worked, notes="Imported from biometric scanner",
            ))
            created += 1

    db.session.commit()

    unmatched_names = sorted({
        next((r["user_id"] for r in parsed_rows if r["user_id"] == uid), uid)
        for uid in unmatched_ids
    })
    return {
        "created": created,
        "updated": updated,
        "skipped_no_shift_no_punch": skipped_no_shift_no_punch,
        "needs_review": needs_review,
        "unmatched_scanner_ids": unmatched_names,
    }
