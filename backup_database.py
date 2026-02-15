#!/usr/bin/env python3
"""
SPRA Database Backup Script - Windows Compatible
Automatically backs up PostgreSQL database with auto-detection
"""

import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://spra_user:spra_password_123@localhost:5432/spra')
BACKUP_DIR = os.environ.get('BACKUP_PATH', './backups')
RETENTION_DAYS = int(os.environ.get('RETENTION_DAYS', 30))

def parse_db_url(url):
    """Parse PostgreSQL connection string"""
    try:
        url = url.replace('postgresql://', '')
        credentials, host_db = url.split('@')
        username, password = credentials.split(':')
        
        if ':' in host_db:
            host, rest = host_db.split(':')
            port, db = rest.split('/')
        else:
            host, db = host_db.split('/')
            port = '5432'
        
        return {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'database': db
        }
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}")
        sys.exit(1)

def find_pg_dump():
    """Find pg_dump executable in common PostgreSQL locations"""
    possible_paths = [
        r'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe',
        r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe',
        r'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe',
        r'C:\Program Files\PostgreSQL\15\bin\pg_dump.exe',
        r'C:\Program Files (x86)\PostgreSQL\18\bin\pg_dump.exe',
        r'C:\Program Files (x86)\PostgreSQL\17\bin\pg_dump.exe',
    ]
    
    # Check hardcoded paths
    for path in possible_paths:
        if Path(path).exists():
            print(f"✓ Found pg_dump at: {path}")
            return path
    
    # Try to find via PATH environment variable
    try:
        result = subprocess.run(['where', 'pg_dump.exe'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            found_path = result.stdout.strip().split('\n')[0]
            print(f"✓ Found pg_dump in PATH: {found_path}")
            return found_path
    except:
        pass
    
    print("✗ pg_dump not found!")
    print("  Please ensure PostgreSQL is installed with command-line tools")
    return None

def test_connection(db_config):
    """Test database connection"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['username'],
            password=db_config['password'],
            database=db_config['database']
        )
        conn.close()
        print(f"✓ Database connection successful")
        return True
    except ImportError:
        print("⚠ psycopg2 not installed (optional check)")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def create_backup():
    """Create database backup"""
    try:
        # Create backup directory
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(exist_ok=True)
        print(f"✓ Backup directory ready: {backup_path.absolute()}")
        
        # Parse connection details
        db_config = parse_db_url(DATABASE_URL)
        print(f"  Database: {db_config['database']} @ {db_config['host']}:{db_config['port']}")
        
        # Test connection first
        if not test_connection(db_config):
            print("Cannot proceed - database unreachable")
            return False
        
        # Find pg_dump
        pg_dump_path = find_pg_dump()
        if not pg_dump_path:
            print("\nERROR: PostgreSQL tools not found!")
            print("\nPlease install PostgreSQL from: https://www.postgresql.org/download/windows/")
            print("Make sure to select 'Command Line Tools' during installation")
            return False
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_path / f"spra_backup_{timestamp}.sql"
        
        print(f"\nCreating backup: {backup_file.name}")
        
        # Set environment variable for password
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['password']
        
        # Build and execute pg_dump command
        cmd = [
            pg_dump_path,
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['username'],
            '-d', db_config['database'],
            '-F', 'plain',
            '-f', str(backup_file)
        ]
        
        print(f"  Running: {pg_dump_path} (with password hidden)")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                env=env, 
                timeout=300
            )
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                print(f"\n✗ pg_dump failed with code {result.returncode}")
                print(f"  Error: {error_msg}")
                return False
            
            # Verify file was created
            if not backup_file.exists():
                print(f"\n✗ Backup file was not created!")
                if result.stderr:
                    print(f"  stderr: {result.stderr}")
                return False
            
            print(f"  SQL file created ({backup_file.stat().st_size / 1024:.1f} KB)")
            
        except subprocess.TimeoutExpired:
            print(f"\n✗ Backup timeout (exceeded 5 minutes)")
            return False
        except Exception as e:
            print(f"\n✗ Backup execution error: {e}")
            return False
        
        # Compress backup file
        print(f"  Compressing...")
        try:
            with open(backup_file, 'rb') as f_in:
                with gzip.open(f'{backup_file}.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            backup_file.unlink()
            compressed_file = backup_file.with_suffix('.sql.gz')
            file_size = compressed_file.stat().st_size / (1024 * 1024)
            
            print(f"\n✓ Backup successful!")
            print(f"  File: {compressed_file.name}")
            print(f"  Size: {file_size:.2f} MB")
            
        except Exception as e:
            print(f"\n✗ Compression failed: {e}")
            return False
        
        # Clean old backups
        cleanup_old_backups(backup_path)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_old_backups(backup_path):
    """Remove backups older than retention period"""
    try:
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
        
        deleted = 0
        for backup_file in backup_path.glob('spra_backup_*.sql.gz'):
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                backup_file.unlink()
                print(f"  Deleted old backup: {backup_file.name}")
                deleted += 1
        
        if deleted > 0:
            print(f"\nCleaned up {deleted} old backup(s)")
    except Exception as e:
        print(f"Warning: Cleanup error: {e}")

if __name__ == '__main__':
    print(f"SPRA Database Backup - {datetime.now().isoformat()}")
    print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")
    print(f"Backup directory: {BACKUP_DIR}")
    print(f"Retention period: {RETENTION_DAYS} days")
    print("-" * 60)
    
    success = create_backup()
    sys.exit(0 if success else 1)
