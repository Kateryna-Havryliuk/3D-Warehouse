import sqlite3
import json
from datetime import datetime

DB_PATH = 'data/warehouse.db'

def get_db():
    """Отримує з'єднання з базою даних"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Ініціалізація бази даних з покращеною структурою"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Таблиця секторів (стелажів)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sectors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            x INTEGER,
            y INTEGER,
            width INTEGER,
            height INTEGER,
            color TEXT DEFAULT '#3498db',
            zone TEXT DEFAULT 'general',
            max_shelves INTEGER DEFAULT 5
        )
    ''')
    
    # Таблиця товарів
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            barcode TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблиця розташувань (один товар може бути на різних полицях!)
    c.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            sector_id TEXT NOT NULL,
            quantity INTEGER DEFAULT 0 CHECK(quantity >= 0),
            shelf TEXT NOT NULL DEFAULT 'Полиця 1',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE CASCADE,
            UNIQUE(item_id, sector_id, shelf)
        )
    ''')
    
    # Таблиця історії переміщень
    c.execute('''
        CREATE TABLE IF NOT EXISTS movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            from_sector TEXT,
            to_sector TEXT,
            from_shelf TEXT,
            to_shelf TEXT,
            quantity INTEGER,
            user TEXT,
            comment TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    ''')
    
    # Оптимізовані індекси
    c.execute('CREATE INDEX IF NOT EXISTS idx_items_name ON items(name COLLATE NOCASE)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_items_article ON items(article COLLATE NOCASE)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_items_barcode ON items(barcode)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_locations_sector ON locations(sector_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_locations_shelf ON locations(shelf)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_locations_item ON locations(item_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_movements_timestamp ON movements(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_movements_item ON movements(item_id)')
    
    conn.commit()
    conn.close()

def add_sector(sector_id, name, x, y, width, height, color='#3498db', zone='general', max_shelves=5):
    """Додати або оновити сектор"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO sectors (id, name, x, y, width, height, color, zone, max_shelves)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (sector_id, name, x, y, width, height, color, zone, max_shelves))
    conn.commit()
    conn.close()

