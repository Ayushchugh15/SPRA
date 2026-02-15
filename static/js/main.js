// API Base URL
const API_BASE = '/api';

// State
let currentOrders = [];
let currentHornTypes = [];
let currentComponents = [];
let currentMRPPlans = [];
let selectedOrderId = null;
let selectedHornTypeId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    loadDashboardStats();
    loadOrders();
    loadHornTypes();
    loadComponents();
    loadProductionConfig();
    
    document.getElementById('createOrderForm').addEventListener('submit', handleCreateOrder);
    document.getElementById('createComponentForm').addEventListener('submit', handleCreateComponent);
    document.getElementById('createHornTypeForm').addEventListener('submit', handleCreateHornType);
    document.getElementById('configForm').addEventListener('submit', handleUpdateConfig);
    
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('orderDeadline').setAttribute('min', today);
});

// ==================== TAB MANAGEMENT ====================

function initializeTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// ==================== DASHBOARD ====================

async function loadDashboardStats() {
    try {
        const response = await fetch(`${API_BASE}/analytics/dashboard`);
        const data = await response.json();
        document.getElementById('totalComponents').textContent = data.total_components;
        document.getElementById('totalHornTypes').textContent = data.total_horn_types || 0;
        document.getElementById('totalOrders').textContent = data.total_orders;
        document.getElementById('activeOrders').textContent = data.active_orders;
        document.getElementById('lowStockComponents').textContent = data.low_stock_components;
        document.getElementById('inventoryValue').textContent = `$${formatNumber(data.total_inventory_value)}`;
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// ==================== ORDERS ====================

async function loadOrders() {
    try {
        const response = await fetch(`${API_BASE}/orders`);
        currentOrders = await response.json();
        renderOrdersTable();
        updateMRPOrderSelect();
    } catch (error) {
        console.error('Error loading orders:', error);
        showError('Failed to load orders');
    }
}

function renderOrdersTable() {
    const tbody = document.getElementById('ordersTableBody');
    if (currentOrders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No orders found. Create your first order!</td></tr>';
        return;
    }
    
    tbody.innerHTML = currentOrders.map(order => {
        const lineItemsStr = (order.line_items || []).map(li => 
            `${li.horn_type_name}: ${formatNumber(li.quantity)}`
        ).join(', ') || '-';
        return `
            <tr>
                <td><strong>${order.order_number}</strong></td>
                <td>${order.customer_name}</td>
                <td><small>${lineItemsStr}</small></td>
                <td>${formatNumber(order.quantity)} horns</td>
                <td>${formatDate(order.deadline)}</td>
                <td><span class="status-badge status-${order.status}">${order.status.replace('_', ' ')}</span></td>
                <td>
                    <button class="btn btn-primary btn-small" onclick="viewOrderDetails(${order.id})">View</button>
                    <button class="btn btn-warning btn-small" onclick="editOrder(${order.id})">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="deleteOrder(${order.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

async function showOrderForm() {
    document.getElementById('orderFormTitle').textContent = 'Create New Order';
    document.getElementById('orderSubmitBtn').textContent = 'Create Order';
    document.getElementById('orderEditId').value = '';
    await loadHornTypes();  // Refresh horn types for dropdown
    resetOrderLineItems();
    document.getElementById('orderForm').style.display = 'block';
}

function hideOrderForm() {
    document.getElementById('orderForm').style.display = 'none';
    document.getElementById('createOrderForm').reset();
    document.getElementById('orderEditId').value = '';
}

function resetOrderLineItems() {
    const container = document.getElementById('orderLineItemsContainer');
    container.innerHTML = `
        <div class="line-item-row">
            <select class="line-item-horn-type" required>
                <option value="">-- Select Horn Type --</option>
            </select>
            <input type="number" class="line-item-quantity" placeholder="Qty" min="1" required>
            <button type="button" class="btn btn-secondary btn-small" onclick="removeOrderLineItem(this)" title="Remove">−</button>
        </div>
    `;
    populateOrderHornTypeDropdowns();
}

function populateOrderHornTypeDropdowns() {
    const options = currentHornTypes.map(ht => 
        `<option value="${ht.id}">${ht.code} - ${ht.name}</option>`
    ).join('');
    document.querySelectorAll('.line-item-horn-type').forEach(sel => {
        const currentVal = sel.value;
        sel.innerHTML = '<option value="">-- Select Horn Type --</option>' + options;
        if (currentVal) sel.value = currentVal;
    });
}

function addOrderLineItem() {
    const container = document.getElementById('orderLineItemsContainer');
    const div = document.createElement('div');
    div.className = 'line-item-row';
    div.innerHTML = `
        <select class="line-item-horn-type" required>
            <option value="">-- Select Horn Type --</option>
            ${currentHornTypes.map(ht => `<option value="${ht.id}">${ht.code} - ${ht.name}</option>`).join('')}
        </select>
        <input type="number" class="line-item-quantity" placeholder="Qty" min="1" required>
        <button type="button" class="btn btn-secondary btn-small" onclick="removeOrderLineItem(this)" title="Remove">−</button>
    `;
    container.appendChild(div);
}

function removeOrderLineItem(btn) {
    const container = document.getElementById('orderLineItemsContainer');
    if (container.children.length > 1) {
        btn.closest('.line-item-row').remove();
    } else {
        showError('At least one line item is required');
    }
}

function getOrderLineItemsData() {
    const rows = document.querySelectorAll('#orderLineItemsContainer .line-item-row');
    const items = [];
    rows.forEach(row => {
        const hornTypeId = row.querySelector('.line-item-horn-type').value;
        const qty = parseInt(row.querySelector('.line-item-quantity').value);
        if (hornTypeId && qty > 0) items.push({ horn_type_id: hornTypeId, quantity: qty });
    });
    return items;
}

async function handleCreateOrder(e) {
    e.preventDefault();
    const editId = document.getElementById('orderEditId').value;
    const isEdit = editId !== '';
    const lineItems = getOrderLineItemsData();
    
    if (lineItems.length === 0) {
        showError('Add at least one horn type with quantity');
        return;
    }
    
    const orderData = {
        order_number: document.getElementById('orderNumber').value,
        customer_name: document.getElementById('customerName').value,
        deadline: new Date(document.getElementById('orderDeadline').value).toISOString(),
        status: document.getElementById('orderStatus').value,
        notes: document.getElementById('orderNotes').value,
        line_items: lineItems
    };
    
    try {
        const url = isEdit ? `${API_BASE}/orders/${editId}` : `${API_BASE}/orders`;
        const method = isEdit ? 'PUT' : 'POST';
        const response = await fetch(url, {
            method, headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderData)
        });
        
        if (response.ok) {
            showSuccess(isEdit ? 'Order updated successfully!' : 'Order created successfully!');
            hideOrderForm();
            loadOrders();
            loadDashboardStats();
        } else {
            const err = await response.json();
            showError(err.error || `Failed to ${isEdit ? 'update' : 'create'} order`);
        }
    } catch (error) {
        showError(`Failed to ${isEdit ? 'update' : 'create'} order`);
    }
}

async function editOrder(orderId) {
    await loadHornTypes();  // Ensure horn types are loaded
    const order = currentOrders.find(o => o.id === orderId);
    if (!order) return;
    
    document.getElementById('orderEditId').value = order.id;
    document.getElementById('orderNumber').value = order.order_number;
    document.getElementById('customerName').value = order.customer_name;
    document.getElementById('orderDeadline').value = order.deadline.split('T')[0];
    document.getElementById('orderStatus').value = order.status;
    document.getElementById('orderNotes').value = order.notes || '';
    
    resetOrderLineItems();
    const container = document.getElementById('orderLineItemsContainer');
    const lineItems = order.line_items || [];
    container.innerHTML = '';
    lineItems.forEach((li, idx) => {
        const div = document.createElement('div');
        div.className = 'line-item-row';
        div.innerHTML = `
            <select class="line-item-horn-type" required>
                <option value="">-- Select Horn Type --</option>
                ${currentHornTypes.map(ht => 
                    `<option value="${ht.id}" ${ht.id == li.horn_type_id ? 'selected' : ''}>${ht.code} - ${ht.name}</option>`
                ).join('')}
            </select>
            <input type="number" class="line-item-quantity" placeholder="Qty" min="1" value="${li.quantity}" required>
            <button type="button" class="btn btn-secondary btn-small" onclick="removeOrderLineItem(this)" title="Remove">−</button>
        `;
        container.appendChild(div);
    });
    if (lineItems.length === 0) addOrderLineItem();
    
    document.getElementById('orderFormTitle').textContent = 'Edit Order';
    document.getElementById('orderSubmitBtn').textContent = 'Update Order';
    document.getElementById('orderForm').style.display = 'block';
    document.getElementById('orderForm').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function deleteOrder(orderId) {
    if (!confirm('Are you sure you want to delete this order?')) return;
    try {
        const res = await fetch(`${API_BASE}/orders/${orderId}`, { method: 'DELETE' });
        if (res.ok) { showSuccess('Order deleted!'); loadOrders(); loadDashboardStats(); }
        else showError('Failed to delete order');
    } catch (e) { showError('Failed to delete order'); }
}

function viewOrderDetails(orderId) {
    const order = currentOrders.find(o => o.id === orderId);
    if (!order) return;
    const lineItemsStr = (order.line_items || []).map(li => 
        `<li>${li.horn_type_name}: ${formatNumber(li.quantity)} horns</li>`
    ).join('');
    document.getElementById('modalBody').innerHTML = `
        <h2>Order Details</h2>
        <div class="form-container">
            <p><strong>Order Number:</strong> ${order.order_number}</p>
            <p><strong>Customer:</strong> ${order.customer_name}</p>
            <p><strong>Total Quantity:</strong> ${formatNumber(order.quantity)} horns</p>
            <p><strong>Line Items:</strong><ul>${lineItemsStr}</ul></p>
            <p><strong>Deadline:</strong> ${formatDate(order.deadline)}</p>
            <p><strong>Status:</strong> <span class="status-badge status-${order.status}">${order.status.replace('_', ' ')}</span></p>
            <p><strong>Notes:</strong> ${order.notes || 'N/A'}</p>
        </div>
        <button class="btn btn-primary" onclick="closeModal(); switchTab('mrp'); document.getElementById('mrpOrderSelect').value='${order.id}'; loadMRPPlan();">View MRP Plan</button>
    `;
    document.getElementById('modal').style.display = 'block';
}

// ==================== HORN TYPES ====================

async function loadHornTypes() {
    try {
        const response = await fetch(`${API_BASE}/horn-types`);
        currentHornTypes = await response.json();
        renderHornTypes();
    } catch (error) {
        console.error('Error loading horn types:', error);
        document.getElementById('hornTypesList').innerHTML = '<div class="loading">Failed to load horn types</div>';
    }
}

function renderHornTypes() {
    const container = document.getElementById('hornTypesList');
    if (currentHornTypes.length === 0) {
        container.innerHTML = '<div class="loading">No horn types. Add your first horn type!</div>';
        return;
    }
    
    container.innerHTML = currentHornTypes.map(ht => `
        <div class="horn-type-card">
            <h4>${ht.code} - ${ht.name}</h4>
            <p><small>${ht.description || ''}</small></p>
            <p><strong>Components in BOM:</strong> ${(ht.bom_components || []).length}</p>
            <div class="horn-type-card-actions">
                <button class="btn btn-primary btn-small" onclick="showHornTypeBOM(${ht.id})">Manage BOM</button>
                <button class="btn btn-warning btn-small" onclick="editHornType(${ht.id})">Edit</button>
                <button class="btn btn-danger btn-small" onclick="deleteHornType(${ht.id})">Delete</button>
            </div>
        </div>
    `).join('');
}

function showHornTypeForm() {
    document.getElementById('hornTypeFormTitle').textContent = 'Add New Horn Type';
    document.getElementById('hornTypeSubmitBtn').textContent = 'Add Horn Type';
    document.getElementById('hornTypeEditId').value = '';
    document.getElementById('hornTypeForm').style.display = 'block';
}

function hideHornTypeForm() {
    document.getElementById('hornTypeForm').style.display = 'none';
    document.getElementById('createHornTypeForm').reset();
}

async function handleCreateHornType(e) {
    e.preventDefault();
    const editId = document.getElementById('hornTypeEditId').value;
    const isEdit = editId !== '';
    const data = {
        code: document.getElementById('hornTypeCode').value,
        name: document.getElementById('hornTypeName').value,
        description: document.getElementById('hornTypeDescription').value
    };
    
    try {
        const url = isEdit ? `${API_BASE}/horn-types/${editId}` : `${API_BASE}/horn-types`;
        const method = isEdit ? 'PUT' : 'POST';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        if (res.ok) {
            showSuccess(isEdit ? 'Horn type updated!' : 'Horn type added!');
            hideHornTypeForm();
            loadHornTypes();
            loadDashboardStats();
        } else {
            const err = await res.json();
            showError(err.error || 'Failed');
        }
    } catch (e) { showError('Failed'); }
}

function editHornType(id) {
    const ht = currentHornTypes.find(h => h.id === id);
    if (!ht) return;
    document.getElementById('hornTypeEditId').value = ht.id;
    document.getElementById('hornTypeCode').value = ht.code;
    document.getElementById('hornTypeName').value = ht.name;
    document.getElementById('hornTypeDescription').value = ht.description || '';
    document.getElementById('hornTypeFormTitle').textContent = 'Edit Horn Type';
    document.getElementById('hornTypeSubmitBtn').textContent = 'Update Horn Type';
    document.getElementById('hornTypeForm').style.display = 'block';
}

async function deleteHornType(id) {
    if (!confirm('Delete this horn type? Orders using it may be affected.')) return;
    try {
        const res = await fetch(`${API_BASE}/horn-types/${id}`, { method: 'DELETE' });
        if (res.ok) { showSuccess('Deleted!'); loadHornTypes(); loadDashboardStats(); }
        else showError('Failed');
    } catch (e) { showError('Failed'); }
}

async function showHornTypeBOM(hornTypeId) {
    selectedHornTypeId = hornTypeId;
    await loadComponents();  // Ensure components are loaded
    await loadHornTypes();   // Refresh horn type data
    const ht = currentHornTypes.find(h => h.id == hornTypeId);
    document.getElementById('bomHornTypeName').textContent = ht ? `${ht.code} - ${ht.name}` : '';
    document.getElementById('hornTypeBOMSection').style.display = 'block';
    populateBOMComponentSelect();
    renderHornTypeBOMTable();
}

function populateBOMComponentSelect() {
    const select = document.getElementById('bomComponentSelect');
    if (!currentComponents || currentComponents.length === 0) {
        select.innerHTML = '<option value="">-- No components. Add components in Components tab first --</option>';
        return;
    }
    const existingIds = (currentHornTypes.find(h => h.id == selectedHornTypeId)?.bom_components || [])
        .map(b => Number(b.component_id));
    // Show components not in BOM; if all are already in BOM, show all (API will reject duplicates)
    const available = currentComponents.filter(c => !existingIds.includes(Number(c.id)));
    const options = available.length > 0 ? available : currentComponents;
    select.innerHTML = '<option value="">-- Select Component --</option>' +
        options.map(c => `<option value="${c.id}">${c.code} - ${c.name} (${c.unit})</option>`).join('');
}

function renderHornTypeBOMTable() {
    const ht = currentHornTypes.find(h => h.id == selectedHornTypeId);
    const tbody = document.getElementById('hornTypeBOMTableBody');
    if (!ht || !ht.bom_components || ht.bom_components.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4">No components in BOM. Add components above.</td></tr>';
        return;
    }
    tbody.innerHTML = ht.bom_components.map(b => `
        <tr>
            <td>${b.component_code} - ${b.component_name}</td>
            <td>${b.quantity_per_horn}</td>
            <td>${b.component_unit}</td>
            <td>
                <button class="btn btn-danger btn-small" onclick="removeComponentFromHornType(${b.component_id})">Remove</button>
            </td>
        </tr>
    `).join('');
}

async function addComponentToHornType() {
    const componentId = document.getElementById('bomComponentSelect').value;
    const qty = parseFloat(document.getElementById('bomQuantityPerHorn').value);
    if (!componentId || !qty || qty <= 0) {
        showError('Select a component and enter quantity');
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/horn-types/${selectedHornTypeId}/components`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ component_id: componentId, quantity_per_horn: qty })
        });
        if (res.ok) {
            showSuccess('Component added to BOM!');
            loadHornTypes();
            populateBOMComponentSelect();
            renderHornTypeBOMTable();
        } else {
            const err = await res.json();
            showError(err.error || 'Failed');
        }
    } catch (e) { showError('Failed'); }
}

