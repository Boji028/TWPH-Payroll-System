from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from app.decorators import staff_required
from app.models.payroll import PayrollRun
from app.services.dashboard_service import get_dashboard_stats
from app.services.workforce_service import get_workforce_roster

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "employee":
            return redirect(url_for("self_service.dashboard"))
        return redirect(url_for("main.dashboard"))
    return render_template("main/landing.html", current_year=datetime.utcnow().year)


@main_bp.route("/dashboard")
@staff_required
def dashboard():
    stats = get_dashboard_stats()
    recent_runs = PayrollRun.query.order_by(PayrollRun.period_start.desc()).limit(5).all()
    workforce_preview = get_workforce_roster(limit=6)
    return render_template(
        "main/dashboard.html", recent_runs=recent_runs, workforce_preview=workforce_preview, **stats
    )