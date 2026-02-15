"""
Database initialization - DEVELOPMENT ONLY
WARNING: Drops all tables and recreates with sample data. Do NOT use in production!
For production, use: python create_tables.py
"""
from app import app, db
from models import Component, HornType, HornTypeComponent, Order, OrderLineItem, ProductionConfig
from datetime import datetime, timedelta

def init_database():
    """Initialize database with sample data - DESTROYS existing data!"""
    import os
    if os.environ.get('FLASK_ENV') == 'production':
        print("ERROR: init_db.py must NOT be run in production (it drops all data).")
        print("Use: python create_tables.py")
        return
    with app.app_context():
        print("WARNING: Dropping all tables and creating fresh database with sample data...")
        db.drop_all()
        db.create_all()
        
        # Create production configuration
        print("Creating production configuration...")
        config = ProductionConfig(
            daily_production_capacity=4000,
            working_days_per_week=6,
            max_inventory_days=30,
            safety_stock_days=3
        )
        db.session.add(config)
        
        # Create sample components (generic parts - no quantity_per_horn here)
        print("Creating sample components...")
        sample_components = [
            # Electrical Components
            {'code': 'HORN-001', 'name': 'Horn Diaphragm', 'unit': 'pieces', 'cost': 15.50, 'lead_time': 10, 'supplier': 'ElectroSound Ltd'},
            {'code': 'HORN-002', 'name': 'Electromagnetic Coil', 'unit': 'pieces', 'cost': 12.00, 'lead_time': 7, 'supplier': 'MagneticParts Co'},
            {'code': 'HORN-003', 'name': 'Contact Points', 'unit': 'pieces', 'cost': 3.50, 'lead_time': 5, 'supplier': 'ElectroSound Ltd'},
            {'code': 'HORN-004', 'name': 'Armature', 'unit': 'pieces', 'cost': 8.75, 'lead_time': 8, 'supplier': 'MagneticParts Co'},
            {'code': 'HORN-005', 'name': 'Copper Wire (22 AWG)', 'unit': 'meters', 'cost': 1.20, 'lead_time': 3, 'supplier': 'WireTech Industries'},
            # Housing & Body
            {'code': 'HORN-006', 'name': 'Metal Housing (Steel)', 'unit': 'pieces', 'cost': 18.00, 'lead_time': 12, 'supplier': 'MetalWorks Inc'},
            {'code': 'HORN-007', 'name': 'Front Grille', 'unit': 'pieces', 'cost': 5.25, 'lead_time': 7, 'supplier': 'MetalWorks Inc'},
            {'code': 'HORN-008', 'name': 'Mounting Bracket', 'unit': 'pieces', 'cost': 4.50, 'lead_time': 6, 'supplier': 'AutoParts Direct'},
            {'code': 'HORN-009', 'name': 'Rubber Gasket', 'unit': 'pieces', 'cost': 1.80, 'lead_time': 4, 'supplier': 'RubberSeals Co'},
            {'code': 'HORN-010', 'name': 'Back Cover Plate', 'unit': 'pieces', 'cost': 3.25, 'lead_time': 7, 'supplier': 'MetalWorks Inc'},
            # Fasteners
            {'code': 'HORN-011', 'name': 'M6 Bolts', 'unit': 'pieces', 'cost': 0.15, 'lead_time': 2, 'supplier': 'FastenerWorld'},
            {'code': 'HORN-012', 'name': 'M6 Nuts', 'unit': 'pieces', 'cost': 0.10, 'lead_time': 2, 'supplier': 'FastenerWorld'},
            {'code': 'HORN-013', 'name': 'Washers', 'unit': 'pieces', 'cost': 0.08, 'lead_time': 2, 'supplier': 'FastenerWorld'},
            {'code': 'HORN-014', 'name': 'Self-tapping Screws', 'unit': 'pieces', 'cost': 0.12, 'lead_time': 2, 'supplier': 'FastenerWorld'},
            {'code': 'HORN-015', 'name': 'Spring Clips', 'unit': 'pieces', 'cost': 0.25, 'lead_time': 3, 'supplier': 'SpringTech'},
            # Electrical Connections
            {'code': 'HORN-016', 'name': 'Terminal Connectors', 'unit': 'pieces', 'cost': 0.85, 'lead_time': 4, 'supplier': 'ElectroSound Ltd'},
            {'code': 'HORN-017', 'name': 'Insulation Sleeve', 'unit': 'pieces', 'cost': 0.35, 'lead_time': 3, 'supplier': 'WireTech Industries'},
            {'code': 'HORN-018', 'name': 'Wire Harness', 'unit': 'pieces', 'cost': 2.50, 'lead_time': 5, 'supplier': 'WireTech Industries'},
            {'code': 'HORN-019', 'name': 'Fuse (10A)', 'unit': 'pieces', 'cost': 0.75, 'lead_time': 3, 'supplier': 'ElectroSound Ltd'},
            # Acoustic
            {'code': 'HORN-020', 'name': 'Resonator Disc', 'unit': 'pieces', 'cost': 6.50, 'lead_time': 8, 'supplier': 'AcousticParts Ltd'},
            {'code': 'HORN-021', 'name': 'Sound Amplifier Cone', 'unit': 'pieces', 'cost': 7.25, 'lead_time': 9, 'supplier': 'AcousticParts Ltd'},
            {'code': 'HORN-022', 'name': 'Vibration Dampener', 'unit': 'pieces', 'cost': 1.95, 'lead_time': 5, 'supplier': 'RubberSeals Co'},
            # Finishing
            {'code': 'HORN-023', 'name': 'Powder Coating (Black)', 'unit': 'kg', 'cost': 8.00, 'lead_time': 4, 'supplier': 'CoatingTech'},
            {'code': 'HORN-024', 'name': 'Anti-corrosion Primer', 'unit': 'liters', 'cost': 12.00, 'lead_time': 5, 'supplier': 'CoatingTech'},
            {'code': 'HORN-025', 'name': 'Weatherproof Sealant', 'unit': 'liters', 'cost': 15.00, 'lead_time': 4, 'supplier': 'ChemicalSupply Co'},
            # Quality & Packaging
            {'code': 'HORN-026', 'name': 'Quality Control Sticker', 'unit': 'pieces', 'cost': 0.05, 'lead_time': 2, 'supplier': 'PrintLabels Inc'},
            {'code': 'HORN-027', 'name': 'Product Label', 'unit': 'pieces', 'cost': 0.15, 'lead_time': 3, 'supplier': 'PrintLabels Inc'},
            {'code': 'HORN-028', 'name': 'Cardboard Box', 'unit': 'pieces', 'cost': 1.25, 'lead_time': 3, 'supplier': 'PackagingPro'},
            {'code': 'HORN-029', 'name': 'Bubble Wrap', 'unit': 'meters', 'cost': 0.80, 'lead_time': 2, 'supplier': 'PackagingPro'},
            {'code': 'HORN-030', 'name': 'Instruction Manual', 'unit': 'pieces', 'cost': 0.35, 'lead_time': 4, 'supplier': 'PrintLabels Inc'},
        ]
        
        components_by_code = {}
        for comp_data in sample_components:
            component = Component(
                code=comp_data['code'],
                name=comp_data['name'],
                description=f"Component for horn assembly - {comp_data['name']}",
                unit=comp_data['unit'],
                current_inventory=0,
                min_stock_level=5000,
                max_stock_level=50000,
                lead_time_days=comp_data['lead_time'],
                supplier_name=comp_data['supplier'],
                supplier_contact=f"contact@{comp_data['supplier'].lower().replace(' ', '')}.com",
                unit_cost=comp_data['cost'],
                minimum_order_quantity=1000
            )
            db.session.add(component)
            components_by_code[comp_data['code']] = component
        
        db.session.flush()
        
        # Standard Horn BOM (qty per horn for each component)
        standard_bom = [
            ('HORN-001', 1), ('HORN-002', 1), ('HORN-003', 2), ('HORN-004', 1), ('HORN-005', 2.5),
            ('HORN-006', 1), ('HORN-007', 1), ('HORN-008', 1), ('HORN-009', 1), ('HORN-010', 1),
            ('HORN-011', 4), ('HORN-012', 4), ('HORN-013', 4), ('HORN-014', 6), ('HORN-015', 2),
            ('HORN-016', 2), ('HORN-017', 2), ('HORN-018', 1), ('HORN-019', 1),
            ('HORN-020', 1), ('HORN-021', 1), ('HORN-022', 2),
            ('HORN-023', 0.05), ('HORN-024', 0.02), ('HORN-025', 0.01),
            ('HORN-026', 1), ('HORN-027', 1), ('HORN-028', 1), ('HORN-029', 0.5), ('HORN-030', 1),
        ]
        
        # Premium Horn BOM (some different quantities - better components)
        premium_bom = [
            ('HORN-001', 1), ('HORN-002', 1), ('HORN-003', 2), ('HORN-004', 1), ('HORN-005', 3),
            ('HORN-006', 1), ('HORN-007', 1), ('HORN-008', 1), ('HORN-009', 2), ('HORN-010', 1),
            ('HORN-011', 4), ('HORN-012', 4), ('HORN-013', 4), ('HORN-014', 8), ('HORN-015', 2),
            ('HORN-016', 2), ('HORN-017', 2), ('HORN-018', 1), ('HORN-019', 1),
            ('HORN-020', 1), ('HORN-021', 1), ('HORN-022', 3),
            ('HORN-023', 0.06), ('HORN-024', 0.025), ('HORN-025', 0.015),
            ('HORN-026', 1), ('HORN-027', 1), ('HORN-028', 1), ('HORN-029', 0.75), ('HORN-030', 1),
        ]
        
        # Compact Horn BOM (fewer/smaller components)
        compact_bom = [
            ('HORN-001', 1), ('HORN-002', 1), ('HORN-003', 2), ('HORN-004', 1), ('HORN-005', 2),
            ('HORN-006', 1), ('HORN-007', 1), ('HORN-008', 1), ('HORN-009', 1), ('HORN-010', 1),
            ('HORN-011', 3), ('HORN-012', 3), ('HORN-013', 3), ('HORN-014', 4), ('HORN-015', 2),
            ('HORN-016', 2), ('HORN-017', 2), ('HORN-018', 1), ('HORN-019', 1),
            ('HORN-020', 1), ('HORN-021', 1), ('HORN-022', 2),
            ('HORN-023', 0.04), ('HORN-024', 0.015), ('HORN-025', 0.01),
            ('HORN-026', 1), ('HORN-027', 1), ('HORN-028', 1), ('HORN-029', 0.4), ('HORN-030', 1),
        ]
        
        # Create horn types and assign components
        print("Creating horn types and BOMs...")
        
        standard_horn = HornType(code='STD-001', name='Standard Horn', description='Standard automotive horn - full feature set')
        db.session.add(standard_horn)
        db.session.flush()
        for code, qty in standard_bom:
            if code in components_by_code:
                ht_comp = HornTypeComponent(horn_type_id=standard_horn.id, component_id=components_by_code[code].id, quantity_per_horn=qty)
                db.session.add(ht_comp)
        
        premium_horn = HornType(code='PRM-001', name='Premium Horn', description='Premium horn with enhanced sound and durability')
        db.session.add(premium_horn)
        db.session.flush()
        for code, qty in premium_bom:
            if code in components_by_code:
                ht_comp = HornTypeComponent(horn_type_id=premium_horn.id, component_id=components_by_code[code].id, quantity_per_horn=qty)
                db.session.add(ht_comp)
        
        compact_horn = HornType(code='CMP-001', name='Compact Horn', description='Compact horn for limited space applications')
        db.session.add(compact_horn)
        db.session.flush()
        for code, qty in compact_bom:
            if code in components_by_code:
                ht_comp = HornTypeComponent(horn_type_id=compact_horn.id, component_id=components_by_code[code].id, quantity_per_horn=qty)
                db.session.add(ht_comp)
        
        # Create sample order with line items (mixed horn types)
        print("Creating sample order...")
        deadline = datetime.utcnow() + timedelta(days=60)
        order = Order(
            order_number='ORD-2026-001',
            customer_name='AutoMotive Industries Ltd',
            deadline=deadline,
            status='pending',
            notes='Large order: 150k Standard + 30k Premium + 20k Compact horns'
        )
        db.session.add(order)
        db.session.flush()
        
        db.session.add(OrderLineItem(order_id=order.id, horn_type_id=standard_horn.id, quantity=150000))
        db.session.add(OrderLineItem(order_id=order.id, horn_type_id=premium_horn.id, quantity=30000))
        db.session.add(OrderLineItem(order_id=order.id, horn_type_id=compact_horn.id, quantity=20000))
        
        db.session.commit()
        
        print("Database initialized successfully!")
        print(f"\nHorn types created: 3 (Standard, Premium, Compact)")
        print(f"Components created: {len(sample_components)}")
        print(f"\nSample order: {order.order_number}")
        print(f"  Customer: {order.customer_name}")
        print(f"  Total: 200,000 horns (150k Standard + 30k Premium + 20k Compact)")
        print(f"  Deadline: {order.deadline.strftime('%Y-%m-%d')}")
        print("\nYou can now run 'python app.py' to start the application")

if __name__ == '__main__':
    init_database()
