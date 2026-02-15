"""
SPRA - Smart Production Resource Allocator
Production-ready Flask Application with Authentication
"""
import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from models import (
    db, User, AuditLog, Component, HornType, HornTypeComponent,
    Order, OrderLineItem, ProductionConfig, MRPPlan, InventoryTransaction
)
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
import math

# Import config
try:
    from config import DEBUG, SECRET_KEY, DATABASE_URI, ENV
except ImportError:
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = ENV != 'production'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///data/spra.db')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = DEBUG

# ==================== SESSION CONFIGURATION ====================
# Session timeout: 30 minutes of inactivity (use 12 hours if "remember me" is checked)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Reset timeout on each request
app.config['SESSION_COOKIE_SECURE'] = (ENV == 'production')  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# CORS - restrict in production
if ENV == 'production':
    CORS(app, origins=os.environ.get('CORS_ORIGINS', '*').split(','), supports_credentials=True)
else:
    CORS(app)

db.init_app(app)

# ==================== AUTHENTICATION SETUP ====================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.before_request
def before_request():
    """Refresh session timeout on each request"""
    from flask import session
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)


@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    # Prevent XSS attacks
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy - prevent inline scripts
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src fonts.gstatic.com"
    
    # HTTPS only (in production)
    if ENV == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response


# ==================== AUDIT LOGGING ====================

def add_audit_log(action, entity_type=None, entity_id=None, changes=None):
    """Log user actions for audit trail"""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=json.dumps(changes) if changes else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        app.logger.error(f'Audit logging error: {e}')


# ==================== ROLE-BASED ACCESS CONTROL ====================

def admin_required(f):
    """Decorator: Require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            add_audit_log('UNAUTHORIZED_ACCESS', f.__name__)
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return login_required(decorated_function)


def operator_required(f):
    """Decorator: Require operator or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_operator():
            add_audit_log('UNAUTHORIZED_ACCESS', f.__name__)
            return jsonify({'error': 'Operator access required'}), 403
        return f(*args, **kwargs)
    return login_required(decorated_function)


