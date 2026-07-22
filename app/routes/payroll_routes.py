from io import BytesIO
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from app.decorators import staff_required
from app.extensions import db
from app.models.payroll import PayrollRun, Payslip
from app.services.payroll_service import process_payroll_run
from app.services.pdf_service import render_payslip_pdf
from datetime import datetime

payroll_bp = Blueprint("payroll", __name__)


@payroll_bp.route("/")
@staff_required
def list_runs():
    runs = PayrollRun.query.order_by(PayrollRun.period_start.desc()).all()
    return render_template("payroll/list.html", runs=runs)


@payroll_bp.route("/new", methods=["GET", "POST"])
@staff_required
def new_run():
    if request.method == "POST":
        period_start = datetime.strptime(request.form["period_start"], "%Y-%m-%d").date()
        period_end = datetime.strptime(request.form["period_end"], "%Y-%m-%d").date()
        run = PayrollRun(period_start=period_start, period_end=period_end, status="draft")
        db.session.add(run)
        db.session.commit()
        flash("Payroll run created. Review and process when ready.", "success")
        return redirect(url_for("payroll.view_run", run_id=run.id))
    return render_template("payroll/new.html")


@payroll_bp.route("/<int:run_id>")
@staff_required
def view_run(run_id):
    run = PayrollRun.query.get_or_404(run_id)
    return render_template("payroll/view.html", run=run)


@payroll_bp.route("/<int:run_id>/process", methods=["POST"])
@staff_required
def process_run(run_id):
    run = PayrollRun.query.get_or_404(run_id)
    if run.status != "draft":
        flash("This payroll run has already been processed.", "warning")
        return redirect(url_for("payroll.view_run", run_id=run.id))

    process_payroll_run(run)  # core computation lives in services/payroll_service.py
    flash("Payroll processed successfully.", "success")
    return redirect(url_for("payroll.view_run", run_id=run.id))


@payroll_bp.route("/payslip/<int:payslip_id>")
@staff_required
def view_payslip(payslip_id):
    payslip = Payslip.query.get_or_404(payslip_id)
    return render_template("payroll/payslip.html", payslip=payslip)


@payroll_bp.route("/payslip/<int:payslip_id>/pdf")
@staff_required
def download_payslip_pdf(payslip_id):
    payslip = Payslip.query.get_or_404(payslip_id)
    pdf_bytes = render_payslip_pdf(payslip)
    filename = f"payslip-{payslip.employee.employee_code}-{payslip.payroll_run.period_start}.pdf"
    return send_file(
        BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename
    )
