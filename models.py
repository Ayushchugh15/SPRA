from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ==================== AUTHENTICATION ====================

class User(UserMixin, db.Model):
    """User account for SPRA access"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20), default='operator')  # admin, operator, viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_operator(self):
        return self.role in ('admin', 'operator')
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class AuditLog(db.Model):
    """Tracks all user actions for compliance and debugging"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, etc.
    entity_type = db.Column(db.String(50))  # Component, Order, etc.
    entity_id = db.Column(db.Integer)
    changes = db.Column(db.Text)  # JSON of what changed
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref='audit_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'changes': self.changes,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


# ==================== MANUFACTURING ====================

class Component(db.Model):
    """Represents a component/part - generic parts used in horn assembly"""
    __tablename__ = 'components'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(50), default='pieces')  # pieces, kg, meters, etc.
    current_inventory = db.Column(db.Float, default=0)
    min_stock_level = db.Column(db.Float, default=0)  # Minimum inventory to maintain
    max_stock_level = db.Column(db.Float, default=0)  # Maximum storage capacity
    lead_time_days = db.Column(db.Integer, default=7)  # Days to receive after ordering
    supplier_name = db.Column(db.String(200))
    supplier_contact = db.Column(db.String(200))
    unit_cost = db.Column(db.Float, default=0)
    minimum_order_quantity = db.Column(db.Float, default=0)  # MOQ from supplier
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'unit': self.unit,
            'current_inventory': self.current_inventory,
            'min_stock_level': self.min_stock_level,
            'max_stock_level': self.max_stock_level,
            'lead_time_days': self.lead_time_days,
            'supplier_name': self.supplier_name,
            'supplier_contact': self.supplier_contact,
            'unit_cost': self.unit_cost,
            'minimum_order_quantity': self.minimum_order_quantity,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class HornType(db.Model):
    """Represents a specific type of horn product (e.g., Standard Horn, Premium Horn)"""
    __tablename__ = 'horn_types'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bom_components = db.relationship('HornTypeComponent', backref='horn_type', lazy=True, cascade='all, delete-orphan')
    order_line_items = db.relationship('OrderLineItem', backref='horn_type', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class HornTypeComponent(db.Model):
    """Links components to horn types with quantity per horn - BOM for each horn type"""
    __tablename__ = 'horn_type_components'
    
    id = db.Column(db.Integer, primary_key=True)
    horn_type_id = db.Column(db.Integer, db.ForeignKey('horn_types.id'), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    quantity_per_horn = db.Column(db.Float, nullable=False)  # How many units needed per horn of this type
    
    # Relationships
    component = db.relationship('Component', backref='horn_type_assignments', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'horn_type_id': self.horn_type_id,
            'component_id': self.component_id,
            'component_code': self.component.code if self.component else None,
            'component_name': self.component.name if self.component else None,
            'component_unit': self.component.unit if self.component else 'pieces',
            'quantity_per_horn': self.quantity_per_horn
        }


class Order(db.Model):
    """Represents a customer order - contains line items for different horn types"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(200), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    line_items = db.relationship('OrderLineItem', backref='order', lazy=True, cascade='all, delete-orphan')
    mrp_plans = db.relationship('MRPPlan', backref='order', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_quantity(self):
        """Total horns across all line items"""
        return sum(item.quantity for item in self.line_items)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_name': self.customer_name,
            'quantity': self.total_quantity,  # Computed for backward compatibility
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'status': self.status,
            'notes': self.notes,
            'line_items': [item.to_dict() for item in self.line_items],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class OrderLineItem(db.Model):
    """Order line item - specific horn type with quantity"""
    __tablename__ = 'order_line_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    horn_type_id = db.Column(db.Integer, db.ForeignKey('horn_types.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'horn_type_id': self.horn_type_id,
            'horn_type_code': self.horn_type.code if self.horn_type else None,
            'horn_type_name': self.horn_type.name if self.horn_type else None,
            'quantity': self.quantity
        }


class ProductionConfig(db.Model):
    """Configuration for production capacity and constraints"""
    __tablename__ = 'production_config'
    
    id = db.Column(db.Integer, primary_key=True)
    daily_production_capacity = db.Column(db.Integer, nullable=False)  # Horns per day
    working_days_per_week = db.Column(db.Integer, default=6)
    max_inventory_days = db.Column(db.Integer, default=30)  # Max days of inventory to hold
    safety_stock_days = db.Column(db.Integer, default=3)  # Buffer days for safety stock
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'daily_production_capacity': self.daily_production_capacity,
            'working_days_per_week': self.working_days_per_week,
            'max_inventory_days': self.max_inventory_days,
            'safety_stock_days': self.safety_stock_days,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MRPPlan(db.Model):
    """Material Requirement Planning results for an order"""
    __tablename__ = 'mrp_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    total_required = db.Column(db.Float, nullable=False)  # Total quantity needed
    current_inventory = db.Column(db.Float, nullable=False)  # Inventory at planning time
    net_requirement = db.Column(db.Float, nullable=False)  # What needs to be ordered
    order_quantity = db.Column(db.Float, nullable=False)  # Actual order quantity (adjusted for MOQ)
    order_date = db.Column(db.DateTime, nullable=False)  # When to place the order
    expected_delivery = db.Column(db.DateTime, nullable=False)  # When it should arrive
    estimated_cost = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default='planned')  # planned, ordered, received
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    component = db.relationship('Component', backref='mrp_plans', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'component_id': self.component_id,
            'component_code': self.component.code if self.component else None,
            'component_name': self.component.name if self.component else None,
            'total_required': self.total_required,
            'current_inventory': self.current_inventory,
            'net_requirement': self.net_requirement,
            'order_quantity': self.order_quantity,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'expected_delivery': self.expected_delivery.isoformat() if self.expected_delivery else None,
            'estimated_cost': self.estimated_cost,
            'status': self.status,
            'supplier_name': self.component.supplier_name if self.component else None,
            'lead_time_days': self.component.lead_time_days if self.component else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class InventoryTransaction(db.Model):
    """Track inventory movements"""
    __tablename__ = 'inventory_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # receipt, consumption, adjustment
    quantity = db.Column(db.Float, nullable=False)  # Positive for receipt, negative for consumption
    balance_after = db.Column(db.Float, nullable=False)
    reference = db.Column(db.String(200))  # Order number, PO number, etc.
    notes = db.Column(db.Text)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    component = db.relationship('Component', backref='transactions', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'component_id': self.component_id,
            'component_name': self.component.name if self.component else None,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'balance_after': self.balance_after,
            'reference': self.reference,
            'notes': self.notes,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None
        }
