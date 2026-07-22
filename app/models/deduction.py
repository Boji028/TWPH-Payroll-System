from app.extensions import db


class Deduction(db.Model):
    """A single deduction line item on a payslip. Kept generic on purpose:
    'type' covers simple items today (cash_advance, loan, tardiness) and
    can later include statutory ones (sss, philhealth, pagibig, withholding_tax)
    once that requirement is confirmed, without changing the schema."""

    __tablename__ = "deductions"

    id = db.Column(db.Integer, primary_key=True)
    payslip_id = db.Column(db.Integer, db.ForeignKey("payslips.id"), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g. 'cash_advance', 'loan', 'tardiness'
    description = db.Column(db.String(255))
    amount = db.Column(db.Numeric(12, 2), nullable=False)

    def __repr__(self):
        return f"<Deduction {self.type} {self.amount}>"