# ==================== AUTHENTICATION ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username or not password:
            add_audit_log('LOGIN_FAILED', changes={'reason': 'Missing credentials'})
            return jsonify({'error': 'Username and password required'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            add_audit_log('LOGIN_FAILED', changes={'username': username})
            return jsonify({'error': 'Invalid username or password'}), 401
        
        if not user.is_active:
            add_audit_log('LOGIN_FAILED', changes={'username': username, 'reason': 'Account disabled'})
            return jsonify({'error': 'Account is disabled'}), 403
        
        # Login successful
        remember = data.get('remember', False)
        login_user(user, remember=remember)
        
        # Set session lifetime based on "remember me"
        from flask import session
        if remember:
            app.permanent_session_lifetime = timedelta(days=7)  # 7 days
        else:
            app.permanent_session_lifetime = timedelta(minutes=30)  # 30 minutes
        session.permanent = True
        
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        add_audit_log('LOGIN_SUCCESS', changes={'username': username, 'remember': remember})
        
        if request.is_json:
            return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200
        return redirect(url_for('index'))
    
    return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """User logout"""
    add_audit_log('LOGOUT', changes={'username': current_user.username})
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register new user (admin only in production)"""
    if ENV == 'production' and (not current_user.is_authenticated or not current_user.is_admin()):
        return jsonify({'error': 'Registration disabled. Contact administrator.'}), 403
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        # Validate input
        if not username or len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters'}), 400
        
        if not email or '@' not in email:
            return jsonify({'error': 'Valid email required'}), 400
        
        if not password or len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=data.get('role', 'operator')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        add_audit_log('USER_CREATED', 'User', user.id, {'username': username, 'email': email})
        
        return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201
    
    return render_template('register.html')


@app.route('/api/user', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged in user info"""
    return jsonify(current_user.to_dict())


# ==================== DASHBOARD ====================

@app.route('/')
@app.route('/dashboard')
@login_required
def index():
    """Main dashboard"""
    return render_template('index.html')


# ==================== COMPONENT ROUTES ====================


@app.route('/api/components', methods=['GET'])
@operator_required
def get_components():
    """Get all components"""
    components = Component.query.all()
    add_audit_log('VIEW_COMPONENTS', 'Component', changes={'count': len(components)})
    return jsonify([c.to_dict() for c in components])


@app.route('/api/components', methods=['POST'])
@operator_required
def create_component():
    """Create a new component"""
    data = request.json
    
    # Validate required fields
    if not data.get('code') or not data.get('name'):
        return jsonify({'error': 'Code and name are required'}), 400
    
    if Component.query.filter_by(code=data['code']).first():
        return jsonify({'error': 'Component code already exists'}), 400
    
    component = Component(
        code=data['code'].strip(),
        name=data['name'].strip(),
        description=data.get('description', '').strip(),
        unit=data.get('unit', 'pieces').strip(),
        current_inventory=float(data.get('current_inventory', 0)),
        min_stock_level=float(data.get('min_stock_level', 0)),
        max_stock_level=float(data.get('max_stock_level', 0)),
        lead_time_days=int(data.get('lead_time_days', 7)),
        supplier_name=data.get('supplier_name', '').strip(),
        supplier_contact=data.get('supplier_contact', '').strip(),
        unit_cost=float(data.get('unit_cost', 0)),
        minimum_order_quantity=float(data.get('minimum_order_quantity', 0))
    )
    
    db.session.add(component)
    db.session.commit()
    
    add_audit_log('CREATE_COMPONENT', 'Component', component.id, {'code': component.code, 'name': component.name})
    
    return jsonify(component.to_dict()), 201


@app.route('/api/components/<int:component_id>', methods=['PUT'])
@operator_required
def update_component(component_id):
    """Update a component"""
    component = Component.query.get_or_404(component_id)
    data = request.json
    
    changes = {}
    for key, value in data.items():
        if hasattr(component, key) and key not in ['id', 'created_at', 'updated_at']:
            old_value = getattr(component, key)
            # Strip strings
            if isinstance(value, str):
                value = value.strip()
            setattr(component, key, value)
            changes[key] = {'old': old_value, 'new': value}
    
    component.updated_at = datetime.utcnow()
    db.session.commit()
    
    add_audit_log('UPDATE_COMPONENT', 'Component', component.id, changes)
    
    return jsonify(component.to_dict())


@app.route('/api/components/<int:component_id>', methods=['DELETE'])
@admin_required
def delete_component(component_id):
    """Delete a component (admin only)"""
    component = Component.query.get_or_404(component_id)
    code = component.code
    db.session.delete(component)
    db.session.commit()
    
    add_audit_log('DELETE_COMPONENT', 'Component', component_id, {'code': code})
    
    return jsonify({'message': 'Component deleted successfully'})


# ==================== HORN TYPE ROUTES ====================

@app.route('/api/horn-types', methods=['GET'])
def get_horn_types():
    """Get all horn types with their BOM components"""
    horn_types = HornType.query.all()
    result = []
    for ht in horn_types:
        ht_dict = ht.to_dict()
        ht_dict['bom_components'] = [b.to_dict() for b in ht.bom_components]
        result.append(ht_dict)
    return jsonify(result)


@app.route('/api/horn-types', methods=['POST'])
def create_horn_type():
    """Create a new horn type"""
    data = request.json
    
    if HornType.query.filter_by(code=data['code']).first():
        return jsonify({'error': 'Horn type code already exists'}), 400
    
    horn_type = HornType(
        code=data['code'],
        name=data['name'],
        description=data.get('description', '')
    )
    
    db.session.add(horn_type)
    db.session.commit()
    
    return jsonify(horn_type.to_dict()), 201


@app.route('/api/horn-types/<int:horn_type_id>', methods=['PUT'])
def update_horn_type(horn_type_id):
    """Update a horn type"""
    horn_type = HornType.query.get_or_404(horn_type_id)
    data = request.json
    
    for key, value in data.items():
        if hasattr(horn_type, key) and key not in ['id', 'created_at', 'updated_at', 'bom_components']:
            setattr(horn_type, key, value)
    
    horn_type.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(horn_type.to_dict())


@app.route('/api/horn-types/<int:horn_type_id>', methods=['DELETE'])
def delete_horn_type(horn_type_id):
    """Delete a horn type"""
    horn_type = HornType.query.get_or_404(horn_type_id)
    db.session.delete(horn_type)
    db.session.commit()
    
    return jsonify({'message': 'Horn type deleted successfully'})


@app.route('/api/horn-types/<int:horn_type_id>/components', methods=['GET'])
def get_horn_type_components(horn_type_id):
    """Get BOM components for a horn type"""
    horn_type = HornType.query.get_or_404(horn_type_id)
    return jsonify([b.to_dict() for b in horn_type.bom_components])


@app.route('/api/horn-types/<int:horn_type_id>/components', methods=['POST'])
def add_component_to_horn_type(horn_type_id):
    """Add a component to horn type BOM"""
    horn_type = HornType.query.get_or_404(horn_type_id)
    data = request.json
    
    existing = HornTypeComponent.query.filter_by(
        horn_type_id=horn_type_id,
        component_id=data['component_id']
    ).first()
    
    if existing:
        return jsonify({'error': 'Component already in this horn type BOM'}), 400
    
    bom_item = HornTypeComponent(
        horn_type_id=horn_type_id,
        component_id=data['component_id'],
        quantity_per_horn=float(data['quantity_per_horn'])
    )
    
    db.session.add(bom_item)
    db.session.commit()
    
    return jsonify(bom_item.to_dict()), 201


@app.route('/api/horn-types/<int:horn_type_id>/components/<int:component_id>', methods=['PUT'])
def update_horn_type_component(horn_type_id, component_id):
    """Update quantity_per_horn for a component in horn type BOM"""
    bom_item = HornTypeComponent.query.filter_by(
        horn_type_id=horn_type_id,
        component_id=component_id
    ).first_or_404()
    
    data = request.json
    bom_item.quantity_per_horn = float(data.get('quantity_per_horn', bom_item.quantity_per_horn))
    db.session.commit()
    
    return jsonify(bom_item.to_dict())


@app.route('/api/horn-types/<int:horn_type_id>/components/<int:component_id>', methods=['DELETE'])
def remove_component_from_horn_type(horn_type_id, component_id):
    """Remove a component from horn type BOM"""
    bom_item = HornTypeComponent.query.filter_by(
        horn_type_id=horn_type_id,
        component_id=component_id
    ).first_or_404()
    
    db.session.delete(bom_item)
    db.session.commit()
    
    return jsonify({'message': 'Component removed from horn type'})


# ==================== ORDER ROUTES ====================

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders with line items"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order with line items"""
    data = request.json
    
    order_number = data.get('order_number')
    if not order_number:
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
    
    order = Order(
        order_number=order_number,
        customer_name=data['customer_name'],
        deadline=deadline,
        status=data.get('status', 'pending'),
        notes=data.get('notes', '')
    )
    
    db.session.add(order)
    db.session.flush()
    
    line_items = data.get('line_items', [])
    if not line_items:
        return jsonify({'error': 'At least one horn type with quantity is required'}), 400
    
    for item in line_items:
        line_item = OrderLineItem(
            order_id=order.id,
            horn_type_id=int(item['horn_type_id']),
            quantity=int(item['quantity'])
        )
        db.session.add(line_item)
    
    db.session.commit()
    
    return jsonify(order.to_dict()), 201


@app.route('/api/orders/<int:order_id>', methods=['PUT'])
@operator_required
def update_order(order_id):
    """Update an order"""
    order = Order.query.get_or_404(order_id)
    data = request.json
    
    changes = {}
    for key in ['order_number', 'customer_name', 'deadline', 'status', 'notes']:
        if key in data:
            old_value = getattr(order, key)
            value = data[key]
            if key == 'deadline' and isinstance(value, str):
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            setattr(order, key, value)
            if old_value != value:
                changes[key] = {'old': str(old_value), 'new': str(value)}
    
    if 'line_items' in data:
        OrderLineItem.query.filter_by(order_id=order_id).delete()
        for item in data['line_items']:
            line_item = OrderLineItem(
                order_id=order_id,
                horn_type_id=int(item['horn_type_id']),
                quantity=int(item['quantity'])
            )
            db.session.add(line_item)
        changes['line_items'] = 'Updated'
    
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    add_audit_log('UPDATE_ORDER', 'Order', order_id, changes)
    
    return jsonify(order.to_dict())


@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
@admin_required
def delete_order(order_id):
    """Delete an order (admin only)"""
    order = Order.query.get_or_404(order_id)
    order_number = order.order_number
    db.session.delete(order)
    db.session.commit()
    
    add_audit_log('DELETE_ORDER', 'Order', order_id, {'order_number': order_number})
    
    return jsonify({'message': 'Order deleted successfully'})


# ==================== PRODUCTION CONFIG ROUTES ====================

@app.route('/api/production-config', methods=['GET'])
def get_production_config():
    """Get production configuration"""
    config = ProductionConfig.query.first()
    if not config:
        config = ProductionConfig(
            daily_production_capacity=4000,
            working_days_per_week=6,
            max_inventory_days=30,
            safety_stock_days=3
        )
        db.session.add(config)
        db.session.commit()
    
    return jsonify(config.to_dict())


@app.route('/api/production-config', methods=['PUT'])
def update_production_config():
    """Update production configuration"""
    config = ProductionConfig.query.first()
    if not config:
        config = ProductionConfig()
        db.session.add(config)
    
    data = request.json
    for key, value in data.items():
        if hasattr(config, key) and key not in ['id', 'updated_at']:
            setattr(config, key, value)
    
    config.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(config.to_dict())


# ==================== MRP ROUTES ====================

@app.route('/api/mrp/generate/<int:order_id>', methods=['POST'])
@operator_required
def generate_mrp(order_id):
    """Generate MRP plan for an order"""
    order = Order.query.get_or_404(order_id)
    config = ProductionConfig.query.first()
    
    if not config:
        return jsonify({'error': 'Production configuration not set'}), 400
    
    component_requirements = defaultdict(float)
    
    for line_item in order.line_items:
        horn_type = line_item.horn_type
        if not horn_type:
            continue
        for bom_item in horn_type.bom_components:
            component_requirements[bom_item.component_id] += (
                line_item.quantity * bom_item.quantity_per_horn
            )
    
    if not component_requirements:
        return jsonify({'error': 'Order has no horn types with components. Add components to horn types first.'}), 400
    
    component_ids = list(component_requirements.keys())
    components = Component.query.filter(Component.id.in_(component_ids)).all()
    
    MRPPlan.query.filter_by(order_id=order_id).delete()
    
    order_date = order.order_date or datetime.utcnow()
    deadline = order.deadline
    total_quantity = order.total_quantity
    
    working_days = calculate_working_days(order_date, deadline, config.working_days_per_week)
    
    if working_days <= 0:
        return jsonify({'error': 'Invalid deadline - not enough working days'}), 400
    
    daily_production = math.ceil(total_quantity / working_days)
    
    if daily_production > config.daily_production_capacity:
        return jsonify({
            'warning': f'Required daily production ({daily_production}) exceeds capacity ({config.daily_production_capacity})',
            'required_days': math.ceil(total_quantity / config.daily_production_capacity),
            'available_days': working_days
        }), 400
    
    production_start = order_date + timedelta(days=config.safety_stock_days)
    mrp_plans = []
    
    for component in components:
        total_required = component_requirements[component.id]
        net_requirement = max(0, total_required - component.current_inventory)
        
        if net_requirement > 0:
            if component.minimum_order_quantity > 0:
                order_quantity = math.ceil(net_requirement / component.minimum_order_quantity) * component.minimum_order_quantity
            else:
                order_quantity = net_requirement
        else:
            order_quantity = 0
        
        if component.max_stock_level > 0:
            max_order = component.max_stock_level - component.current_inventory
            if order_quantity > max_order:
                order_quantity = max_order
        
        days_before_production = component.lead_time_days + config.safety_stock_days
        order_date_calculated = production_start - timedelta(days=days_before_production)
        
        if order_date_calculated < datetime.utcnow():
            order_date_calculated = datetime.utcnow()
        
        expected_delivery = order_date_calculated + timedelta(days=component.lead_time_days)
        estimated_cost = order_quantity * component.unit_cost
        
        mrp_plan = MRPPlan(
            order_id=order_id,
            component_id=component.id,
            total_required=total_required,
            current_inventory=component.current_inventory,
            net_requirement=net_requirement,
            order_quantity=order_quantity,
            order_date=order_date_calculated,
            expected_delivery=expected_delivery,
            estimated_cost=estimated_cost,
            status='planned'
        )
        
        db.session.add(mrp_plan)
        mrp_plans.append(mrp_plan)
    
    db.session.commit()
    
    total_cost = sum(plan.estimated_cost for plan in mrp_plans)
    components_to_order = sum(1 for plan in mrp_plans if plan.order_quantity > 0)
    
    return jsonify({
        'message': 'MRP plan generated successfully',
        'summary': {
            'order_quantity': total_quantity,
            'working_days': working_days,
            'daily_production': daily_production,
            'production_start': production_start.isoformat(),
            'total_components': len(components),
            'components_to_order': components_to_order,
            'total_estimated_cost': total_cost
        },
        'plans': [plan.to_dict() for plan in mrp_plans]
    })
    
    add_audit_log('GENERATE_MRP', 'MRPPlan', None, {'order_id': order_id, 'total_cost': total_cost})
    
    return jsonify(response)


@app.route('/api/mrp/order/<int:order_id>', methods=['GET'])
@operator_required
def get_mrp_plans(order_id):
    """Get MRP plans for an order"""
    plans = MRPPlan.query.filter_by(order_id=order_id).all()
    return jsonify([plan.to_dict() for plan in plans])


@app.route('/api/mrp/<int:plan_id>/status', methods=['PUT'])
def update_mrp_status(plan_id):
    """Update MRP plan status"""
    plan = MRPPlan.query.get_or_404(plan_id)
    data = request.json
    
    plan.status = data.get('status', plan.status)
    
    if plan.status == 'received':
        component = Component.query.get(plan.component_id)
        if component:
            component.current_inventory += plan.order_quantity
            transaction = InventoryTransaction(
                component_id=component.id,
                transaction_type='receipt',
                quantity=plan.order_quantity,
                balance_after=component.current_inventory,
                reference=f"MRP-{plan.id}",
                notes=f"Received order for Order #{plan.order_id}"
            )
            db.session.add(transaction)
    
    db.session.commit()
    
    return jsonify(plan.to_dict())


# ==================== INVENTORY ROUTES ====================

@app.route('/api/inventory/transactions', methods=['GET'])
def get_inventory_transactions():
    """Get inventory transactions"""
    component_id = request.args.get('component_id', type=int)
    limit = request.args.get('limit', 100, type=int)
    
    query = InventoryTransaction.query
    if component_id:
        query = query.filter_by(component_id=component_id)
    
    transactions = query.order_by(InventoryTransaction.transaction_date.desc()).limit(limit).all()
    return jsonify([t.to_dict() for t in transactions])


@app.route('/api/inventory/adjust', methods=['POST'])
def adjust_inventory():
    """Manually adjust inventory"""
    data = request.json
    component = Component.query.get_or_404(data['component_id'])
    
    adjustment = float(data['quantity'])
    component.current_inventory += adjustment
    
    transaction = InventoryTransaction(
        component_id=component.id,
        transaction_type='adjustment',
        quantity=adjustment,
        balance_after=component.current_inventory,
        reference=data.get('reference', ''),
        notes=data.get('notes', '')
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'component': component.to_dict(),
        'transaction': transaction.to_dict()
    })


# ==================== ANALYTICS ROUTES ====================

@app.route('/api/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """Get dashboard analytics"""
    total_components = Component.query.count()
    total_horn_types = HornType.query.count()
    total_orders = Order.query.count()
    active_orders = Order.query.filter(Order.status.in_(['pending', 'in_progress'])).count()
    
    low_stock_components = Component.query.filter(
        Component.current_inventory < Component.min_stock_level
    ).count()
    
    components = Component.query.all()
    total_inventory_value = sum(c.current_inventory * c.unit_cost for c in components)
    
    return jsonify({
        'total_components': total_components,
        'total_horn_types': total_horn_types,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'low_stock_components': low_stock_components,
        'total_inventory_value': total_inventory_value
    })


# ==================== HELPER FUNCTIONS ====================

def calculate_working_days(start_date, end_date, working_days_per_week):
    """Calculate number of working days between two dates"""
    total_days = (end_date - start_date).days
    weeks = total_days // 7
    remaining_days = total_days % 7
    working_days = weeks * working_days_per_week
    working_days += min(remaining_days, working_days_per_week)
    return working_days


# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(
        debug=DEBUG,
        host=os.environ.get('HOST', '0.0.0.0'),
        port=int(os.environ.get('PORT', 5000))
    )
