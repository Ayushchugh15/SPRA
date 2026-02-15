@echo off
REM SPRA Backup Script for Windows Task Scheduler
REM Place this in: C:\Users\chugh\Desktop\SPRA\backup_schedule.bat
REM Then schedule it in Task Scheduler to run daily at 2 AM

setlocal enabledelayedexpansion

REM Set environment variables
set FLASK_ENV=production
set PYTHON_PATH=C:\Users\chugh\Desktop\SPRA\venv\Scripts\python.exe
set BACKUP_SCRIPT=C:\Users\chugh\Desktop\SPRA\backup_database.py
set LOG_FILE=C:\Users\chugh\Desktop\SPRA\backups\backup.log

REM Create backups directory if not exists
if not exist C:\Users\chugh\Desktop\SPRA\backups mkdir C:\Users\chugh\Desktop\SPRA\backups

REM Run backup with logging
echo. >> %LOG_FILE%
echo ========================================== >> %LOG_FILE%
echo Backup started at %date% %time% >> %LOG_FILE%
echo ========================================== >> %LOG_FILE%

%PYTHON_PATH% %BACKUP_SCRIPT% >> %LOG_FILE% 2>&1

if %errorlevel% equ 0 (
    echo Backup completed successfully at %time% >> %LOG_FILE%
    echo Status: SUCCESS >> %LOG_FILE%
) else (
    echo Backup FAILED at %time% with error code %errorlevel% >> %LOG_FILE%
    echo Status: FAILED >> %LOG_FILE%
)

echo. >> %LOG_FILE%
endlocal
