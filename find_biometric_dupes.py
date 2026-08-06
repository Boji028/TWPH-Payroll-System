"""
One-off diagnostic script — not part of the app.
Lists every employee's employee_code and biometric_id side by side,
and flags any biometric_id that's used by more than one employee.

Run it from the same folder as run.py, with your venv activated:
    python find_biometric_dupes.py
"""
import os
from collections import defaultdict
from app import create_app
from app.extensions import db
from app.models.employee import Employee

app = create_app(os.environ.get("FLASK_ENV", "development"))

with app.app_context():
    employees = Employee.query.order_by(Employee.biometric_id).all()

    print(f"{'employee_code':<15} {'biometric_id':<15} {'name'}")
    print("-" * 50)

    seen = defaultdict(list)
    for e in employees:
        print(f"{e.employee_code:<15} {str(e.biometric_id):<15} {e.full_name}")
        if e.biometric_id is not None:
            seen[e.biometric_id].append(e)

    dupes = {bid: emps for bid, emps in seen.items() if len(emps) > 1}
    print("\n--- Duplicate biometric_id values ---")
    if not dupes:
        print("None found. (If you're still seeing the error, it may be the")
        print("specific NEW value you're typing in, not one already saved —")
        print("try the value you were entering when the error happened.)")
    else:
        for bid, emps in dupes.items():
            names = ", ".join(f"{e.employee_code} ({e.full_name})" for e in emps)
            print(f"biometric_id '{bid}' is used by: {names}")
