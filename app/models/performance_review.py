# app/models/performance_review.py
from datetime import datetime
from enum import Enum

from app.extensions import db


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"


class GoalStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NOT_MET = "not_met"


# Fixed rating categories - every review scores all of these 1-5.
RATING_CATEGORIES = [
    "job_knowledge",
    "quality_of_work",
    "communication",
    "teamwork",
    "punctuality",
]

RATING_CATEGORY_LABELS = {
    "job_knowledge": "Job Knowledge",
    "quality_of_work": "Quality of Work",
    "communication": "Communication",
    "teamwork": "Teamwork",
    "punctuality": "Punctuality & Attendance",
}

GOAL_STATUS_LABELS = {
    GoalStatus.NOT_STARTED: "Not Started",
    GoalStatus.IN_PROGRESS: "In Progress",
    GoalStatus.COMPLETED: "Completed",
    GoalStatus.NOT_MET: "Not Met",
}


class PerformanceReview(db.Model):
    """An ad-hoc performance review created by admin/HR for an employee.
    No manager role or fixed cycle - staff creates one whenever needed.
    Draft reviews are only visible to staff; self-service only sees
    reviews once finalized (see status)."""

    __tablename__ = "performance_reviews"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(150), nullable=False)  # e.g. "Q3 2026 Review"
    review_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(ReviewStatus), nullable=False, default=ReviewStatus.DRAFT)
    overall_comments = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finalized_at = db.Column(db.DateTime, nullable=True)

    employee = db.relationship(
        "Employee",
        backref=db.backref("performance_reviews", lazy="dynamic", cascade="all, delete-orphan"),
    )
    reviewed_by = db.relationship("User")
    ratings = db.relationship(
        "ReviewRating", backref="review", lazy="joined", cascade="all, delete-orphan"
    )
    # Goals created during this review. Not cascade-deleted with the review -
    # a goal outlives the review that created it (see PerformanceGoal).
    goals = db.relationship("PerformanceGoal", backref="review", lazy="dynamic")

    @property
    def average_score(self):
        if not self.ratings:
            return None
        return round(sum(r.score for r in self.ratings) / len(self.ratings), 1)

    @property
    def is_finalized(self):
        return self.status == ReviewStatus.FINALIZED

    def __repr__(self):
        return f"<PerformanceReview {self.title} (employee_id={self.employee_id})>"


class ReviewRating(db.Model):
    """One category score within a PerformanceReview. One row per category
    in RATING_CATEGORIES for every review."""

    __tablename__ = "review_ratings"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("performance_reviews.id"), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)  # one of RATING_CATEGORIES
    score = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.String(255), nullable=True)

    @property
    def category_label(self):
        return RATING_CATEGORY_LABELS.get(self.category, self.category)

    def __repr__(self):
        return f"<ReviewRating {self.category}={self.score}>"


class PerformanceGoal(db.Model):
    """A goal tracked for an employee. Tied to the review that created it
    (review_id) but belongs primarily to the employee, since a goal is
    usually followed up on in a later review - it is not deleted if that
    review is deleted, only unlinked (see delete_review in employee_routes)."""

    __tablename__ = "performance_goals"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)
    review_id = db.Column(db.Integer, db.ForeignKey("performance_reviews.id"), nullable=True, index=True)

    description = db.Column(db.String(255), nullable=False)
    target_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.Enum(GoalStatus), nullable=False, default=GoalStatus.NOT_STARTED)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship(
        "Employee",
        backref=db.backref("performance_goals", lazy="dynamic", cascade="all, delete-orphan"),
    )

    @property
    def status_label(self):
        return GOAL_STATUS_LABELS.get(self.status, self.status)

    def __repr__(self):
        return f"<PerformanceGoal {self.description[:30]!r} ({self.status})>"
