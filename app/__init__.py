from flask import Flask
from app.config import config
from app.extensions import db, login_manager, csrf, migrate
import cloudinary

def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Bind extensions to this app instance
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    cloudinary.config(secure=True)

    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.employee_routes import employee_bp
    from app.routes.attendance_routes import attendance_bp
    from app.routes.payroll_routes import payroll_bp
    from app.routes.self_service_routes import self_service_bp
    from app.routes.leave_routes import leave_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(employee_bp, url_prefix="/employees")
    app.register_blueprint(attendance_bp, url_prefix="/attendance")
    app.register_blueprint(payroll_bp, url_prefix="/payroll")
    app.register_blueprint(self_service_bp, url_prefix="/my")
    app.register_blueprint(leave_bp, url_prefix="/leave")

    # Import models so Flask-Migrate can detect them
    from app.models import employee, attendance, payroll, deduction, user, leave

    return app
