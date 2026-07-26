# app/services/schedule_rotation_service.py
"""Generates one Monday-start week's WeeklyShiftAssignment rows for every
active employee, then expands each into daily ScheduledShift rows.

Rest days are represented purely as the *absence* of a ScheduledShift row
for that date - never create one for an employee's rest_day. That is what
keeps rest days out of the absence scoring in
biometric_import_service._derive_status, with no changes needed there.
"""
from datetime import timedelta

from app.extensions import db
from app.models.employee import Employee
from app.models.schedule import ScheduledShift, ShiftType, WeeklyShiftAssignment


def sync_scheduled_shifts_for_week(employee_id, week_start_date, shift_type, rest_day, created_by_id):
    for offset in range(7):
        the_date = week_start_date + timedelta(days=offset)
        existing = ScheduledShift.query.filter_by(employee_id=employee_id, date=the_date).first()
        if offset == rest_day:
            if existing:
                db.session.delete(existing)
        elif existing:
            existing.shift_type = shift_type
        else:
            db.session.add(ScheduledShift(
                employee_id=employee_id, date=the_date, shift_type=shift_type,
                created_by_id=created_by_id,
            ))


def generate_week(week_start_date, created_by_id):
    """Idempotent - safe to re-run for the same week before it starts.
    Returns a summary dict: assigned, overrides_skipped, new_hires_balanced.
    """
    prior_week_start = week_start_date - timedelta(days=7)
    employees = Employee.query.filter_by(status="active").order_by(Employee.id).all()

    prior_assignments = {
        a.employee_id: a
        for a in WeeklyShiftAssignment.query.filter_by(week_start_date=prior_week_start).all()
    }
    this_week_assignments = {
        a.employee_id: a
        for a in WeeklyShiftAssignment.query.filter_by(week_start_date=week_start_date).all()
    }

    counts = {ShiftType.OPENING: 0, ShiftType.CLOSING: 0}
    new_hires = []
    assigned = 0
    overrides_skipped = 0

    # Phase 1: continuing employees (flip from prior week) and overrides
    # (left untouched, but still counted so balance stays accurate).
    for employee in employees:
        existing = this_week_assignments.get(employee.id)
        if existing and existing.is_override:
            overrides_skipped += 1
            counts[existing.shift_type] += 1
            continue

        prior = prior_assignments.get(employee.id)
        if prior is None:
            new_hires.append(employee)
            continue

        new_shift = ShiftType.CLOSING if prior.shift_type == ShiftType.OPENING else ShiftType.OPENING
        rest_day = existing.rest_day if existing else employee.rest_day
        counts[new_shift] += 1

        if existing:
            existing.shift_type = new_shift
            existing.rest_day = rest_day
        else:
            existing = WeeklyShiftAssignment(
                employee_id=employee.id, week_start_date=week_start_date,
                shift_type=new_shift, rest_day=rest_day, created_by_id=created_by_id,
            )
            db.session.add(existing)
        sync_scheduled_shifts_for_week(employee.id, week_start_date, new_shift, rest_day, created_by_id)
        assigned += 1

    # Phase 2: new hires - balance to whichever shift has fewer people so
    # far, updating the running count immediately so several new hires in
    # the same run split evenly rather than all landing on one shift.
    for employee in new_hires:
        new_shift = ShiftType.OPENING if counts[ShiftType.OPENING] <= counts[ShiftType.CLOSING] else ShiftType.CLOSING
        counts[new_shift] += 1
        rest_day = employee.rest_day

        existing = this_week_assignments.get(employee.id)
        if existing:
            existing.shift_type = new_shift
            existing.rest_day = rest_day
        else:
            existing = WeeklyShiftAssignment(
                employee_id=employee.id, week_start_date=week_start_date,
                shift_type=new_shift, rest_day=rest_day, created_by_id=created_by_id,
            )
            db.session.add(existing)
        sync_scheduled_shifts_for_week(employee.id, week_start_date, new_shift, rest_day, created_by_id)
        assigned += 1

    return {
        "assigned": assigned,
        "overrides_skipped": overrides_skipped,
        "new_hires_balanced": len(new_hires),
    }
