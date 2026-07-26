# PowerShell script to create a Windows Task Scheduler entry for the
# weekly shift rotation. Mirrors Travel Worthy PH's
# setup_inquiry_cleanup_scheduler.ps1 (same New-ScheduledTask* cmdlets,
# same admin check, same messaging), adapted to a weekly trigger instead
# of daily. Run this as Administrator.

param(
    [string]$Time = "22:00",  # Default: Sunday 10:00 PM, before the new week starts
    [string]$DayOfWeek = "Sunday",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
USAGE:
    powershell -ExecutionPolicy Bypass -File setup_weekly_rotation_scheduler.ps1

PARAMETERS:
    -Time "HH:MM"     : Set run time (default: 22:00)
    -DayOfWeek "Day"  : Set run day (default: Sunday)

EXAMPLES:
    # Run Sunday at 10:00 PM (default)
    powershell -ExecutionPolicy Bypass -File setup_weekly_rotation_scheduler.ps1

    # Run Monday at 6:00 AM instead
    powershell -ExecutionPolicy Bypass -File setup_weekly_rotation_scheduler.ps1 -DayOfWeek "Monday" -Time "06:00"
"@
    exit 0
}

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "`nHow to run as Administrator:"
    Write-Host "1. Press Win+X"
    Write-Host "2. Select 'Windows PowerShell (Admin)' or 'Terminal (Admin)'"
    Write-Host "3. Run: powershell -ExecutionPolicy Bypass -File setup_weekly_rotation_scheduler.ps1"
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Payroll System - Weekly Shift Rotation Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ProjectPath = "C:\Users\ENZO KOPS\Desktop\TravelWorthyPH_Payroll_System\Payroll_System"
$BatchFile = "$ProjectPath\run_weekly_rotation.bat"
$TaskName = "Weekly Shift Rotation"
$TaskDescription = "Weekly: auto-generate the upcoming week's shift rotation (flip Opening/Closing, keep each employee's fixed rest day, balance new hires)"

# Verify batch file exists
if (-not (Test-Path $BatchFile)) {
    Write-Host "ERROR: Batch file not found at: $BatchFile" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "   Task Name: $TaskName"
Write-Host "   Batch File: $BatchFile"
Write-Host "   Schedule: Weekly on $DayOfWeek at $Time"
Write-Host ""

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Task already exists. Updating..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create trigger (weekly, on the specified day/time)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $Time

# Create action
$action = New-ScheduledTaskAction -Execute $BatchFile

# Create settings. No -RunWithoutNetwork - that parameter doesn't exist on
# New-ScheduledTaskSettingsSet (verified via Get-Command ... -Syntax); the
# task already runs regardless of network availability by default as long
# as -RunOnlyIfNetworkAvailable (which we don't want) isn't set.
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

# Create principal (run with highest privileges)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask -TaskName $TaskName `
        -Description $TaskDescription `
        -Trigger $trigger `
        -Action $action `
        -Settings $settings `
        -Principal $principal `
        -Force | Out-Null

    Write-Host "Task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Schedule Details:" -ForegroundColor Yellow
    Write-Host "   Task: $TaskName"
    Write-Host "   Schedule: Weekly on $DayOfWeek at $Time"
    Write-Host "   Status: Enabled"
    Write-Host ""

    # Enable the task
    Enable-ScheduledTask -TaskName $TaskName | Out-Null

    Write-Host "To manage the task:" -ForegroundColor Cyan
    Write-Host "   1. Open Task Scheduler: Press Win+R, type 'taskschd.msc'"
    Write-Host "   2. Go to Task Scheduler Library"
    Write-Host "   3. Find: '$TaskName'"
    Write-Host "   4. Right-click -> Properties to configure"
    Write-Host ""

    Write-Host "To test it:" -ForegroundColor Cyan
    Write-Host "   1. Open Task Scheduler"
    Write-Host "   2. Find: '$TaskName'"
    Write-Host "   3. Right-click -> Run"
    Write-Host "   4. Check its 'Last Run Result' column, or History tab, for the exit code"
    Write-Host ""

    Write-Host "Setup complete!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to create scheduled task: $_" -ForegroundColor Red
    exit 1
}
