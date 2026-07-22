from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user
from app.decorators import staff_required
from app.extensions import db
from app.models.leave import LeaveRequest

leave_bp = Blueprint("leave", __name__)


@leave_bp.route("/")
@staff_required
def list_requests():
    pending = (
        LeaveRequest.query.filter_by(status="pending")
        .order_by(LeaveRequest.requested_at)
        .all()
    )
    reviewed = (
        LeaveRequest.query.filter(LeaveRequest.status != "pending")
        .order_by(LeaveRequest.reviewed_at.desc())
        .limit(20)
        .all()
    )
    return render_template("leave/list.html", pending=pending, reviewed=reviewed)


@leave_bp.route("/<int:request_id>/approve", methods=["POST"])
@staff_required
def approve(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    if leave_request.status != "pending":
        flash("This request has already been reviewed.", "warning")
        return redirect(url_for("leave.list_requests"))
    leave_request.status = "approved"
    leave_request.reviewed_by_id = current_user.id
    leave_request.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f"Approved {leave_request.employee.full_name}'s leave request.", "success")
    return redirect(url_for("leave.list_requests"))


@leave_bp.route("/<int:request_id>/reject", methods=["POST"])
@staff_required
def reject(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    if leave_request.status != "pending":
        flash("This request has already been reviewed.", "warning")
        return redirect(url_for("leave.list_requests"))
    leave_request.status = "rejected"
    leave_request.reviewed_by_id = current_user.id
    leave_request.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f"Rejected {leave_request.employee.full_name}'s leave request.", "info")
    return redirect(url_for("leave.list_requests"))
