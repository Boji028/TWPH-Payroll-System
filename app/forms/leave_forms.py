from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, ValidationError


class LeaveRequestForm(FlaskForm):
    leave_type = SelectField(
        "Type",
        choices=[
            ("vacation", "Vacation"),
            ("sick", "Sick"),
            ("unpaid", "Unpaid"),
            ("other", "Other"),
        ],
        validators=[DataRequired()],
    )
    start_date = DateField("Start date", validators=[DataRequired()])
    end_date = DateField("End date", validators=[DataRequired()])
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Submit request")

    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError("End date can't be before the start date.")
