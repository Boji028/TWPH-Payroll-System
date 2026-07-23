from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired


class BiometricImportForm(FlaskForm):
    file = FileField(
        "Scanner export file (.xls)",
        validators=[
            FileRequired(),
            FileAllowed(["xls"], "The scanner exports .xls files - other formats aren't supported yet."),
        ],
    )
