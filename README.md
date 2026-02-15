# Smart Production Resource Allocator (SPRA)

## Overview
An industry-ready Manufacturing Resource Planning (MRP) system designed for horn assembly manufacturing. This system optimizes production planning, inventory management, and component ordering to fulfill large-scale orders efficiently.

## Features

### 1. Order Management
- Track customer orders with quantities and deadlines
- Calculate production requirements
- Monitor order fulfillment progress

### 2. Bill of Materials (BOM)
- Define all 30+ components required for horn assembly
- Track component specifications and suppliers
- Manage component relationships

### 3. Production Planning
- Set daily production capacity
- Generate optimized production schedules
- Account for working days and production constraints

### 4. Inventory Management
- Track current inventory levels for all components
- Set minimum and maximum inventory thresholds
- Monitor inventory turnover and storage capacity

### 5. Material Requirement Planning (MRP)
- Calculate exact component requirements
- Determine optimal ordering quantities
- Schedule component deliveries based on production timeline
- Minimize inventory holding costs while preventing stockouts

### 6. Supplier Management
- Track multiple suppliers per component
- Manage lead times and minimum order quantities
- Compare pricing and delivery schedules

## Technology Stack

- **Backend**: Python 3.10+ with Flask
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla JS + Chart.js for visualizations)
- **API**: RESTful API architecture

## Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Initialize the database:
```bash
python init_db.py
```

6. Run the application:
```bash
python app.py
```

7. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage Guide

### 1. Setup Components (BOM)
- Navigate to "Components" section
- Add all 30 components with details:
  - Component name and code
  - Quantity required per horn
  - Current inventory
  - Minimum/maximum stock levels
  - Supplier information
  - Lead time (days to receive after ordering)

### 2. Create an Order
- Go to "Orders" section
- Enter order details:
  - Customer name
  - Quantity (e.g., 200,000 horns)
  - Deadline (e.g., 2 months)
- System calculates required production rate

### 3. Set Production Capacity
- Configure daily production capacity
- Set working days per week
- Define inventory storage constraints

### 4. Generate MRP Plan
- Click "Generate MRP Plan"
- System calculates:
  - Daily component consumption
  - When to order each component
  - How much to order
  - Expected inventory levels over time
- View detailed ordering schedule and timeline

### 5. Monitor Execution
- Track daily production
- Update inventory as components arrive
- Monitor order fulfillment progress

## Key Calculations

### Production Schedule
```
Daily Production Required = Total Order Quantity / Available Working Days
```

### Component Requirements
```
Total Component Needed = Order Quantity × Component Quantity per Horn
Net Requirement = Total Needed - Current Inventory
```

### Order Timing
```
Order Date = Production Start Date - Lead Time - Safety Buffer
Order Quantity = Net Requirement (adjusted for MOQ and packaging)
```

### Inventory Optimization
- Just-In-Time (JIT) ordering to minimize holding costs
- Safety stock to prevent production delays
- Considers storage capacity constraints

## Project Structure

```
SPRA/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── init_db.py            # Database initialization
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   └── js/
│       └── main.js       # Frontend logic
├── templates/
│   └── index.html        # Main UI
└── README.md             # This file
```

## Example Scenario

**Order**: 200,000 horns in 60 days

**Production Capacity**: 4,000 horns/day

**Working Days**: 50 days (excluding weekends/holidays)

**Components**: 30 different components per horn

**System Output**:
- Component ordering schedule for all 30 components
- Optimal order quantities considering lead times
- Daily inventory projections
- Alerts for potential bottlenecks

## Future Enhancements

- Multi-order management
- Real-time supplier integration
- Cost optimization algorithms
- Quality control tracking
- Predictive analytics for demand forecasting
- Mobile app for shop floor updates
- Integration with ERP systems

## Support

For issues or questions, please refer to the documentation or contact the development team.

## License

Proprietary - For internal company use only
