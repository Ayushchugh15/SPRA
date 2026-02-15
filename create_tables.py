"""
Production-safe: Create database tables only.
Does NOT drop tables or add sample data. Safe to run on existing databases.
"""
import os

# Set production mode for table creation
os.environ.setdefault('FLASK_ENV', 'production')

from app import app, db

def create_tables():
    """Create all tables if they don't exist. Safe for production."""
    with app.app_context():
        print("Creating database tables (if not exist)...")
        db.create_all()
        print("Tables ready.")
        # Ensure ProductionConfig has default if empty
        from models import ProductionConfig
        if ProductionConfig.query.first() is None:
            config = ProductionConfig(
                daily_production_capacity=4000,
                working_days_per_week=6,
                max_inventory_days=30,
                safety_stock_days=3
            )
            db.session.add(config)
            db.session.commit()
            print("Default production config created.")

if __name__ == '__main__':
    create_tables()
