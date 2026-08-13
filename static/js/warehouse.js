// Проста робоча версія без складного масштабування
let warehouseMap;
let currentScale = 15;
let currentZoom = 1;

document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Завантажуємо макет
        const response = await fetch('/api/layout');
        const data = await response.json();
        
        renderWarehouse(data.warehouse);
        updateLegend(data.warehouse.racks);
        
    } catch (error) {
        console.error('Помилка завантаження:', error);
        document.getElementById('warehouseSvg').innerHTML = 
            '<text x="50" y="50" fill="red">Помилка завантаження карти</text>';
    }
});

function renderWarehouse(warehouse) {
    const svg = document.getElementById('warehouseSvg');
    const width = warehouse.width * currentScale;
    const height = warehouse.height * currentScale;
    
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.style.width = '100%';
    svg.style.height = '100%';
    
    let html = '';
    
    // Фон
    html += `<rect x="0" y="0" width="${width}" height="${height}" fill="#2c3e50" stroke="#34495e" stroke-width="2"/>`;
    
    // Сітка (опціонально)
    for (let x = 0; x <= width; x += currentScale * 5) {
        html += `<line x1="${x}" y1="0" x2="${x}" y2="${height}" stroke="#34495e" stroke-width="0.5" opacity="0.3"/>`;
    }
    for (let y = 0; y <= height; y += currentScale * 5) {
        html += `<line x1="0" y1="${y}" x2="${width}" y2="${y}" stroke="#34495e" stroke-width="0.5" opacity="0.3"/>`;
    }
    
    // Зони
    warehouse.zones.forEach(zone => {
        const zx = zone.x * currentScale;
        const zy = zone.y * currentScale;
        const zw = zone.width * currentScale;
        const zh = zone.height * currentScale;
        
        html += `<rect x="${zx}" y="${zy}" width="${zw}" height="${zh}" 
                       fill="${zone.color}" opacity="0.3" stroke="${zone.color}" stroke-width="2" stroke-dasharray="5,5"/>`;
        html += `<text x="${zx + zw/2}" y="${zy + zh/2}" text-anchor="middle" 
                       fill="${zone.color}" font-size="12" font-weight="bold">${zone.name}</text>`;
    });
    
    // Стелажі
    warehouse.racks.forEach(rack => {
        const rx = rack.x * currentScale;
        const ry = rack.y * currentScale;
        const rw = rack.width * currentScale;
        const rh = rack.height * currentScale;
        
        // Основа стелажа
        html += `<g class="rack" onclick="selectRack('${rack.id}')" style="cursor: pointer;">`;
        html += `<rect x="${rx}" y="${ry}" width="${rw}" height="${rh}" 
                       fill="${rack.color}" stroke="white" stroke-width="2" rx="3"
                       onmouseover="this.style.filter='brightness(1.2)'" 
                       onmouseout="this.style.filter='none'"/>`;
        
        // Полиці (лінії)
        const shelfHeight = rh / rack.shelves;
        for (let i = 1; i < rack.shelves; i++) {
            const sy = ry + (i * shelfHeight);
            html += `<line x1="${rx}" y1="${sy}" x2="${rx + rw}" y2="${sy}" 
                          stroke="rgba(255,255,255,0.6)" stroke-width="1"/>`;
        }
        
        // Текст ID
        html += `<text x="${rx + rw/2}" y="${ry + rh/2}" text-anchor="middle" 
                       dominant-baseline="middle" fill="white" font-size="16" font-weight="bold">${rack.id}</text>`;
        
        // Назва під стелажем
        html += `<text x="${rx + rw/2}" y="${ry + rh + 15}" text-anchor="middle" 
                       fill="${rack.color}" font-size="10">${rack.shelves} полиць</text>`;
        
        html += `</g>`;
    });
    
    svg.innerHTML = html;
}

function selectRack(rackId) {
    // Підсвітка
    document.querySelectorAll('.rack rect').forEach(r => {
        r.style.stroke = 'white';
        r.style.strokeWidth = '2';
    });
    
    event.target.style.stroke = '#f1c40f';
    event.target.style.strokeWidth = '4';
    
    // Завантажуємо дані
    loadRackInfo(rackId);
}

async function loadRackInfo(rackId) {
    try {
        const response = await fetch(`/api/rack/${rackId}/items`);
        const data = await response.json();
        
        const panel = document.getElementById('infoPanel');
        
        if (!data.rack) {
            panel.innerHTML = '<h3>❌ Помилка</h3><p>Стелаж не знайдено</p>';
            return;
        }
        
        let itemsHtml = '';
        if (data.items && data.items.length > 0) {
            // Групуємо по полицях
            const byShelf = {};
            data.items.forEach(item => {
                const shelf = item.shelf || 'Без полиці';
                if (!byShelf[shelf]) byShelf[shelf] = [];
                byShelf[shelf].push(item);
            });
            
            itemsHtml = '<div class="shelves-list">';
            Object.entries(byShelf).sort().forEach(([shelf, items]) => {
                itemsHtml += `<div class="shelf-group">
                    <h4>${shelf}</h4>
                    ${items.map(item => `
                        <div class="item-row">
                            <span class="item-name">${item.name}</span>
                            <span class="item-qty">${item.quantity} шт</span>
                        </div>
                    `).join('')}
                </div>`;
            });
            itemsHtml += '</div>';
        } else {
            itemsHtml = '<p class="empty">Стелаж порожній</p>';
        }
        
        panel.innerHTML = `
            <h3>📦 Стелаж ${data.rack.id}</h3>
            <p><strong>${data.rack.name}</strong></p>
            <p>Зона: ${data.rack.zone}</p>
            <p>Полиць: ${data.rack.shelves}</p>
            <hr>
            <h4>Товари:</h4>
            ${itemsHtml}
        `;
        
    } catch (error) {
        console.error('Помилка:', error);
    }
}

function updateLegend(racks) {
    const legend = document.getElementById('legendItems');
    if (!legend) return;
    
    const colors = {};
    racks.forEach(r => {
        if (!colors[r.zone]) colors[r.zone] = r.color;
    });
    
    legend.innerHTML = Object.entries(colors).map(([zone, color]) => `
        <div class="legend-item">
            <span class="color-box" style="background:${color}"></span>
            <span>${zone}</span>
        </div>
    `).join('');
}

// Прості функції масштабування
function zoomIn() {
    currentZoom *= 1.2;
    applyZoom();
}

function zoomOut() {
    currentZoom /= 1.2;
    applyZoom();
}

function resetView() {
    currentZoom = 1;
    applyZoom();
}

function applyZoom() {
    const svg = document.getElementById('warehouseSvg');
    svg.style.transform = `scale(${currentZoom})`;
    svg.style.transformOrigin = 'center center';
    
    const display = document.getElementById('zoomValue');
    if (display) display.textContent = Math.round(currentZoom * 100) + '%';
}