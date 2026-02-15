# Schedule SPRA Backup with Windows Task Scheduler

## Automatic Setup (PowerShell)

Run PowerShell as Administrator and execute:

```powershell
# Create backup task
$taskName = "SPRA Daily Backup"
$taskPath = "\SPRA\"
$scriptPath = "C:\Users\chugh\Desktop\SPRA\backup_schedule.bat"

# Create trigger (2:00 AM daily)
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

# Create action
$action = New-ScheduledTaskAction -Execute $scriptPath

# Create task settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RunOnlyIfIdle

# Register the task
Register-ScheduledTask `
    -TaskName $taskName `
    -TaskPath $taskPath `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -RunLevel Highest `
    -Description "SPRA Database backup - runs daily at 2:00 AM"

Write-Host "Task created: $taskName"
Write-Host "Schedule: Daily at 2:00 AM"
```

---

## Manual Setup (GUI)

If you prefer the UI:

1. **Open Task Scheduler**
   - Press `Win + R` → type `taskschd.msc` → Enter

2. **Create New Task**
   - Right-click "Task Scheduler Library" → "Create Task"
   - Name: `SPRA Daily Backup`
   - Location: `\SPRA\`
   - Description: `SPRA Database backup - runs daily at 2:00 AM`
   - ✓ Check "Run with highest privileges"

3. **Configure Trigger (Schedule)**
   - Click "Triggers" tab
   - Click "New..."
   - Begin the task: `On a schedule`
   - Daily
   - Start: `[Today's date]`
   - Time: `02:00:00` (2:00 AM)
   - Repeat every: `1` day
   - For a duration of: `Indefinitely`
   - ✓ Enabled
   - Click OK

4. **Configure Action (Run Script)**
   - Click "Actions" tab
   - Click "New..."
   - Action: `Start a program`
   - Program/script: `C:\Users\chugh\Desktop\SPRA\backup_schedule.bat`
   - Click OK

5. **Configure Conditions**
   - Click "Conditions" tab
   - ✗ Uncheck "Start the task only if the computer is on AC power"
   - ✓ Check "Start a new instance..." if running again while already running
   - Click OK

6. **Test the Task**
   - Right-click the task → "Run"
   - Check backups folder: `C:\Users\chugh\Desktop\SPRA\backups\`
   - Check log: `C:\Users\chugh\Desktop\SPRA\backups\backup.log`

---

## Verify Backup is Working

```powershell
# Check if task exists
Get-ScheduledTask | Where-Object {$_.TaskName -eq "SPRA Daily Backup"}

# View backup folder
Get-ChildItem C:\Users\chugh\Desktop\SPRA\backups\

# View backup log
Get-Content C:\Users\chugh\Desktop\SPRA\backups\backup.log

# Check last run time
Get-ScheduledTaskInfo -TaskName "SPRA Daily Backup"

# Manually trigger backup
C:\Users\chugh\Desktop\SPRA\backup_schedule.bat
```

---

## Troubleshooting

**Backup not running?**
- Check Task Scheduler > History
- Check backups folder exists
- Run manually: `backup_schedule.bat`
- Check `.env` variables are set

**PostgreSQL not found?**
- psql must be in PATH
- Or update backup script with full psql path

**Backup file too large?**
- Archives are compressed (.sql.gz)
- Should be 1-10 MB typical
- Increase RETENTION_DAYS in `.env` if needed

---

## Backup Files

All backups stored in: `C:\Users\chugh\Desktop\SPRA\backups\`

File naming: `spra_backup_YYYYMMDD_HHMMSS.sql.gz`

Example:
```
spra_backup_20260216_020000.sql.gz   (2.5 MB)
spra_backup_20260215_020000.sql.gz   (2.4 MB)
spra_backup_20260214_020000.sql.gz   (2.3 MB)
```

Kept for: 30 days (configurable in `.env` - RETENTION_DAYS)
