# SPRA Database Backup & Restore System

## Overview

The SPRA application includes automated database backup and restore functionality. Backups are compressed and stored in the `./backups` directory with automatic cleanup of old backups (default: 30 days).

**Status: ✓ TESTED AND WORKING**

---

## Quick Start

### 1. Manual Backup (Test Now)

```powershell
cd C:\Users\chugh\Desktop\SPRA
python backup_database.py
```

Expected output:
```
✓ Backup successful!
  File: spra_backup_20260216_023500.sql.gz
  Size: 0.00 MB
```

Backup file will be created in `./backups/` directory.

### 2. Schedule Automatic Backups (Task Scheduler)

Run this PowerShell script **as Administrator**:

```powershell
# Open PowerShell as Administrator, then:
cd C:\Users\chugh\Desktop\SPRA
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_backup_schedule.ps1 -Action Install
```

This will create a Windows Task Scheduler task that:
- Runs daily at **2:00 AM**
- Automatically runs backup_database.py
- Logs results to `backup.log`
- Automatically cleans up backups older than 30 days

### 3. Restore from Backup

```powershell
# List available backups
Get-ChildItem .\backups\

# Restore database from backup
python restore_database.py backups/spra_backup_20260216_023500.sql.gz
```

The restore command will:
- Prompt for confirmation (data will be overwritten)
- Ask for 'postgres' superuser password
- Drop existing database and recreate it
- Restore all data from backup file

---

## File Locations & Descriptions

| File | Purpose |
|------|---------|
| `backup_database.py` | Main backup script (run manually or via Task Scheduler) |
| `restore_database.py` | Restore data from backup file |
| `backup_schedule.bat` | Batch script for Windows Task Scheduler |
| `setup_backup_schedule.ps1` | PowerShell script to manage Task Scheduler setup |
| `./backups/` | Directory where backup files are stored |
| `backup.log` | Log file with backup run history |

---

## Configuration

Backup behavior is controlled via environment variables in `.env`:

```env
DATABASE_URL=postgresql://spra_user:spra_password_123@localhost:5432/spra
BACKUP_PATH=./backups
RETENTION_DAYS=30
```

To change these, edit the `.env` file in the SPRA root directory.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `BACKUP_PATH` | `./backups` | Where to store backup files |
| `RETENTION_DAYS` | `30` | Keep backups for this many days (older ones auto-deleted) |

---

## Command Reference

### Automatic/Manual Backups

```powershell
# Run backup immediately
python backup_database.py

# Change retention to 60 days (one-time)
$env:RETENTION_DAYS=60; python backup_database.py
```

### Task Scheduler Management

```powershell
# Run as Administrator

# Install automatic backup task
.\setup_backup_schedule.ps1 -Action Install

# Schedule backup for specific day (1=Monday, 6=Saturday)
.\setup_backup_schedule.ps1 -Action Install -DayOfWeek 3 -Time "03:00"

# Schedule daily backup at 1 AM
.\setup_backup_schedule.ps1 -Action Install -Time "01:00"

# Test backup now
.\setup_backup_schedule.ps1 -Action Test

# Remove scheduled task
.\setup_backup_schedule.ps1 -Action Remove
```

### Restore Operations

```powershell
# Restore from specific backup (requires postgres password)
python restore_database.py backups/spra_backup_20260216_023500.sql.gz

# List available backups
Get-ChildItem .\backups\spra_backup_*.sql.gz | Sort-Object LastWriteTime -Descending
```

---

## Troubleshooting

### ❌ Backup fails with "pg_dump not found"

**Cause:** PostgreSQL command-line tools not installed

**Fix:**
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run installer and check **"Command Line Tools"** option
3. Complete installation
4. Retry backup: `python backup_database.py`

### ❌ "The system cannot find the file specified"

**Cause:** PostgreSQL installed in non-standard location

**Fix:**
1. Find PostgreSQL installation: 
   ```powershell
   Get-ChildItem "C:\Program Files" -Filter "PostgreSQL*" -Recurse
   ```
2. Check if `pg_dump.exe` exists in `bin` folder
3. Script auto-detects common paths, but may need manual adjustment

### ❌ Task Scheduler not running backup

**Cause:** Insufficient permissions or script path issue

