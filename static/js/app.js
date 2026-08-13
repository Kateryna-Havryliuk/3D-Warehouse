let warehouseMap;
let currentLayout;

// Ініціалізація
document.addEventListener('DOMContentLoaded', async () => {
    // Завантажуємо макет складу
    const response = await fetch('/static/warehouse_layout.json');
    currentLayout = await response.json();
    
    // Створюємо карту
    warehouseMap = new WarehouseMap('warehouseSvg', currentLayout);
    
    // Підписка на події
    window.addEventListener('rackSelected', (e) => {
        showRackDetails(e.detail);
    });
    
    // Оновлюємо статистику
    updateStats();
    
    // Файл вибрано
    document.getElementById('csvFile').addEventListener('change', (e) => {
        const file = e.target.files[0];
        document.getElementById('fileName').textContent = file ? file.name : 'Файл не вибрано';
        document.getElementById('importBtn').disabled = !file;
    });
});

// Пошук товарів
async function searchItems() {
    const query = document.getElementById('searchInput').value.trim();
    if (query.length < 2) {
        alert('Введіть мінімум 2 символи');
        return;
    }
    
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const results = await response.json();
        
        displaySearchResults(results);
    } catch (error) {
        console.error('Помилка пошуку:', error);
    }
}

function displaySearchResults(results) {
    const overlay = document.getElementById('searchOverlay');
    const list = document.getElementById('resultsList');
    const count = document.getElementById('resultCount');
    
    if (!overlay) return;
    
    overlay.style.display = 'block';
    count.textContent = results.length;
    
    if (results.length === 0) {
        list.innerHTML = '<p>Нічого не знайдено</p>';
        return;
    }
    
    // Групуємо за стелажами
    const byRack = {};
    results.forEach(item => {
        if (!byRack[item.sector_id]) {
            byRack[item.sector_id] = {
                name: item.sector_name,
                color: item.color,
                items: []
            };
        }
        byRack[item.sector_id].items.push(item);
    });
    
    list.innerHTML = Object.entries(byRack).map(([rackId, data]) => `
        <div class="result-group" style="border-left: 4px solid ${data.color}; padding-left: 10px; margin-bottom: 15px;">
            <h4 onclick="focusOnRack('${rackId}')" style="cursor: pointer; color: ${data.color};">
                📍 Стелаж ${rackId} — ${data.name}
            </h4>
            ${data.items.map(item => `
                <div class="result-item" style="margin: 5px 0; padding: 8px; background: #f8f9fa; border-radius: 5px;">
                    <div style="font-weight: bold;">${item.name}</div>
                    <div style="font-size: 0.9em; color: #666;">
                        Артикул: ${item.article} | 
                        Кількість: ${item.quantity} шт |
                        ${item.shelf || 'Полиця не вказана'}
                    </div>
                </div>
            `).join('')}
        </div>
    `).join('');
}

function focusOnRack(rackId) {
    // Виділяємо на карті
    selectRack(rackId);
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    const overlay = document.getElementById('searchOverlay');
    if (overlay) overlay.style.display = 'none';
    
    // Знімаємо виділення
    document.querySelectorAll('.rack rect').forEach(r => {
        r.style.stroke = 'white';
        r.style.strokeWidth = '2';
    });
}

function quickSearch(term) {
    document.getElementById('searchInput').value = term;
    searchItems();
}

// Імпорт файлу
async function importFile() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Виберіть файл');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/import', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Помилка: ' + result.error);
        } else {
            alert(`✅ Імпортовано ${result.imported} записів!`);
            fileInput.value = '';
            document.getElementById('fileName').textContent = 'Файл не вибрано';
            document.getElementById('importBtn').disabled = true;
        }
    } catch (error) {
        alert('Помилка завантаження: ' + error);
    }
}

// Додаткові функції
function showAllRacks() {
    clearSearch();
    alert('На карті відображено всі 8 стелажів. Натисніть на будь-який для деталей.');
}

function showEmptyShelves() {
    alert('Функція в розробці. Використовуйте пошук для перевірки наявності товарів.');
}

function exportData() {
    alert('Експорт буде реалізовано у фінальній версії.');
}

