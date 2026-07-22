"""Employee self-service views — scoped to whichever Employee the current
User account is linked to via User.employee_id. Any authenticated user
with an employee_id can reach these, regardless of role, so an owner or
HR staffer who also has an Employee record can use their own self-service
view too."""
import requests
from app.models.employee_document import EmployeeDocument
from io import BytesIO
from flask import Blueprint, render_template, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.payroll import Payslip
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest
from app.forms.leave_forms import LeaveRequestForm
from app.services.pdf_service import render_payslip_pdf

self_service_bp = Blueprint("self_service", __name__)


def _current_employee():
    if not current_user.employee_id:
        abort(404)
    return current_user.employee


@self_service_bp.route("/")
@login_required
def dashboard():
    employee = _current_employee()
    recent_payslips = (
        employee.payslips.order_by(Payslip.created_at.desc()).limit(3).all()
    )
    return render_template(
        "self_service/dashboard.html", employee=employee, recent_payslips=recent_payslips
    )


@self_service_bp.route("/attendance")
@login_required
def attendance():
    employee = _current_employee()
    records = (
        employee.attendance_records.order_by(Attendance.date.desc()).limit(30).all()
    )
    return render_template("self_service/attendance.html", employee=employee, records=records)


@self_service_bp.route("/payslips")
@login_required
def payslips():
    employee = _current_employee()
    slips = employee.payslips.order_by(Payslip.created_at.desc()).all()
    return render_template("self_service/payslips.html", employee=employee, payslips=slips)


@self_service_bp.route("/payslips/<int:payslip_id>")
@login_required
def payslip_detail(payslip_id):
    employee = _current_employee()
    payslip = Payslip.query.get_or_404(payslip_id)
    if payslip.employee_id != employee.id:
        abort(403)
    return render_template("self_service/payslip_detail.html", payslip=payslip)


@self_service_bp.route("/payslips/<int:payslip_id>/pdf")
@login_required
def payslip_pdf(payslip_id):
    employee = _current_employee()
    payslip = Payslip.query.get_or_404(payslip_id)
    if payslip.employee_id != employee.id:
        abort(403)
    pdf_bytes = render_payslip_pdf(payslip)
    filename = f"payslip-{payslip.payroll_run.period_start}.pdf"
    return send_file(
        BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename
    )
@self_service_bp.route("/leave", methods=["GET", "POST"])
@login_required
def leave():
    employee = _current_employee()
    form = LeaveRequestForm()
    if form.validate_on_submit():
        leave_request = LeaveRequest(
            employee_id=employee.id,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data,
        )
        db.session.add(leave_request)
        db.session.commit()
        flash("Leave request submitted.", "success")
        return redirect(url_for("self_service.leave"))
    requests = employee.leave_requests.order_by(LeaveRequest.requested_at.desc()).all()
    return render_template("self_service/leave.html", employee=employee, form=form, requests=requests)
@self_service_bp.route("/documents")
@login_required
def documents():
    employee = _current_employee()
    docs = employee.documents.order_by(EmployeeDocument.uploaded_at.desc()).all()
    return render_template("self_service/documents.html", employee=employee, documents=docs)
@self_service_bp.route("/documents/<int:document_id>/download")
@login_required
def download_document(document_id):
    employee = _current_employee()
    document = EmployeeDocument.query.get_or_404(document_id)
    if document.employee_id != employee.id:
        abort(403)
    response = requests.get(document.cloudinary_url)
    response.raise_for_status()
    return send_file(
        BytesIO(response.content),
        mimetype=response.headers.get("Content-Type", "application/octet-stream"),
        as_attachment=True,
        download_name=document.original_filename,
    )