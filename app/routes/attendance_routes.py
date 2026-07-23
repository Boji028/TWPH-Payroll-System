from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.decorators import staff_required
from app.extensions import db
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.services.attendance_service import get_pay_period, build_attendance_grid
from app.forms.attendance_import_form import BiometricImportForm
from app.services.biometric_import_service import import_attendance, BiometricImportError

attendance_bp = Blueprint("attendance", __name__)


@attendance_bp.route("/")
@staff_required
def list_attendance():
    date_str = request.args.get("date")
    anchor_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.utcnow().date()
    )
    period_start, period_end, payday = get_pay_period(anchor_date)
    dates, rows = build_attendance_grid(period_start, period_end)
    return render_template(
        "attendance/list.html",
        dates=dates, rows=rows,
        period_start=period_start, period_end=period_end, payday=payday,
        prev_anchor=period_start - timedelta(days=1),
        next_anchor=period_end + timedelta(days=1),
    )


@attendance_bp.route("/log", methods=["GET", "POST"])
@staff_required
def log_attendance():
    employees = Employee.query.filter_by(status="active").order_by(Employee.last_name).all()
    if request.method == "POST":
        date_val = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        for employee in employees:
            hours = request.form.get(f"hours_{employee.id}")
            status = request.form.get(f"status_{employee.id}", "present")
            if hours:
                existing = Attendance.query.filter_by(
                    employee_id=employee.id, date=date_val
                ).first()
                if existing:
                    existing.hours_worked = hours
                    existing.status = status
                else:
                    db.session.add(
                        Attendance(
                            employee_id=employee.id,
                            date=date_val,
                            hours_worked=hours,
                            status=status,
                        )
                    )
        db.session.commit()
        flash("Attendance saved.", "success")
        return redirect(url_for("attendance.list_attendance", date=request.form["date"]))
    return render_template("attendance/log.html", employees=employees)


@attendance_bp.route("/import", methods=["GET", "POST"])
@staff_required
def import_attendance_view():
    form = BiometricImportForm()
    if form.validate_on_submit():
        try:
            summary = import_attendance(form.file.data.read())
        except BiometricImportError as e:
            flash(str(e), "danger")
            return render_template("attendance/import.html", form=form)
        return render_template("attendance/import.html", form=BiometricImportForm(), summary=summary)
    return render_template("attendance/import.html", form=form)
