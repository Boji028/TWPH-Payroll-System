# app/routes/workforce_routes.py
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from app.decorators import staff_required
from app.services.workforce_service import get_workforce_roster

workforce_bp = Blueprint("workforce", __name__)


@workforce_bp.route("/")
@staff_required
def list_workforce():
    roster = get_workforce_roster()
    return render_template("workforce/list.html", roster=roster)


@workforce_bp.route("/data")
@staff_required
def data():
    """JSON used by the polling JS on both the Workforce page and the
    dashboard widget. ?limit=N caps the number of rows (used by the
    smaller dashboard version)."""
    limit = request.args.get("limit", type=int)
    roster = get_workforce_roster(limit=limit)
    return jsonify({"employees": roster, "generated_at": datetime.utcnow().isoformat() + "Z"})
