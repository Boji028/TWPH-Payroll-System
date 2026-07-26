# app/routes/schedule_routes.py
from datetime import datetime, date
from io import BytesIO
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import current_user
from app.decorators import staff_required
from app.extensions import db
from app.models.employee import Employee
from app.models.schedule import ScheduledShift, ShiftType, WeeklyShiftAssignment, week_start_for
from app.forms.schedule_forms import WeeklyAssignmentForm
from app.services.schedule_export_service import render_weekly_schedule_xlsx
from app.services.schedule_rotation_service import sync_scheduled_shifts_for_week

schedule_bp = Blueprint("schedule", __name__)


@schedule_bp.route("/")
@staff_required
def list_schedule():
    date_str = request.args.get("date")
    selected_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()
    )
    shifts = (
        ScheduledShift.query.filter_by(date=selected_date)
        .join(Employee)
        .order_by(Employee.last_name)
        .all()
    )
    return render_template("schedule/list.html", shifts=shifts, selected_date=selected_date)


def _rotation_controlled_employee_ids(week_start):
    """Employee IDs with a WeeklyShiftAssignment (auto-generated or admin
    override) for this week - their schedule for the whole week is owned
    by Weekly Schedule, so the old daily tool below must never touch it."""
    return {
        a.employee_id
        for a in WeeklyShiftAssignment.query.filter_by(week_start_date=week_start).all()
    }


@schedule_bp.route("/log", methods=["GET", "POST"])
@staff_required
def log_schedule():
    employees = Employee.query.filter_by(status="active").order_by(Employee.last_name).all()
    if request.method == "POST":
        date_val = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        rotation_employee_ids = _rotation_controlled_employee_ids(week_start_for(date_val))
        for employee in employees:
            if employee.id in rotation_employee_ids:
                # this employee's whole week is owned by Weekly Schedule -
                # skip entirely, regardless of what was submitted for them
                continue
            shift_value = request.form.get(f"shift_{employee.id}", "")
            existing = ScheduledShift.query.filter_by(employee_id=employee.id, date=date_val).first()
            if shift_value:
                if existing:
                    existing.shift_type = ShiftType(shift_value)
                else:
                    db.session.add(ScheduledShift(
                        employee_id=employee.id,
                        date=date_val,
                        shift_type=ShiftType(shift_value),
                        created_by_id=current_user.id,
                    ))
            elif existing:
                # blank selection clears a previously scheduled shift for this employee/date
                db.session.delete(existing)
        db.session.commit()
        if rotation_employee_ids:
            flash(
                f"Schedule saved. {len(rotation_employee_ids)} employee(s) were skipped "
                "because this week is managed by Weekly Schedule - edit them from there instead.",
                "warning",
            )
        else:
            flash("Schedule saved.", "success")
        return redirect(url_for("schedule.list_schedule", date=request.form["date"]))

    date_str = request.args.get("date")
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
    rotation_week_start = week_start_for(selected_date) if selected_date else None
    rotation_assignments = (
        {a.employee_id: a for a in WeeklyShiftAssignment.query.filter_by(week_start_date=rotation_week_start).all()}
        if selected_date else {}
    )
    return render_template(
        "schedule/log.html",
        employees=employees,
        selected_date=selected_date,
        rotation_week_start=rotation_week_start,
        rotation_assignments=rotation_assignments,
    )


def _week_from_request():
    week_str = request.args.get("week")
    return datetime.strptime(week_str, "%Y-%m-%d").date() if week_str else week_start_for(date.today())


@schedule_bp.route("/weekly")
@staff_required
def weekly_schedule():
    week_start = _week_from_request()
    employees = Employee.query.filter_by(status="active").order_by(Employee.last_name).all()
    assignments = {
        a.employee_id: a
        for a in WeeklyShiftAssignment.query.filter_by(week_start_date=week_start).all()
    }
    rows = [(employee, assignments.get(employee.id)) for employee in employees]
    return render_template("schedule/weekly.html", rows=rows, week_start=week_start)


@schedule_bp.route("/weekly/<int:employee_id>/edit", methods=["GET", "POST"])
@staff_required
def edit_weekly_assignment(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    week_start = _week_from_request()
    assignment = WeeklyShiftAssignment.query.filter_by(
        employee_id=employee_id, week_start_date=week_start
    ).first()

    form = WeeklyAssignmentForm(obj=assignment)
    if assignment is None and request.method == "GET":
        form.rest_day.data = employee.rest_day

    if form.validate_on_submit():
        shift_type = ShiftType(form.shift_type.data)
        rest_day = form.rest_day.data
        if assignment:
            assignment.shift_type = shift_type
            assignment.rest_day = rest_day
            assignment.is_override = True
        else:
            assignment = WeeklyShiftAssignment(
                employee_id=employee.id, week_start_date=week_start,
                shift_type=shift_type, rest_day=rest_day, is_override=True,
                created_by_id=current_user.id,
            )
            db.session.add(assignment)
        sync_scheduled_shifts_for_week(employee.id, week_start, shift_type, rest_day, current_user.id)
        db.session.commit()
        flash(f"Schedule updated for {employee.full_name}, week of {week_start}.", "success")
        return redirect(url_for("schedule.weekly_schedule", week=week_start.isoformat()))

    return render_template(
        "schedule/weekly_edit.html", form=form, employee=employee, week_start=week_start
    )


@schedule_bp.route("/weekly/export")
@staff_required
def export_weekly_schedule():
    week_start = _week_from_request()
    assignments = (
        WeeklyShiftAssignment.query.filter_by(week_start_date=week_start)
        .join(Employee)
        .order_by(Employee.last_name)
        .all()
    )
    xlsx_bytes = render_weekly_schedule_xlsx(assignments)
    return send_file(
        BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"schedule-{week_start.isoformat()}.xlsx",
    )
