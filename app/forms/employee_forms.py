from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Email


class EmployeeForm(FlaskForm):
    employee_code = StringField("Employee Code", validators=[DataRequired()])
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    email = StringField("Email", validators=[Optional(), Email()])
    phone = StringField("Phone", validators=[Optional()])
    department = StringField("Department", validators=[Optional()])
    position = StringField("Position", validators=[Optional()])

    pay_type = SelectField(
        "Pay Type",
        choices=[("monthly", "Monthly Salary"), ("daily", "Daily Rate"), ("hourly", "Hourly Rate")],
        validators=[DataRequired()],
    )
    monthly_rate = DecimalField("Monthly Rate", validators=[Optional()])
    daily_rate = DecimalField("Daily Rate", validators=[Optional()])
    hourly_rate = DecimalField("Hourly Rate", validators=[Optional()])

    date_hired = DateField("Date Hired", validators=[DataRequired()])
    submit = SubmitField("Save Employee")