async function removeComponentFromHornType(componentId) {
    if (!selectedHornTypeId) {
        showError('Please open Manage BOM again and try removing.');
        return;
    }
    if (!confirm('Remove this component from BOM?')) return;
    try {
        const res = await fetch(`${API_BASE}/horn-types/${selectedHornTypeId}/components/${componentId}`, { method: 'DELETE' });
        if (res.ok) {
            showSuccess('Removed!');
            await loadHornTypes();  // Await so we have fresh data before re-rendering
            populateBOMComponentSelect();
            renderHornTypeBOMTable();
        } else {
            const err = await res.json().catch(() => ({}));
            showError(err.error || 'Failed to remove');
        }
    } catch (e) {
        showError('Failed to remove: ' + (e.message || 'Network error'));
    }
}

// ==================== COMPONENTS ====================

async function loadComponents() {
    try {
        const response = await fetch(`${API_BASE}/components`);
        currentComponents = await response.json();
        renderComponentsTable();
    } catch (error) {
        console.error('Error loading components:', error);
        showError('Failed to load components');
    }
}

function renderComponentsTable() {
    const tbody = document.getElementById('componentsTableBody');
    if (currentComponents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No components found.</td></tr>';
        return;
    }
    tbody.innerHTML = currentComponents.map(comp => {
        const isLowStock = comp.current_inventory < comp.min_stock_level;
        const stockClass = isLowStock ? 'style="color: var(--danger-color); font-weight: bold;"' : '';
        return `
            <tr>
                <td><strong>${comp.code}</strong></td>
                <td>${comp.name}</td>
                <td>${comp.unit}</td>
                <td ${stockClass}>${formatNumber(comp.current_inventory)}</td>
                <td>${formatNumber(comp.min_stock_level)}</td>
                <td>${comp.supplier_name || 'N/A'}</td>
                <td>${comp.lead_time_days} days</td>
                <td>
                    <button class="btn btn-primary btn-small" onclick="viewComponentDetails(${comp.id})">View</button>
                    <button class="btn btn-warning btn-small" onclick="editComponent(${comp.id})">Edit</button>
                    <button class="btn btn-danger btn-small" onclick="deleteComponent(${comp.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

function showComponentForm() {
    document.getElementById('componentFormTitle').textContent = 'Add New Component';
    document.getElementById('componentSubmitBtn').textContent = 'Add Component';
    document.getElementById('componentEditId').value = '';
    document.getElementById('componentCode').removeAttribute('readonly');
    document.getElementById('componentForm').style.display = 'block';
}

function hideComponentForm() {
    document.getElementById('componentForm').style.display = 'none';
    document.getElementById('createComponentForm').reset();
    document.getElementById('componentEditId').value = '';
    document.getElementById('componentCode').removeAttribute('readonly');
}

async function handleCreateComponent(e) {
    e.preventDefault();
    const editId = document.getElementById('componentEditId').value;
    const isEdit = editId !== '';
    const componentData = {
        code: document.getElementById('componentCode').value,
        name: document.getElementById('componentName').value,
        description: document.getElementById('componentDescription').value,
        unit: document.getElementById('componentUnit').value,
        current_inventory: parseFloat(document.getElementById('componentInventory').value),
        min_stock_level: parseFloat(document.getElementById('componentMinStock').value),
        max_stock_level: parseFloat(document.getElementById('componentMaxStock').value),
        lead_time_days: parseInt(document.getElementById('componentLeadTime').value),
        supplier_name: document.getElementById('componentSupplier').value,
        supplier_contact: document.getElementById('componentSupplierContact').value,
        unit_cost: parseFloat(document.getElementById('componentUnitCost').value),
        minimum_order_quantity: parseFloat(document.getElementById('componentMOQ').value)
    };
    
    try {
        const url = isEdit ? `${API_BASE}/components/${editId}` : `${API_BASE}/components`;
        const res = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(componentData)
        });
        if (res.ok) {
            showSuccess(isEdit ? 'Component updated!' : 'Component added!');
            hideComponentForm();
            loadComponents();
            loadDashboardStats();
        } else {
            const err = await res.json();
            showError(err.error || 'Failed');
        }
    } catch (e) { showError('Failed'); }
}

function editComponent(componentId) {
    const comp = currentComponents.find(c => c.id === componentId);
    if (!comp) return;
    document.getElementById('componentEditId').value = comp.id;
    document.getElementById('componentCode').value = comp.code;
    document.getElementById('componentName').value = comp.name;
    document.getElementById('componentDescription').value = comp.description || '';
    document.getElementById('componentUnit').value = comp.unit;
    document.getElementById('componentInventory').value = comp.current_inventory;
    document.getElementById('componentMinStock').value = comp.min_stock_level;
    document.getElementById('componentMaxStock').value = comp.max_stock_level;
    document.getElementById('componentLeadTime').value = comp.lead_time_days;
    document.getElementById('componentSupplier').value = comp.supplier_name || '';
    document.getElementById('componentSupplierContact').value = comp.supplier_contact || '';
    document.getElementById('componentUnitCost').value = comp.unit_cost;
    document.getElementById('componentMOQ').value = comp.minimum_order_quantity;
    document.getElementById('componentCode').setAttribute('readonly', 'readonly');
    document.getElementById('componentFormTitle').textContent = 'Edit Component';
    document.getElementById('componentSubmitBtn').textContent = 'Update Component';
    document.getElementById('componentForm').style.display = 'block';
}

async function deleteComponent(componentId) {
    if (!confirm('Delete this component?')) return;
    try {
        const res = await fetch(`${API_BASE}/components/${componentId}`, { method: 'DELETE' });
        if (res.ok) { showSuccess('Deleted!'); loadComponents(); loadDashboardStats(); }
        else showError('Failed');
    } catch (e) { showError('Failed'); }
}

function viewComponentDetails(componentId) {
    const comp = currentComponents.find(c => c.id === componentId);
    if (!comp) return;
    const isLowStock = comp.current_inventory < comp.min_stock_level;
    const stockWarning = isLowStock ? '<div class="alert alert-warning">⚠️ Low stock!</div>' : '';
    document.getElementById('modalBody').innerHTML = `
        <h2>Component Details</h2>${stockWarning}
        <div class="form-container">
            <p><strong>Code:</strong> ${comp.code}</p>
            <p><strong>Name:</strong> ${comp.name}</p>
            <p><strong>Unit:</strong> ${comp.unit}</p>
            <p><strong>Unit Cost:</strong> $${comp.unit_cost}</p>
            <p><strong>Lead Time:</strong> ${comp.lead_time_days} days</p>
            <p><strong>Current Inventory:</strong> ${formatNumber(comp.current_inventory)}</p>
            <p><strong>Supplier:</strong> ${comp.supplier_name || 'N/A'}</p>
        </div>
    `;
    document.getElementById('modal').style.display = 'block';
}

// ==================== PRODUCTION CONFIG ====================

async function loadProductionConfig() {
    try {
        const res = await fetch(`${API_BASE}/production-config`);
        const config = await res.json();
        document.getElementById('configDailyCapacity').value = config.daily_production_capacity;
        document.getElementById('configWorkingDays').value = config.working_days_per_week;
        document.getElementById('configMaxInventoryDays').value = config.max_inventory_days;
        document.getElementById('configSafetyStockDays').value = config.safety_stock_days;
    } catch (e) {}
}

async function handleUpdateConfig(e) {
    e.preventDefault();
    try {
        const res = await fetch(`${API_BASE}/production-config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                daily_production_capacity: parseInt(document.getElementById('configDailyCapacity').value),
                working_days_per_week: parseInt(document.getElementById('configWorkingDays').value),
                max_inventory_days: parseInt(document.getElementById('configMaxInventoryDays').value),
                safety_stock_days: parseInt(document.getElementById('configSafetyStockDays').value)
            })
        });
        if (res.ok) showSuccess('Config updated!');
        else showError('Failed');
    } catch (e) { showError('Failed'); }
}

