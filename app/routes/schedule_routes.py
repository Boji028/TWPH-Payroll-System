# app/routes/schedule_routes.py
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.decorators import staff_required
from app.extensions import db
from app.models.employee import Employee
from app.models.schedule import ScheduledShift, ShiftType

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


@schedule_bp.route("/log", methods=["GET", "POST"])
@staff_required
def log_schedule():
    employees = Employee.query.filter_by(status="active").order_by(Employee.last_name).all()
    if request.method == "POST":
        date_val = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        for employee in employees:
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
        flash("Schedule saved.", "success")
        return redirect(url_for("schedule.list_schedule", date=request.form["date"]))
    return render_template("schedule/log.html", employees=employees)
