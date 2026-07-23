from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional, Length

SCORE_CHOICES = [(str(i), str(i)) for i in range(1, 6)]


class ReviewForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    review_date = DateField("Review date", validators=[DataRequired()])

    job_knowledge_score = SelectField("Job Knowledge", choices=SCORE_CHOICES, validators=[DataRequired()])
    job_knowledge_comment = StringField("Comment", validators=[Optional(), Length(max=255)])

    quality_of_work_score = SelectField("Quality of Work", choices=SCORE_CHOICES, validators=[DataRequired()])
    quality_of_work_comment = StringField("Comment", validators=[Optional(), Length(max=255)])

    communication_score = SelectField("Communication", choices=SCORE_CHOICES, validators=[DataRequired()])
    communication_comment = StringField("Comment", validators=[Optional(), Length(max=255)])

    teamwork_score = SelectField("Teamwork", choices=SCORE_CHOICES, validators=[DataRequired()])
    teamwork_comment = StringField("Comment", validators=[Optional(), Length(max=255)])

    punctuality_score = SelectField("Punctuality & Attendance", choices=SCORE_CHOICES, validators=[DataRequired()])
    punctuality_comment = StringField("Comment", validators=[Optional(), Length(max=255)])

    overall_comments = TextAreaField("Overall comments", validators=[Optional()])


class GoalForm(FlaskForm):
    description = StringField("Goal", validators=[DataRequired(), Length(max=255)])
    target_date = DateField("Target date", validators=[Optional()])


class GoalStatusForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("not_met", "Not Met"),
        ],
        validators=[DataRequired()],
    )
