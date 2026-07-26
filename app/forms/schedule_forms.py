from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired

from app.models.schedule import ShiftType, SHIFT_LABELS, WEEKDAY_LABELS


class WeeklyAssignmentForm(FlaskForm):
    """Admin override of one employee's shift/rest day for one specific
    week. Saving always marks the row is_override=True so the next
    rotation run leaves it alone."""

    shift_type = SelectField(
        "Shift",
        choices=[(t.value, SHIFT_LABELS[t]) for t in (ShiftType.OPENING, ShiftType.CLOSING)],
        validators=[DataRequired()],
    )
    rest_day = SelectField(
        "Rest Day",
        choices=[(i, name) for i, name in WEEKDAY_LABELS.items()],
        coerce=int,
        validators=[DataRequired()],
    )
    submit = SubmitField("Save")