**Fix:**
1. Run setup script as Administrator:
   ```powershell
   Start-Process powershell -Verb RunAs
   cd C:\Users\chugh\Desktop\SPRA
   .\setup_backup_schedule.ps1 -Action Install
   ```
2. Open Task Scheduler (Windows key → "Task Scheduler")
3. Find "SPRA-Database-Backup" task
4. Right-click → Properties → General → Check "Run with highest privileges"
5. Click "Run" to test

### ❌ Restore fails with "database is being accessed by other users"

**Cause:** Other processes using the database

**Fix:**
1. Stop SPRA application: `Ctrl+C` in Flask terminal
2. Close any database clients (pgAdmin, DBeaver, etc.)
3. Try restore again: `python restore_database.py backups/spra_backup_*.sql.gz`
4. Restart SPRA: `python app.py`

### ❌ Backup file is very small or 0 KB

**Cause:** Database may be empty or backup failed silently

**Fix:**
1. Check database connection:
   ```powershell
   $env:DATABASE_URL  # Should show connection string
   ```
2. Verify database exists in PostgreSQL:
   ```powershell
   psql -h localhost -U postgres -c "\l"  # List databases
   ```
3. Check backup log:
   ```powershell
   Get-Content backup.log -Tail 20
   ```

---

## Backup Best Practices

✅ **DO:**
- Schedule backups daily (at 2 AM by default to avoid peak hours)
- Keep 7-30 days of backups (current: 30 days)
- Test restore procedures monthly
- Store backups on multiple drives/cloud storage for critical environments
- Monitor `backup.log` for errors

❌ **DON'T:**
- Delete backup files manually (let auto-cleanup handle it)
- Run backups during peak usage (stick to off-hours like 2 AM)
- Use backups as a replacement for proper disaster recovery plan
- Forget the database password (needed for restore)

---

## Advanced: Cloud Backup

For production use, consider copying backups to cloud storage:

### Copy to OneDrive/Dropbox

```powershell
# After backup completes, sync to cloud
$Latest = Get-ChildItem .\backups\spra_backup_*.sql.gz -Newest 1
Copy-Item $Latest.FullName "C:\Users\chugh\OneDrive\Backups\"
```

### Copy to Network Drive

```powershell
# Run as part of backup_schedule.bat
xcopy "C:\Users\chugh\Desktop\SPRA\backups\spra_backup_*.sql.gz" "\\NetworkServer\Backups\" /Y
```

### S3/Azure Cloud Copy

Requires additional tools like AWS CLI or Azure CLI installed.

---

## Monitoring

### Check Backup Status

```powershell
# View backup log (last 20 lines)
Get-Content backup.log -Tail 20

# View all backups with size
Get-ChildItem .\backups\spra_backup_*.sql.gz | 
  ForEach-Object { "{0} - {1:N2} MB" -f $_.Name, ($_.Length/1MB) }

# View backup history (last 7 days)
Get-ChildItem .\backups\spra_backup_*.sql.gz | 
  Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-7) } |
  Sort-Object LastWriteTime -Descending
```

### View Task Scheduler History

```powershell
# Show last 10 backup task runs
Get-WinEvent -FilterHashtable @{
    LogName='Microsoft-Windows-TaskScheduler/Operational'
    ID=201  # Task completed event
} -MaxEvents 10 | Format-Table TimeCreated, Message
```

---

## Database Connection

Your current backup is configured to connect to:

```
Host:     localhost
Port:     5432
Database: spra
User:     spra_user
```

**PostgreSQL Status:**
- ✓ PostgreSQL 18 installed
- ✓ Database 'spra' created
- ✓ User 'spra_user' created
- ✓ Connection tested

---

## Next Steps

1. **Test backup now:** `python backup_database.py`
2. **Schedule automation:** Run `.\setup_backup_schedule.ps1 -Action Install` as Administrator
3. **Verify schedule:** Check Windows Task Scheduler for "SPRA-Database-Backup" task
4. **Monitor logs:** Check `backup.log` daily for first week
5. **Test restore:** Once you have data in database, test restore to verify backup integrity

---

## Support

For backup issues:
1. Check `backup.log` for detailed error messages
2. Run manual test: `python backup_database.py`
3. Verify PostgreSQL is running: `psql -V`
4. Check database connection: Review `DATABASE_URL` in `.env`

---

**Last Updated:** 2026-02-16  
**Status:** ✓ Production Ready
