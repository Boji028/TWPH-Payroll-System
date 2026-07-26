@echo off
REM Run the PowerShell setup script as Administrator. Mirrors Travel
REM Worthy PH's setup_inquiry_cleanup_scheduler.bat, but:
REM   1. Calls powershell.exe by its full path instead of relying on it
REM      being on PATH.
REM   2. Waits for the elevated run to finish and checks its actual exit
REM      code before claiming success - Start-Process alone (without
REM      -Wait -PassThru) returns as soon as it launches the elevated
REM      process, so the original version always printed "Setup
REM      complete!" even when the elevated script never ran at all.

cls
echo.
echo ========================================
echo Weekly Shift Rotation - Scheduler Setup
echo ========================================
echo.
echo This will create a weekly shift rotation task in Windows Task Scheduler.
echo.

REM Get current directory
cd /d "%~dp0"

set "PWSH=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%PWSH%" (
    echo ERROR: PowerShell not found at "%PWSH%"
    echo Setup did NOT run - the scheduled task was NOT created.
    echo.
    pause
    exit /b 1
)

REM Launch setup_weekly_rotation_scheduler.ps1 elevated, wait for it to
REM finish, and propagate its real exit code back out via this outer
REM PowerShell process's own exit code.
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "try { $p = Start-Process -FilePath '%PWSH%' -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0setup_weekly_rotation_scheduler.ps1\"' -Verb RunAs -Wait -PassThru; exit $p.ExitCode } catch { Write-Host $_.Exception.Message; exit 1 }"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Setup complete! Check Task Scheduler for the "Weekly Shift Rotation" task.
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Setup FAILED - error code: %errorlevel%
    echo The scheduled task was NOT created. This happens if you declined
    echo the "Run as Administrator" prompt, or if
    echo setup_weekly_rotation_scheduler.ps1 itself hit an error. Re-run it
    echo directly from an Administrator PowerShell window to see full output:
    echo   powershell -ExecutionPolicy Bypass -File setup_weekly_rotation_scheduler.ps1
    echo ========================================
)

echo.
pause
