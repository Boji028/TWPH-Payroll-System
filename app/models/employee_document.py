# app/models/employee_document.py
from datetime import datetime, timedelta
from enum import Enum

from app.extensions import db


class DocumentType(str, Enum):
    GOVERNMENT_ID = "government_id"
    CONTRACT = "contract"
    CERTIFICATION = "certification"
    RESUME = "resume"
    OTHER = "other"


class EmployeeDocument(db.Model):
    __tablename__ = "employee_documents"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)

    doc_type = db.Column(db.Enum(DocumentType), nullable=False, default=DocumentType.OTHER)
    label = db.Column(db.String(150), nullable=False)          # e.g. "SSS ID", "Employment Contract 2024"

    cloudinary_url = db.Column(db.String(500), nullable=False)
    cloudinary_public_id = db.Column(db.String(255), nullable=False)  # needed to delete from Cloudinary later
    original_filename = db.Column(db.String(255), nullable=False)

    expiry_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    employee = db.relationship(
        "Employee",
        backref=db.backref("documents", lazy="dynamic", cascade="all, delete-orphan"),
    )
    uploaded_by = db.relationship("User")

    @property
    def is_expired(self):
        return self.expiry_date is not None and self.expiry_date < datetime.utcnow().date()

    @property
    def is_expiring_soon(self, days=30):
        if not self.expiry_date:
            return False
        return datetime.utcnow().date() <= self.expiry_date <= (datetime.utcnow().date() + timedelta(days=days))

    def __repr__(self):
        return f"<EmployeeDocument {self.label} (employee_id={self.employee_id})>"