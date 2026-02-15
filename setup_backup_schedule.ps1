# SPRA Database Backup - Windows Task Scheduler Setup
# Run this script as Administrator to schedule daily backups

param(
    [ValidateSet("Install", "Remove", "Test")]
    [string]$Action = "Install",
    
    [ValidateSet(0,1,2,3,4,5,6)]
    [int]$DayOfWeek = 0,  # 0=Sunday, 1=Monday, etc. Default=daily
    
    [string]$Time = "02:00",  # 2:00 AM
    
    [string]$TaskName = "SPRA-Database-Backup",
    
    [string]$ScriptPath = "C:\Users\chugh\Desktop\SPRA\backup_schedule.bat"
)

function Install-BackupTask {
    Write-Host "Setting up SPRA Database Backup Task Scheduler..." -ForegroundColor Cyan
    
    # Check if running as administrator
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
        Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
        exit 1
    }
    
    # Verify backup script exists
    if (-not (Test-Path $ScriptPath)) {
        Write-Host "ERROR: Backup script not found at: $ScriptPath" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Script found: $ScriptPath" -ForegroundColor Green
    
    # Check if task already exists
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "⚠ Task '$TaskName' already exists. Removing old task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
    }
    
    # Create trigger
    if ($DayOfWeek -eq 0) {
        # Daily trigger
        $trigger = New-ScheduledTaskTrigger -Daily -At $Time
        Write-Host "  Trigger: Daily at $Time" -ForegroundColor Cyan
    } else {
        # Weekly trigger
        $dayName = @("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")[$DayOfWeek]
        $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $dayName -At $Time
        Write-Host "  Trigger: Every $dayName at $Time" -ForegroundColor Cyan
    }
    
    # Create action (run the batch file)
    $action = New-ScheduledTaskAction -Execute $ScriptPath
    
    # Create settings (run with highest privileges, run even if user not logged in)
    $settings = New-ScheduledTaskSettingsSet -RunWithoutNetwork:$false -StartWhenAvailable:$true -DontStopIfGoingOnBattery:$false
    
    # Register the task
    try {
        Register-ScheduledTask -TaskName $TaskName -Trigger $trigger -Action $action -Settings $settings -RunLevel Highest | Out-Null
        Write-Host "✓ Task '$TaskName' created successfully!" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Failed to create task: $_" -ForegroundColor Red
        exit 1
    }
    
    # Verify task was created
    $createdTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($createdTask) {
        Write-Host "`n✓ Task Details:" -ForegroundColor Green
        Write-Host "  Name:       $($createdTask.TaskName)" 
        Write-Host "  Status:     $($createdTask.State)"
        Write-Host "  Path:       $($createdTask.TaskPath)"
        Write-Host "  Next Run:   $($createdTask.Triggers[0].NextExecutionTime)" 
        Write-Host "`n✓ Backup will run automatically every day at $Time" -ForegroundColor Green
        Write-Host "  Check backup status in: .\backups\backup.log" -ForegroundColor Cyan
    }
}

function Remove-BackupTask {
    Write-Host "Removing SPRA Database Backup Task Scheduler..." -ForegroundColor Cyan
    
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
        exit 1
    }
    
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false | Out-Null
        Write-Host "✓ Task '$TaskName' removed successfully" -ForegroundColor Green
    } else {
        Write-Host "⚠ Task '$TaskName' not found" -ForegroundColor Yellow
    }
}

function Test-BackupTask {
    Write-Host "Testing SPRA Database Backup..." -ForegroundColor Cyan
    
    if (-not (Test-Path $ScriptPath)) {
        Write-Host "ERROR: Backup script not found at: $ScriptPath" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Running backup script: $ScriptPath`n" -ForegroundColor Cyan
    & cmd /c $ScriptPath
    
    # Check results
    $backupDir = Split-Path $ScriptPath
    $backups = Get-ChildItem "$backupDir\backups\spra_backup_*.sql.gz" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    
    if ($backups) {
        Write-Host "`n✓ Backup test successful!" -ForegroundColor Green
        Write-Host "Latest backup: $($backups[0].Name) ($([math]::Round($backups[0].Length/1KB, 2)) KB)" -ForegroundColor Green
    } else {
        Write-Host "`n⚠ No backups found" -ForegroundColor Yellow
    }
    
    # Show backup log
    $logFile = "$backupDir\backup.log"
    if (Test-Path $logFile) {
        Write-Host "`nRecent log entries:" -ForegroundColor Cyan
        Get-Content $logFile -Tail 10
    }
}

# Execute requested action
switch ($Action) {
    "Install" { Install-BackupTask }
    "Remove" { Remove-BackupTask }
    "Test" { Test-BackupTask }
}

Write-Host "`nDone!" -ForegroundColor Green
