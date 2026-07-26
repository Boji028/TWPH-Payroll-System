"""
Weekly shift rotation - run once a week via Windows Task Scheduler to
auto-generate the upcoming week's shift assignments. Flips each active
employee's Opening/Closing shift from the previous week; rest days stay
at each employee's fixed default (Employee.rest_day) unless an admin
already set a manual override for that week (WeeklyShiftAssignment.is_override
- see app/services/schedule_rotation_service.py). New hires with no prior
assignment are balanced to whichever shift currently has fewer people.

Manual run (generates the upcoming Monday's week):
    python weekly_shift_rotation.py

(Re)generate a specific week instead:
    python weekly_shift_rotation.py --week 2026-08-03

Windows Task Scheduler setup: same pattern as Travel Worthy PH's
inquiry-cleanup task (see run_inquiry_cleanup.bat /
setup_inquiry_cleanup_scheduler.ps1 in that project) - a .bat wrapper plus
a PowerShell registration script, rather than a raw schtasks one-liner:
  1. run_weekly_rotation.bat - activates the venv and runs this script,
     checking %errorlevel% for success/failure.
  2. setup_weekly_rotation_scheduler.ps1 - registers run_weekly_rotation.bat
     as a weekly Task Scheduler task (default: Sunday 10:00 PM, before the
     new week starts). Must run as Administrator.
  3. setup_weekly_rotation_scheduler.bat - double-click this to elevate and
     run the .ps1 above without opening PowerShell manually.

Task Scheduler's "Task History" tab captures this script's stdout/exit
code automatically via the .bat wrapper.
"""
import argparse
import sys
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models.user import User
from app.services.schedule_rotation_service import generate_week


def _next_monday(today):
    days_ahead = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


def main():
    parser = argparse.ArgumentParser(description="Generate a week's shift rotation.")
    parser.add_argument("--week", help="Monday date (YYYY-MM-DD) to generate instead of the upcoming week")
    args = parser.parse_args()

    if args.week:
        week_start = date.fromisoformat(args.week)
        if week_start.weekday() != 0:
            print(f"Error: {week_start} is not a Monday.")
            sys.exit(1)
    else:
        week_start = _next_monday(date.today())

    app = create_app()
    with app.app_context():
        system_user = User.query.filter_by(role="owner").first()
        if system_user is None:
            print("Error: no owner-role user found to attribute this run to.")
            sys.exit(1)

        try:
            summary = generate_week(week_start, created_by_id=system_user.id)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Rotation failed: {e}")
            sys.exit(1)

    print(
        f"Week of {week_start}: {summary['assigned']} employee(s) assigned "
        f"({summary['new_hires_balanced']} new hire(s) balanced, "
        f"{summary['overrides_skipped']} manual override(s) left untouched)."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