// ==================== MRP ====================

function updateMRPOrderSelect() {
    const select = document.getElementById('mrpOrderSelect');
    select.innerHTML = '<option value="">-- Select an order --</option>' +
        currentOrders.map(o => `<option value="${o.id}">${o.order_number} - ${o.customer_name} (${formatNumber(o.quantity)} horns)</option>`).join('');
}

function loadMRPPlan() {
    selectedOrderId = document.getElementById('mrpOrderSelect').value;
    const generateBtn = document.getElementById('generateMRPBtn');
    const exportBtn = document.getElementById('exportMRPBtn');
    if (selectedOrderId) {
        generateBtn.disabled = false;
        fetchMRPPlan(selectedOrderId);
    } else {
        generateBtn.disabled = true;
        exportBtn.disabled = true;
        document.getElementById('mrpSummary').style.display = 'none';
        document.getElementById('mrpTableBody').innerHTML = '<tr><td colspan="10" class="loading">Select an order and generate MRP plan</td></tr>';
    }
}

async function fetchMRPPlan(orderId) {
    try {
        const res = await fetch(`${API_BASE}/mrp/order/${orderId}`);
        currentMRPPlans = await res.json();
        if (currentMRPPlans.length > 0) {
            renderMRPTable();
            document.getElementById('exportMRPBtn').disabled = false;
        } else {
            document.getElementById('mrpTableBody').innerHTML = '<tr><td colspan="10" class="loading">No MRP plan yet. Click Generate MRP Plan.</td></tr>';
            document.getElementById('mrpSummary').style.display = 'none';
            document.getElementById('exportMRPBtn').disabled = true;
        }
    } catch (e) {}
}

