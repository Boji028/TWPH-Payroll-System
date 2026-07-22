"""
Run once after migrations to create the first login:
    python seed_admin.py
"""
from getpass import getpass
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()

with app.app_context():
    email = input("Admin email: ").strip()
    if User.query.filter_by(email=email).first():
        print("A user with that email already exists.")
    else:
        full_name = input("Full name: ").strip()
        password = getpass("Password: ")
        user = User(full_name=full_name, email=email, role="owner")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Admin user '{email}' created.")