// Enter для пошуку
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchItems();
        });
    }
    
    // Файл вибрано
    const fileInput = document.getElementById('csvFile');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            const nameSpan = document.getElementById('fileName');
            const btn = document.getElementById('importBtn');
            
            if (file) {
                nameSpan.textContent = file.name;
                btn.disabled = false;
            } else {
                nameSpan.textContent = 'Файл не вибрано';
                btn.disabled = true;
            }
        });
    }
});


// Деталі стелажа
async function showRackDetails(rack) {
    try {
        const response = await fetch(`/api/rack/${rack.id}/items`);
        const items = await response.json();
        
        document.getElementById('modalTitle').innerHTML = `
            Стелаж ${rack.id} <small style="color:#7f8c8d">(${rack.name})</small>
        `;
        
        // Візуалізація полиць
        let shelvesHtml = '';
        for (let i = 1; i <= rack.shelves; i++) {
            const shelfItems = items.filter(item => item.shelf == i);
            const totalQty = shelfItems.reduce((sum, item) => sum + item.quantity, 0);
            const fillPercent = Math.min(100, totalQty * 5); // Умовно
            
            shelvesHtml += `
                <div class="shelf-row">
                    <div class="shelf-label">Полиця ${i}</div>
                    <div class="shelf-bar">
                        <div class="shelf-fill" style="width: ${fillPercent}%"></div>
                        <span class="shelf-count">${shelfItems.length} позицій</span>
                    </div>
                    <div class="shelf-items">
                        ${shelfItems.map(item => `
                            <div class="shelf-item">
                                <span class="shelf-item-name">${item.name}</span>
                                <span class="shelf-item-qty">${item.quantity} шт</span>
                            </div>
                        `).join('') || '<span class="empty">Порожньо</span>'}
                    </div>
                </div>
            `;
        }
        
        document.getElementById('modalBody').innerHTML = `
            <div class="rack-info">
                <div class="info-grid">
                    <div class="info-item">
                        <label>Зона:</label>
                        <value>${rack.zone}</value>
                    </div>
                    <div class="info-item">
                        <label>Кількість полиць:</label>
                        <value>${rack.shelves}</value>
                    </div>
                    <div class="info-item">
                        <label>Розміри:</label>
                        <value>${rack.width}×${rack.height} м</value>
                    </div>
                </div>
                
                <h4>📦 Розподіл по полицях:</h4>
                <div class="shelves-container">
                    ${shelvesHtml}
                </div>
            </div>
        `;
        
        document.getElementById('rackModal').style.display = 'block';
    } catch (error) {
        console.error('Помилка:', error);
    }
}

function closeModal() {
    document.getElementById('rackModal').style.display = 'none';
}

// Інструменти карти
function resetView() {
    warehouseMap.zoom = 1;
    warehouseMap.panX = 0;
    warehouseMap.panY = 0;
    warehouseMap.updateTransform();
    updateZoomDisplay();
}

function zoomIn() {
    warehouseMap.zoom *= 1.2;
    warehouseMap.updateTransform();
    updateZoomDisplay();
}

function zoomOut() {
    warehouseMap.zoom /= 1.2;
    warehouseMap.updateTransform();
    updateZoomDisplay();
}

function updateZoomDisplay() {
    document.getElementById('zoomValue').textContent = 
        Math.round(warehouseMap.zoom * 100) + '%';
}

function updateStats() {
    const racks = currentLayout.warehouse.racks;
    const totalShelves = racks.reduce((sum, r) => sum + r.shelves, 0);
    
    document.getElementById('rackCount').textContent = racks.length;
    document.getElementById('shelfCount').textContent = totalShelves;
}

// Імпорт
async function importFile() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/import', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('❌ Помилка: ' + result.error);
        } else {
            alert(`✅ Успішно імпортовано ${result.imported} записів!`);
            fileInput.value = '';
            document.getElementById('fileName').textContent = 'Файл не вибрано';
            document.getElementById('importBtn').disabled = true;
        }
    } catch (error) {
        alert('❌ Помилка завантаження: ' + error);
    }
}

// Закриття модалки по кліку поза нею
window.onclick = function(event) {
    const modal = document.getElementById('rackModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}