async function generateMRPPlan() {
    if (!selectedOrderId) return;
    const btn = document.getElementById('generateMRPBtn');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    try {
        const res = await fetch(`${API_BASE}/mrp/generate/${selectedOrderId}`, { method: 'POST' });
        const result = await res.json();
        if (res.ok) {
            showSuccess('MRP plan generated!');
            displayMRPSummary(result.summary);
            currentMRPPlans = result.plans;
            renderMRPTable();
            document.getElementById('exportMRPBtn').disabled = false;
        } else {
            showError(result.error || result.warning || 'Failed');
        }
    } catch (e) { showError('Failed'); }
    btn.disabled = false;
    btn.textContent = 'Generate MRP Plan';
}

function displayMRPSummary(summary) {
    document.getElementById('summaryQuantity').textContent = `${formatNumber(summary.order_quantity)} horns`;
    document.getElementById('summaryWorkingDays').textContent = `${summary.working_days} days`;
    document.getElementById('summaryDailyProd').textContent = `${formatNumber(summary.daily_production)} horns/day`;
    document.getElementById('summaryProdStart').textContent = formatDate(summary.production_start);
    document.getElementById('summaryComponentsToOrder').textContent = `${summary.components_to_order} of ${summary.total_components}`;
    document.getElementById('summaryTotalCost').textContent = `$${formatNumber(summary.total_estimated_cost)}`;
    document.getElementById('mrpSummary').style.display = 'block';
}

