from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.employee import Employee
from app.models.payroll import PayrollRun

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/landing.html", current_year=datetime.utcnow().year)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    active_employee_count = Employee.query.filter_by(status="active").count()
    recent_runs = PayrollRun.query.order_by(PayrollRun.period_start.desc()).limit(5).all()
    return render_template(
        "main/dashboard.html",
        active_employee_count=active_employee_count,
        recent_runs=recent_runs,
    )