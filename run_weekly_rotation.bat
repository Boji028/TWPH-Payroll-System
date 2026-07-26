@echo off
REM Batch wrapper for weekly_shift_rotation.py - scheduled with Windows Task
REM Scheduler (see setup_weekly_rotation_scheduler.ps1). Mirrors Travel
REM Worthy PH's run_inquiry_cleanup.bat, minus the trailing "pause" - that
REM would hang forever waiting for a keypress when run unattended by Task
REM Scheduler. Double-click this file directly (from an already-open
REM terminal, or via "cmd /k run_weekly_rotation.bat") if you want to see
REM the output stay on screen for a manual test run.

echo.
echo ========================================
echo Weekly Shift Rotation
echo Time: %date% %time%
echo ========================================
echo.

REM Navigate to project directory
cd /d "C:\Users\ENZO KOPS\Desktop\TravelWorthyPH_Payroll_System\Payroll_System"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run rotation script
echo Starting weekly shift rotation...
python weekly_shift_rotation.py

REM Check if successful
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Weekly shift rotation completed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Weekly shift rotation failed with error code: %errorlevel%
    echo ========================================
)
