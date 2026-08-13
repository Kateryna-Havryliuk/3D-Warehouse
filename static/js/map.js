let sectors = [];
let searchTimeout;

// Завантаження секторів при старті
document.addEventListener('DOMContentLoaded', () => {
    loadSectors();
    
    // Enter для пошуку
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') search();
    });
});

async function loadSectors() {
    try {
        const response = await fetch('/api/sectors');
        sectors = await response.json();
        renderSectors();
    } catch (error) {
        console.error('Помилка завантаження секторів:', error);
    }
}

function renderSectors() {
    const container = document.getElementById('sectors');
    container.innerHTML = '';
    
    sectors.forEach(sector => {
        // Група для сектора
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.classList.add('sector');
        g.setAttribute('data-id', sector.id);
        g.onclick = () => showSectorInfo(sector.id);
        
        // Прямокутник сектора
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', sector.x);
        rect.setAttribute('y', sector.y);
        rect.setAttribute('width', sector.width);
        rect.setAttribute('height', sector.height);
        rect.setAttribute('fill', sector.color);
        rect.setAttribute('rx', 8);
        rect.setAttribute('stroke', 'white');
        rect.setAttribute('stroke-width', '2');
        
        // ID сектора (великий)
        const textId = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        textId.setAttribute('x', sector.x + sector.width/2);
        textId.setAttribute('y', sector.y + sector.height/2 - 5);
        textId.classList.add('sector-id');
        textId.textContent = sector.id;
        
        // Назва сектора (менша)
        const textName = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        textName.setAttribute('x', sector.x + sector.width/2);
        textName.setAttribute('y', sector.y + sector.height/2 + 15);
        textName.classList.add('sector-label');
        textName.textContent = sector.name;
        
        g.appendChild(rect);
        g.appendChild(textId);
        g.appendChild(textName);
        container.appendChild(g);
    });
}

async function search() {
    const query = document.getElementById('searchInput').value.trim();
    if (query.length < 2) {
        alert('Введіть мінімум 2 символи');
        return;
    }
    
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const results = await response.json();
        
        displaySearchResults(results);
        highlightSectors(results);
    } catch (error) {
        console.error('Помилка пошуку:', error);
    }
}

function displaySearchResults(results) {
    const panel = document.getElementById('searchResults');
    const list = document.getElementById('resultsList');
    const infoPanel = document.getElementById('infoPanel');
    
    if (results.length === 0) {
        list.innerHTML = '<p>Нічого не знайдено 😕</p>';
    } else {
        list.innerHTML = results.map(item => `
            <div class="result-item" onclick="focusSector('${item.sector_id}')">
                <div class="article">Артикул: ${item.article}</div>
                <div class="name">${item.name}</div>
                <div class="location">📍 Сектор ${item.sector_id} (${item.sector_name}) 
                    ${item.shelf ? '- ' + item.shelf : ''} | 
                    Кількість: <span class="qty">${item.quantity} шт</span>
                </div>
            </div>
        `).join('');
    }
    
    infoPanel.style.display = 'none';
    panel.style.display = 'block';
}

function highlightSectors(results) {
    // Очистити попередні підсвітки
    document.querySelectorAll('.sector rect').forEach(rect => {
        rect.classList.remove('highlight');
        rect.setAttribute('stroke', 'white');
        rect.setAttribute('stroke-width', '2');
    });
    
    // Підсвітити знайдені сектори
    const sectorIds = [...new Set(results.map(r => r.sector_id))];
    sectorIds.forEach(id => {
        const sector = document.querySelector(`.sector[data-id="${id}"] rect`);
        if (sector) {
            sector.classList.add('highlight');
        }
    });
}

function focusSector(sectorId) {
    // Показати інформацію про сектор
    showSectorInfo(sectorId);
    
    // Прокрутити до карти на мобільних
    document.querySelector('.map-container').scrollIntoView({ behavior: 'smooth' });
}

async function showSectorInfo(sectorId) {
    try {
        const [sectorResponse, itemsResponse] = await Promise.all([
            fetch('/api/sectors'),
            fetch(`/api/sector/${sectorId}`)
        ]);
        
        const allSectors = await sectorResponse.json();
        const sector = allSectors.find(s => s.id === sectorId);
        const items = await itemsResponse.json();
        
        document.getElementById('modalTitle').textContent = 
            `Сектор ${sector.id} - ${sector.name}`;
        
        const content = document.getElementById('modalContent');
        if (items.length === 0) {
            content.innerHTML = '<p>У цьому секторі поки немає товарів.</p>';
        } else {
            content.innerHTML = `
                <div class="item-list">
                    ${items.map(item => `
                        <div class="item-card">
                            <h4>${item.name}</h4>
                            <p><strong>Артикул:</strong> ${item.article}</p>
                            <p><strong>Категорія:</strong> ${item.category || 'Не вказано'}</p>
                            <p><strong>Кількість:</strong> <span class="qty">${item.quantity} шт</span></p>
                            ${item.shelf ? `<p><strong>Розташування:</strong> ${item.shelf}</p>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        document.getElementById('sectorModal').style.display = 'block';
    } catch (error) {
        console.error('Помилка:', error);
    }
}

function closeModal() {
    document.getElementById('sectorModal').style.display = 'none';
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('infoPanel').style.display = 'block';
    
    // Очистити підсвітки
    document.querySelectorAll('.sector rect').forEach(rect => {
        rect.classList.remove('highlight');
        rect.setAttribute('stroke', 'white');
    });
}

// Закрити модальне вікно при кліку поза ним
window.onclick = function(event) {
    const modal = document.getElementById('sectorModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Імпорт CSV
async function importData() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Виберіть файл CSV');
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
        }
    } catch (error) {
        alert('Помилка завантаження: ' + error);
    }
}