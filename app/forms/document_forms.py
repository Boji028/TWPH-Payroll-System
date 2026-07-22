from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SelectField, StringField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional, Length


class DocumentUploadForm(FlaskForm):
    doc_type = SelectField(
        "Document Type",
        choices=[
            ("government_id", "Government ID"),
            ("contract", "Contract"),
            ("certification", "Certification"),
            ("resume", "Resume"),
            ("other", "Other"),
        ],
        validators=[DataRequired()],
    )
    label = StringField("Label", validators=[DataRequired(), Length(max=150)])
    file = FileField(
        "File",
        validators=[
            FileRequired(),
            FileAllowed(["pdf", "jpg", "jpeg", "png"], "PDF, JPG, or PNG only."),
        ],
    )
    expiry_date = DateField("Expiry Date", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])