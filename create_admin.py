#!/usr/bin/env python3
import os
from app import app, db
from models import User

os.environ['FLASK_ENV'] = 'production'

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print('Admin user already exists')
    else:
        admin = User(
            username='admin',
            email='admin@spra.local',
            full_name='System Administrator',
            role='admin'
        )
        admin.set_password('Admin@123')  # ⚠️ CHANGE THIS PASSWORD!
        db.session.add(admin)
        db.session.commit()
        print('Admin user created!')
        print('Username: admin')
        print('Password: Admin@123')
        print('⚠️  IMPORTANT: Change the admin password after first login!')