function renderMRPTable() {
    const tbody = document.getElementById('mrpTableBody');
    if (currentMRPPlans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10">No plans</td></tr>';
        return;
    }
    const sorted = [...currentMRPPlans].sort((a,b) => new Date(a.order_date) - new Date(b.order_date));
    tbody.innerHTML = sorted.map(plan => `
        <tr>
            <td><strong>${plan.component_code}</strong><br><small>${plan.component_name}</small></td>
            <td>${formatNumber(plan.total_required)}</td>
            <td>${formatNumber(plan.current_inventory)}</td>
            <td>${formatNumber(plan.net_requirement)}</td>
            <td><strong>${formatNumber(plan.order_quantity)}</strong></td>
            <td>${formatDate(plan.order_date)}</td>
            <td>${formatDate(plan.expected_delivery)}</td>
            <td>${plan.supplier_name || 'N/A'}<br><small>${plan.lead_time_days} days</small></td>
            <td>$${formatNumber(plan.estimated_cost)}</td>
            <td><span class="status-badge status-${plan.status}">${plan.status}</span></td>
        </tr>
    `).join('');
}

function exportMRPPlan() {
    if (currentMRPPlans.length === 0) { showError('No plan to export'); return; }
    const headers = ['Component Code','Component Name','Total Required','Current Inventory','Net Requirement','Order Quantity','Order Date','Expected Delivery','Supplier','Lead Time','Estimated Cost','Status'];
    const rows = currentMRPPlans.map(p => [p.component_code,p.component_name,p.total_required,p.current_inventory,p.net_requirement,p.order_quantity,p.order_date,p.expected_delivery,p.supplier_name||'',p.lead_time_days,p.estimated_cost,p.status]);
    const csv = headers.join(',') + '\n' + rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `MRP_Order_${selectedOrderId}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    showSuccess('Exported!');
}

// ==================== UTILITIES ====================

function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return parseFloat(num).toLocaleString('en-US', { maximumFractionDigits: 2 });
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function showSuccess(msg) { alert('✓ ' + msg); }
function showError(msg) { alert('✗ ' + msg); }
function closeModal() { document.getElementById('modal').style.display = 'none'; }

window.onclick = function(e) {
    if (e.target === document.getElementById('modal')) closeModal();
};