def add_item(article, name, description='', category='', barcode=None):
    """Додати або оновити товар. Повертає ID товару."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id FROM items WHERE article = ?', (article,))
    existing = c.fetchone()
    
    if existing:
        c.execute('''
            UPDATE items SET name = ?, description = ?, category = ?, barcode = ?
            WHERE article = ?
        ''', (name, description, category, barcode, article))
        item_id = existing[0]
    else:
        c.execute('''
            INSERT INTO items (article, name, description, category, barcode)
            VALUES (?, ?, ?, ?, ?)
        ''', (article, name, description, category, barcode))
        item_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return item_id

def add_location(item_id, sector_id, quantity=0, shelf='Полиця 1'):
    """Додати або оновити розташування товару"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Перевіряємо чи існує запис
    c.execute('''
        SELECT id, quantity FROM locations 
        WHERE item_id = ? AND sector_id = ? AND shelf = ?
    ''', (item_id, sector_id, shelf))
    
    existing = c.fetchone()
    
    if existing:
        # Оновлюємо кількість
        c.execute('''
            UPDATE locations SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (quantity, existing[0]))
    else:
        # Створюємо новий запис
        c.execute('''
            INSERT INTO locations (item_id, sector_id, quantity, shelf, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (item_id, sector_id, quantity, shelf))
    
    conn.commit()
    conn.close()

def update_item_quantity(item_id, sector_id, shelf, new_quantity):
    """Оновити кількість конкретного товару на конкретній полиці"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        UPDATE locations SET quantity = ?, updated_at = CURRENT_TIMESTAMP
        WHERE item_id = ? AND sector_id = ? AND shelf = ?
    ''', (new_quantity, item_id, sector_id, shelf))
    
    conn.commit()
    conn.close()

def delete_item(item_id):
    """Видалити товар та всі його розташування (каскадно)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Спочатку видаляємо історію
    c.execute('DELETE FROM movements WHERE item_id = ?', (item_id,))
    # Розташування видаляться каскадно через FOREIGN KEY
    c.execute('DELETE FROM items WHERE id = ?', (item_id,))
    
    conn.commit()
    conn.close()

def get_all_sectors():
    """Отримати всі сектори"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM sectors ORDER BY zone, id')
    sectors = [dict(row) for row in c.fetchall()]
    conn.close()
    return sectors

def search_items(query, limit=50):
    """Пошук товарів з ранжуванням релевантності"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    search_pattern = f'%{query}%'
    exact_match = query
    
    c.execute('''
        SELECT 
            i.id as item_id,
            i.article,
            i.name,
            i.description,
            i.category,
            i.barcode,
            s.id as sector_id,
            s.name as sector_name,
            s.color as sector_color,
            l.quantity,
            l.shelf,
            CASE 
                WHEN i.article = ? THEN 1
                WHEN i.article LIKE ? THEN 2
                WHEN i.name LIKE ? THEN 3
                WHEN i.barcode = ? THEN 1
                ELSE 4
            END as relevance
        FROM items i
        JOIN locations l ON i.id = l.item_id
        JOIN sectors s ON l.sector_id = s.id
        WHERE i.name LIKE ? OR i.article LIKE ? OR i.barcode LIKE ? OR i.category LIKE ?
        ORDER BY relevance, i.name
        LIMIT ?
    ''', (exact_match, f'{exact_match}%', f'{exact_match}%', exact_match,
          search_pattern, search_pattern, search_pattern, search_pattern, limit))
    
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_item_by_article(article):
    """Отримати товар за артикулом або штрихкодом"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT i.*, l.sector_id, l.quantity, l.shelf, s.name as sector_name, s.color
        FROM items i
        JOIN locations l ON i.id = l.item_id
        JOIN sectors s ON l.sector_id = s.id
        WHERE i.article = ? OR i.barcode = ?
        LIMIT 1
    ''', (article, article))
    
    result = c.fetchone()
    conn.close()
    return dict(result) if result else None

def get_item_locations(item_id):
    """Отримати всі розташування конкретного товару"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT l.*, s.name as sector_name, s.color
        FROM locations l
        JOIN sectors s ON l.sector_id = s.id
        WHERE l.item_id = ?
        ORDER BY l.sector_id, l.shelf
    ''', (item_id,))
    
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_sector_items(sector_id):
    """Отримати товари в секторі з групуванням по полицях"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            i.id,
            i.article,
            i.name,
            i.category,
            i.barcode,
            l.quantity,
            l.shelf
        FROM items i
        JOIN locations l ON i.id = l.item_id
        WHERE l.sector_id = ?
        ORDER BY l.shelf, i.name
    ''', (sector_id,))
    
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_shelf_items(sector_id, shelf_name):
    """Отримати товари на конкретній полиці"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT i.id, i.article, i.name, i.category, i.description, i.barcode, l.quantity, l.shelf
        FROM items i
        JOIN locations l ON i.id = l.item_id
        WHERE l.sector_id = ? AND l.shelf = ?
        ORDER BY i.name
    ''', (sector_id, shelf_name))
    
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_all_items():
    """Отримати всі товари з розташуваннями"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            i.id,
            i.article,
            i.name,
            i.category,
            i.barcode,
            s.id as sector_id,
            s.name as sector_name,
            l.quantity,
            l.shelf
        FROM items i
        JOIN locations l ON i.id = l.item_id
        JOIN sectors s ON l.sector_id = s.id
        ORDER BY i.name
    ''')
    
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_warehouse_stats():
    """Отримати загальну статистику складу"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM items')
    total_items = c.fetchone()[0]
    
    c.execute('SELECT SUM(quantity) FROM locations')
    total_quantity = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(DISTINCT sector_id) FROM locations')
    active_sectors = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM sectors')
    total_sectors = c.fetchone()[0]
    
    # Статистика по зонах
    c.execute('''
        SELECT s.zone, COUNT(DISTINCT i.id) as items, SUM(l.quantity) as quantity
        FROM items i
        JOIN locations l ON i.id = l.item_id
        JOIN sectors s ON l.sector_id = s.id
        GROUP BY s.zone
    ''')
    zone_stats = [dict(row) for row in c.fetchall()]
    
    # Статистика по категоріях
    c.execute('''
        SELECT category, COUNT(*) as count, SUM(l.quantity) as total
        FROM items i
        JOIN locations l ON i.id = l.item_id
        GROUP BY category
        ORDER BY total DESC
    ''')
    categories = []
    for row in c.fetchall():
        categories.append({
            'name': row[0] or 'Без категорії',
            'count': row[1],
            'total': row[2]
        })
    
    conn.close()
    
    return {
        'total_items': total_items,
        'total_quantity': total_quantity,
        'active_sectors': active_sectors,
        'total_sectors': total_sectors,
        'categories': categories,
        'zone_stats': zone_stats
    }