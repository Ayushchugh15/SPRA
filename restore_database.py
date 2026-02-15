#!/usr/bin/env python3
"""
SPRA Database Restore Script - Windows Compatible
Restores from a backup file with auto-detection of PostgreSQL tools
Usage: python restore_database.py backups/spra_backup_YYYYMMDD_HHMMSS.sql.gz
"""

import os
import sys
import subprocess
import gzip
from pathlib import Path
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://spra_user:spra_password_123@localhost:5432/spra')

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

def find_postgresql_tool(tool_name):
    """Find PostgreSQL tool (psql or pg_dump) auto-detection"""
    possible_paths = [
        fr'C:\Program Files\PostgreSQL\18\bin\{tool_name}.exe',
        fr'C:\Program Files\PostgreSQL\17\bin\{tool_name}.exe',
        fr'C:\Program Files\PostgreSQL\16\bin\{tool_name}.exe',
        fr'C:\Program Files\PostgreSQL\15\bin\{tool_name}.exe',
        fr'C:\Program Files (x86)\PostgreSQL\18\bin\{tool_name}.exe',
        fr'C:\Program Files (x86)\PostgreSQL\17\bin\{tool_name}.exe',
    ]
    
    # Check hardcoded paths
    for path in possible_paths:
        if Path(path).exists():
            return path
    
    # Try to find via PATH environment variable
    try:
        result = subprocess.run(['where', f'{tool_name}.exe'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return None

def restore_backup(backup_file):
    """Restore database from backup file"""
    try:
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            print(f"✗ Error: Backup file not found: {backup_file}")
            sys.exit(1)
        
        # Parse connection details
        db_config = parse_db_url(DATABASE_URL)
        
        # Find PostgreSQL tools
        psql_path = find_postgresql_tool('psql')
        if not psql_path:
            print("✗ Error: psql not found. PostgreSQL tools not installed?")
            sys.exit(1)
        
        print(f"\n{'='*60}")
        print(f"SPRA Database Restore")
        print(f"{'='*60}")
        print(f"Backup file: {backup_path.name}")
        print(f"File size: {backup_path.stat().st_size / 1024:.1f} KB")
        print(f"Database: {db_config['database']} ({db_config['host']})")
        print(f"PostgreSQL tools: {psql_path}")
        print(f"{'='*60}\n")
        
        # Confirm restore
        response = input("⚠️  This will OVERWRITE the current database. Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Restore cancelled.")
            return False
        
        # Decompress if needed
        if backup_file.endswith('.gz'):
            print("Decompressing backup...")
            with gzip.open(backup_file, 'rb') as f_in:
                sql_file = backup_file.replace('.sql.gz', '.sql')
                with open(sql_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            restore_file = sql_file
            print(f"  Decompressed to: {sql_file}")
        else:
            restore_file = backup_file
        
        # Set password environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['password']
        
        # Get 'postgres' user password for database operations
        postgres_pass = input("\nEnter PostgreSQL 'postgres' superuser password: ")
        
        # Drop and recreate database
        print("\n1. Dropping existing database...")
        drop_cmd = [
            psql_path,
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', 'postgres',
            '-c', f"DROP DATABASE IF EXISTS {db_config['database']};"
        ]
        env['PGPASSWORD'] = postgres_pass
        result = subprocess.run(drop_cmd, capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            print(f"  Warning: {result.stderr}")
        else:
            print("  Database dropped")
        
        print("2. Creating new database...")
        create_cmd = [
            psql_path,
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', 'postgres',
            '-c', f"CREATE DATABASE {db_config['database']};"
        ]
        result = subprocess.run(create_cmd, capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            print(f"  ✗ Error creating database: {result.stderr}")
            return False
        print("  Database created")
        
        # Restore from backup
        print("3. Restoring from backup (this may take a minute)...")
        env['PGPASSWORD'] = db_config['password']
        
        try:
            with open(restore_file, 'r') as f:
                restore_cmd = [
                    psql_path,
                    '-h', db_config['host'],
                    '-p', db_config['port'],
                    '-U', db_config['username'],
                    '-d', db_config['database']
                ]
                result = subprocess.run(restore_cmd, stdin=f, capture_output=True, text=True, env=env, timeout=300)
            
            if result.returncode != 0:
                print(f"  ✗ Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"  ✗ Restore timeout (exceeded 5 minutes)")
            return False
        
        # Cleanup temporary SQL file
        if backup_file.endswith('.gz'):
            Path(restore_file).unlink()
        
        print("  Restore completed")
        
        print("\n✓ Restore successful!")
        print(f"  Database: {db_config['database']}")
        print(f"  Restored at: {datetime.now().isoformat()}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Restore failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python restore_database.py <backup_file>")
        print("Example: python restore_database.py backups/spra_backup_20260216_020000.sql.gz")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    success = restore_backup(backup_file)
    sys.exit(0 if success else 1)

def restore_backup(backup_file):
    """Restore database from backup file"""
    try:
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            print(f"Error: Backup file not found: {backup_file}")
            sys.exit(1)
        
        # Parse connection details
        db_config = parse_db_url(DATABASE_URL)
        
        print(f"\n{'='*60}")
        print(f"SPRA Database Restore")
        print(f"{'='*60}")
        print(f"Backup file: {backup_path.name}")
        print(f"File size: {backup_path.stat().st_size / 1024:.1f} KB")
        print(f"Database: {db_config['database']} ({db_config['host']})")
        print(f"{'='*60}\n")
        
        # Confirm restore
        response = input("⚠️  This will OVERWRITE the current database. Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Restore cancelled.")
            return False
        
        # Decompress if needed
        if backup_file.endswith('.gz'):
            print("Decompressing backup...")
            with gzip.open(backup_file, 'rb') as f_in:
                sql_file = backup_file.replace('.sql.gz', '.sql')
                with open(sql_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            restore_file = sql_file
            print(f"Decompressed to: {sql_file}")
        else:
            restore_file = backup_file
        
        # Set password environment variable
        os.environ['PGPASSWORD'] = db_config['password']
        
        # Full paths to PostgreSQL tools (Windows PostgreSQL 18)
        psql_path = r'C:\Program Files\PostgreSQL\18\bin\psql.exe'
        pg_dump_path = r'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe'
        
        # Drop and recreate database
        print("\n1. Dropping existing database...")
        drop_cmd = [
            psql_path,
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', 'postgres',
            '-c', f"DROP DATABASE IF EXISTS {db_config['database']};"
        ]
        subprocess.run(drop_cmd, capture_output=True)
        
        print("2. Creating new database...")
        create_cmd = [
            psql_path,
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', 'postgres',
            '-c', f"CREATE DATABASE {db_config['database']};"
        ]
        subprocess.run(create_cmd, capture_output=True)
        
        # Restore from backup
        print("3. Restoring from backup (this may take a minute)...")
        with open(restore_file, 'r') as f:
            restore_cmd = [
                psql_path,
                '-h', db_config['host'],
                '-p', db_config['port'],
                '-U', db_config['username'],
                '-d', db_config['database']
            ]
            result = subprocess.run(restore_cmd, stdin=f, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        
        # Cleanup temporary SQL file
        if backup_file.endswith('.gz'):
            Path(restore_file).unlink()
        
        print("\n✓ Restore completed successfully!")
        print(f"Database: {db_config['database']}")
        print(f"Restored at: {datetime.now().isoformat()}")
        
        # Verify
        print("\nVerifying restore...")
        verify_cmd = [
            psql_path,
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['username'],
            '-d', db_config['database'],
            '-c', "SELECT COUNT(*) as total_records FROM (SELECT COUNT(*) FROM components UNION ALL SELECT COUNT(*) FROM orders UNION ALL SELECT COUNT(*) FROM users) t;"
        ]
        result = subprocess.run(verify_cmd, capture_output=True, text=True)
        print(result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Restore failed: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python restore_database.py <backup_file>")
        print("Example: python restore_database.py backups/spra_backup_20260216_020000.sql.gz")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    success = restore_backup(backup_file)
    sys.exit(0 if success else 1)
