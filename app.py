from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
from database import *
import os
import json
import csv
import requests
import io
import sqlite3
import re
import glob
from threading import Thread
import time
import pandas as pd
from datetime import datetime

try:
    import win32com.client  # type: ignore
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

app = Flask(__name__)
CORS(app)  # Дозволяємо CORS для всіх доменів

# Налаштування папки даних
if not os.path.exists('data'):
    os.makedirs('data')

# Ініціалізація БД при старті
init_db()

# ==========================================
# КОНФІГУРАЦІЯ СКЛАДУ (СИНХРОНІЗОВАНО З FRONTEND!)
# ==========================================

WAREHOUSE_CONFIG = {
    'width': 41,      # м
    'depth': 18,      # м  
    'height': 4,      # м
    'rack_height': 2.7,
    'center_rack_height': 2.5
}

# Стелажі згідно з frontend (index.html)
RACKS_CONFIG = [
    # === ПІВНІЧНА ЗОНА (N1-N7) ===
    {'id': 'N1', 'name': 'П1', 'zone': 'north', 'x': 3, 'z': 0.8, 'w': 5, 'd': 1.5, 'h': 2.7, 'shelves': 6, 'color': '#9f7aea'},
    {'id': 'N2', 'name': 'П2', 'zone': 'north', 'x': 8.5, 'z': 1.35, 'w': 6, 'd': 2.7, 'h': 2.7, 'shelves': 6, 'color': '#9f7aea'},
    {'id': 'N3', 'name': 'П3', 'zone': 'north', 'x': 14.5, 'z': 1.35, 'w': 6, 'd': 2.7, 'h': 2.7, 'shelves': 6, 'color': '#9f7aea'},
    {'id': 'N4', 'name': 'П4', 'zone': 'north', 'x': 20.5, 'z': 1.35, 'w': 6, 'd': 2.7, 'h': 2.7, 'shelves': 6, 'color': '#9f7aea'},
    {'id': 'N5', 'name': 'П5', 'zone': 'north', 'x': 26.5, 'z': 1.35, 'w': 6, 'd': 2.7, 'h': 2.7, 'shelves': 6, 'color': '#9f7aea'},
    {'id': 'N6', 'name': 'П6', 'zone': 'north', 'x': 32.5, 'z': 1.35, 'w': 6, 'd': 2.7, 'h': 2.7, 'shelves': 6, 'color': '#9f7aea'},
    {'id': 'N7', 'name': 'П7', 'zone': 'north', 'x': 38, 'z': 1.35, 'w': 5.1, 'd': 2.7, 'h': 2.7, 'shelves': 6, 'color': '#9f7aea'},
    
    # === ЗАХІДНА ЗОНА (W1-W4) ===
    {'id': 'W1', 'name': 'З1', 'zone': 'west', 'x': 2.5, 'z': 8.4, 'w': 6, 'd': 1.6, 'h': 2.7, 'shelves': 6, 'color': '#ed64a6'},
    {'id': 'W2', 'name': 'З2', 'zone': 'west', 'x': 2.5, 'z': 10, 'w': 6, 'd': 1.6, 'h': 2.7, 'shelves': 5, 'color': '#ed64a6'},
    {'id': 'W3', 'name': 'З3', 'zone': 'west', 'x': 7.3, 'z': 17, 'w': 3, 'd': 2, 'h': 2, 'shelves': 4, 'color': '#ed64a6'},
    {'id': 'W4', 'name': 'З4', 'zone': 'west', 'x': 16.7, 'z': 17, 'w': 3, 'd': 2, 'h': 2, 'shelves': 4, 'color': '#ed64a6'},
    
    # === ЦЕНТРАЛЬНА ЗОНА (C1-C5) ===
    {'id': 'C1', 'name': 'Ц1', 'zone': 'center', 'x': 19, 'z': 13, 'w': 1, 'd': 10, 'h': 2.5, 'shelves': 6, 'color': '#4fd1c5'},
    {'id': 'C2', 'name': 'Ц2', 'zone': 'center', 'x': 21, 'z': 13, 'w': 1, 'd': 10, 'h': 2.5, 'shelves': 6, 'color': '#4fd1c5'},
    {'id': 'C3', 'name': 'Ц3', 'zone': 'center', 'x': 23, 'z': 13, 'w': 1, 'd': 10, 'h': 2.5, 'shelves': 6, 'color': '#4fd1c5'},
    {'id': 'C4', 'name': 'Ц4', 'zone': 'center', 'x': 25, 'z': 13, 'w': 1, 'd': 10, 'h': 2.5, 'shelves': 6, 'color': '#4fd1c5'},
    {'id': 'C5', 'name': 'Ц5', 'zone': 'center', 'x': 27, 'z': 13, 'w': 1, 'd': 10, 'h': 2.5, 'shelves': 6, 'color': '#4fd1c5'},
    
    # === СХІДНА ЗОНА (E1-E3) ===
    {'id': 'E1', 'name': 'С1', 'zone': 'east', 'x': 35, 'z': 9, 'w': 9.5, 'd': 2, 'h': 2.7, 'shelves': 5, 'color': '#f6ad55'},
    {'id': 'E2', 'name': 'С2', 'zone': 'east', 'x': 35, 'z': 11, 'w': 9.5, 'd': 2, 'h': 2.7, 'shelves': 5, 'color': '#f6ad55'},
    {'id': 'E3', 'name': 'С3', 'zone': 'east', 'x': 35, 'z': 17, 'w': 9.5, 'd': 2, 'h': 2.2, 'shelves': 4, 'color': '#f6ad55'},
]

def init_warehouse_data():
    """Ініціалізація стелажів у БД"""
    for rack in RACKS_CONFIG:
        add_sector(
            rack['id'],
            rack['name'],
            int(rack['x'] * 10),
            int(rack['z'] * 10),
            int(rack['w'] * 10),
            int(rack['d'] * 10),
            rack['color'],
            rack['zone'],
            rack['shelves']
        )

def seed_test_data():
    """Додавання тестових товарів тільки якщо база порожня"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM items')
    count = c.fetchone()[0]
    conn.close()
    
    if count == 0:
        test_items = [
            ('AX-750', 'Вісь AL-KO 750кг без гальм', 'Вісь для легкових причепів', 'Вісі', '200000001234', 'N1', 'Полиця 2', 15),
            ('AX-1350B', 'Вісь AL-KO 1350кг гальмівна', 'З гальмами', 'Вісі', '200000001235', 'N2', 'Полиця 3', 8),
            ('RS-3L-750', 'Ресора 3-листова 750кг', 'Для причепів до 750кг', 'Підвіска', '200000001236', 'W1', 'Полиця 1', 25),
            ('LED-12V-R', 'Ліхтар задній LED червоний', '12V, стоп-сигнал', 'Освітлення', '200000001237', 'C1', 'Полиця 1', 50),
            ('SPR-1000', 'Амортизатор AL-KO 1000кг', 'Гідравлічний', 'Підвіска', '200000001238', 'C3', 'Полиця 2', 12),
            ('CABLE-7M', 'Кабель 7-контактний 5м', 'Для причепів', 'Електрика', '200000001239', 'E1', 'Полиця 3', 30),
            ('WHEEL-13', 'Колесо 13" з шиною', 'Для причепів', 'Колеса', '200000001240', 'E2', 'Полиця 1', 20),
            ('COUPLING-50', 'Фаркоп 50мм', 'Знімний', 'Фурнітура', '200000001241', 'W2', 'Полиця 2', 10),
        ]
        
        for article, name, desc, cat, barcode, rack_id, shelf, qty in test_items:
            item_id = add_item(article, name, desc, cat, barcode)
            add_location(item_id, rack_id, qty, shelf)

# Ініціалізуємо дані при імпорті модуля
init_warehouse_data()
seed_test_data()

# ==========================================
# API ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/layout')
def api_layout():
    """Отримати конфігурацію складу"""
    return jsonify({
        'warehouse': WAREHOUSE_CONFIG,
        'racks': RACKS_CONFIG
    })

@app.route('/api/sectors')
def api_sectors():
    """Отримати всі сектори"""
    return jsonify(get_all_sectors())

@app.route('/api/racks')
def api_racks():
    """Отримати список стелажів для форм"""
    racks = [{'id': r['id'], 'name': r['name'], 'shelves': r['shelves'], 'zone': r['zone']} 
             for r in RACKS_CONFIG]
    return jsonify(racks)

@app.route('/api/search')
def api_search():
    """Пошук товарів"""
    query = request.args.get('q', '').strip()
    if len(query) < 1:
        # Повертаємо всі товари якщо запит порожній
        return jsonify(get_all_items())
    
    results = search_items(query)
    return jsonify(results)

@app.route('/api/item/<article>')
def api_item_by_article(article):
    """Отримати товар за артикулом"""
    item = get_item_by_article(article)
    if item:
        # Додаємо всі розташування цього товару
        item['locations'] = get_item_locations(item['id'])
        return jsonify(item)
    return jsonify({'error': 'Товар не знайдено'}), 404

@app.route('/api/item/barcode/<barcode>')
def api_item_by_barcode(barcode):
    """Отримати товар за штрихкодом"""
    item = get_item_by_article(barcode)  # Функція шукає і по штрихкоду
    if item:
        item['locations'] = get_item_locations(item['id'])
        return jsonify(item)
    return jsonify({'error': 'Товар не знайдено'}), 404

@app.route('/api/sector/<sector_id>')
def api_sector_items(sector_id):
    """Отримати товари в секторі з групуванням по полицях"""
    items = get_sector_items(sector_id)
    
    # Групуємо по полицях
    shelves = {}
    for item in items:
        shelf = item.get('shelf', 'Полиця 1')
        if shelf not in shelves:
            shelves[shelf] = []
        shelves[shelf].append(item)
    
    return jsonify({
        'sector_id': sector_id,
        'shelves': shelves,
        'total_items': len(items)
    })

@app.route('/api/shelf/<sector_id>/<path:shelf_name>')
def api_shelf_items(sector_id, shelf_name):
    """Отримати товари на конкретній полиці"""
    items = get_shelf_items(sector_id, shelf_name)
    return jsonify(items)

@app.route('/api/item', methods=['POST'])
def api_add_item():
    """Додати новий товар"""
    data = request.json
    
    required = ['article', 'name', 'sector_id', 'shelf', 'quantity']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f"Поле '{field}' обов'язкове"}), 400
    
    # Перевіряємо чи існує стелаж
    rack_ids = [r['id'] for r in RACKS_CONFIG]
    if data['sector_id'] not in rack_ids:
        return jsonify({'error': f"Стелаж '{data['sector_id']}' не існує"}), 400
    
    try:
        item_id = add_item(
            data['article'],
            data['name'],
            data.get('description', ''),
            data.get('category', ''),
            data.get('barcode')
        )
        
        add_location(item_id, data['sector_id'], int(data['quantity']), data['shelf'])
        
        return jsonify({
            'success': True,
            'item_id': item_id,
            'message': 'Товар успішно додано'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/item/<int:item_id>', methods=['PUT'])
def api_update_item(item_id):
    """Оновити товар"""
    data = request.json
    
    try:
        # Оновлюємо кількість на конкретній полиці
        if 'sector_id' in data and 'shelf' in data:
            update_item_quantity(item_id, data['sector_id'], data['shelf'], data.get('quantity', 0))
        return jsonify({'success': True, 'message': 'Кількість оновлено'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/item/<int:item_id>', methods=['DELETE'])
def api_delete_item(item_id):
    """Видалити товар"""
    try:
        delete_item(item_id)
        return jsonify({'success': True, 'message': 'Товар видалено'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import', methods=['POST'])
def api_import():
    """Імпорт товарів з CSV/Excel"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не завантажено'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не вибрано'}), 400
    
    filename = file.filename.lower()
    
    try:
        imported = 0
        errors = []
        
        if filename.endswith('.csv'):
            imported, errors = import_csv(file)
        elif filename.endswith(('.xlsx', '.xls')):
            imported, errors = import_excel(file)
        else:
            return jsonify({'error': 'Підтримуються тільки CSV та Excel файли'}), 400
        
        return jsonify({
            'imported': imported,
            'errors': errors,
            'success': len(errors) == 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def import_csv(file):
    """Імпорт з CSV"""
    imported = 0
    errors = []
    
    content = file.stream.read()
    encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'windows-1251']
    text = None
    
    for enc in encodings:
        try:
            text = content.decode(enc)
            break
        except:
            continue
    
    if text is None:
        raise Exception('Не вдалося визначити кодування файлу')
    
    stream = io.StringIO(text)
    sample = stream.read(1024)
    stream.seek(0)
    
    delimiter = ';' if ';' in sample else ','
    reader = csv.DictReader(stream, delimiter=delimiter)
    
    fieldnames = [f.strip().replace('\ufeff', '') for f in reader.fieldnames] if reader.fieldnames else []
    
    # Маппінг колонок
    column_map = {
        'article': ['Артикул', 'артикул', 'Код', 'код', 'Code', 'SKU', 'Номенклатура.Артикул'],
        'name': ['Найменування', 'назва', 'Назва', 'Наименование', 'Name', 'Номенклатура', 'Товар'],
        'sector': ['Сектор', 'сектор', 'Стелаж', 'стелаж', 'Sector', 'Rack', 'МестоХранения', 'Стеллаж'],
        'quantity': ['Кількість', 'количество', 'Количество', 'Quantity', 'Колво', 'Остаток'],
        'shelf': ['Полиця', 'полиця', 'Полка', 'полка', 'Shelf', 'Ярус', 'Уровень', 'Ярус'],
        'category': ['Категорія', 'категория', 'Категория', 'Category', 'Группа', 'ВидНоменклатуры'],
        'description': ['Опис', 'опис', 'Описание', 'Description', 'Комментарий'],
        'barcode': ['Штрихкод', 'штрихкод', 'Barcode', 'EAN', 'Код товару', 'ШтрихКод']
    }
    
    def find_column(variants):
        for variant in variants:
            for fn in fieldnames:
                if fn.lower().strip() == variant.lower().strip():
                    return fn
        return None
    
    col_article = find_column(column_map['article'])
    col_name = find_column(column_map['name'])
    col_sector = find_column(column_map['sector'])
    col_qty = find_column(column_map['quantity'])
    col_shelf = find_column(column_map['shelf'])
    col_cat = find_column(column_map['category'])
    col_desc = find_column(column_map['description'])
    col_barcode = find_column(column_map['barcode'])
    
    if not col_article or not col_name:
        raise Exception("Не знайдено обов'язкові колонки: Артикул та Найменування")
    
    # Валідні ID стелажів
    valid_racks = [r['id'] for r in RACKS_CONFIG]
    
    for row_num, row in enumerate(reader, start=2):
        try:
            article = str(row.get(col_article, '')).strip()
            name = str(row.get(col_name, '')).strip()
            sector_id = str(row.get(col_sector, 'N1')).strip() if col_sector else 'N1'
            quantity_str = str(row.get(col_qty, '0')).strip() if col_qty else '0'
            shelf = str(row.get(col_shelf, '')).strip() if col_shelf else ''
            category = str(row.get(col_cat, '')).strip() if col_cat else ''
            description = str(row.get(col_desc, '')).strip() if col_desc else ''
            barcode = str(row.get(col_barcode, '')).strip() if col_barcode else None
            
            if not article or not name:
                continue
            
            # Валідація стелажа
            if sector_id not in valid_racks:
                # Спробуємо знайти за ім'ям
                rack_by_name = next((r for r in RACKS_CONFIG if r['name'] == sector_id), None)
                if rack_by_name:
                    sector_id = rack_by_name['id']
                else:
                    errors.append(f'Рядок {row_num}: Невідомий стелаж "{sector_id}"')
                    continue
            
            # Парсинг кількості
            try:
                quantity = int(float(quantity_str.replace(',', '.').replace(' ', '')))
            except:
                quantity = 0
            
            # Нормалізація полиці
            if shelf:
                match = re.search(r'\d+', str(shelf))
                if match:
                    shelf = f'Полиця {match.group()}'
                else:
                    shelf = f'Полиця {shelf}'
            else:
                shelf = 'Полиця 1'
            
            item_id = add_item(article, name, description, category, barcode)
            add_location(item_id, sector_id, quantity, shelf)
            
            imported += 1
            
        except Exception as e:
            errors.append(f'Рядок {row_num}: {str(e)}')
    
    return imported, errors

def import_excel(file):
    """Імпорт з Excel"""
    try:
        df = pd.read_excel(file.stream)
    except Exception as e:
        raise Exception(f'Не вдалося прочитати Excel файл: {str(e)}')
    
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_buffer.seek(0)
    
    class FileWrapper:
        def __init__(self, stream):
            self.stream = stream
    
    wrapper = FileWrapper(csv_buffer)
    return import_csv(wrapper)

@app.route('/api/export/template')
def download_template():
    """Завантажити шаблон для імпорту"""
    template = """Артикул;Найменування;Сектор;Кількість;Полиця;Категорія;Опис;Штрихкод
AX-750;Вісь AL-KO 750кг без гальм;N1;15;Полиця 2;Вісі;Вісь для легкових причепів;200000001234
AX-1350;Вісь AL-KO 1350кг гальмівна;N2;8;Полиця 3;Вісі;З гальмами;200000001235
RS-3L;Ресора 3-листова 750кг;W1;25;Полиця 1;Підвіска;Для причепів до 750кг;200000001236
LED-12V;Ліхтар задній LED 12V;C1;50;Полиця 1;Освітлення;12V стоп-сигнал;200000001237"""
    
    return Response(
        template,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=template_import.csv'}
    )

@app.route('/api/export/all')
def export_all_items():
    """Експорт всіх товарів в Excel"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            i.article as 'Артикул',
            i.name as 'Найменування',
            i.category as 'Категорія',
            s.name as 'Стелаж',
            l.shelf as 'Полиця',
            l.quantity as 'Кількість',
            i.barcode as 'Штрихкод',
            i.description as 'Опис'
        FROM items i
        JOIN locations l ON i.id = l.item_id
        JOIN sectors s ON l.sector_id = s.id
        ORDER BY s.name, l.shelf
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Товари')
    
    output.seek(0)
    
    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=товари_експорт.xlsx'}
    )

@app.route('/api/export/report')
def export_report():
    """Експорт звіту по складу"""
    conn = sqlite3.connect(DB_PATH)
    
    stats = get_warehouse_stats()
    
    # Детальний звіт
    df_details = pd.read_sql_query("""
        SELECT 
            s.name as 'Стелаж',
            s.zone as 'Зона',
            l.shelf as 'Полиця',
            i.article as 'Артикул',
            i.name as 'Найменування',
            i.category as 'Категорія',
            l.quantity as 'Кількість',
            i.barcode as 'Штрихкод'
        FROM items i
        JOIN locations l ON i.id = l.item_id
        JOIN sectors s ON l.sector_id = s.id
        ORDER BY s.zone, s.name, l.shelf, i.name
    """, conn)
    
    conn.close()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Загальна інформація
        summary = pd.DataFrame({
            'Показник': ['Всього товарів', 'Всього одиниць', 'Активних стелажів', 'Дата звіту'],
            'Значення': [stats['total_items'], stats['total_quantity'], 
                        stats['active_sectors'], datetime.now().strftime('%d.%m.%Y %H:%M')]
        })
        summary.to_excel(writer, index=False, sheet_name='Загальна статистика')
        
        # По категоріях
        if stats['categories']:
            df_cats = pd.DataFrame(stats['categories'])
            df_cats.to_excel(writer, index=False, sheet_name='Категорії')
        
        # Детальний звіт
        df_details.to_excel(writer, index=False, sheet_name='Детальний звіт')
    
    output.seek(0)
    
    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=звіт_склад.xlsx'}
    )

# ==========================================
# 1С ПІДКЛЮЧЕННЯ
# ==========================================

@app.route('/api/1c/test', methods=['POST'])
def test_1c_connection():
    """Тест підключення до 1С"""
    config = request.json
    
    try:
        if config['mode'] == 'com':
            # Windows COM підключення
            try:
                v83 = win32com.client.Dispatch("V83.COMConnector")
                
                if config.get('connectionString'):
                    conn = v83.Connect(config['connectionString'])
                else:
                    conn = win32com.client.Dispatch("V83.Application")
                    conn.Connect("")
                
                # Тестовий запит
                query = conn.NewObject("Query", "SELECT TOP 1 * FROM Справочник.Номенклатура")
                result = query.Execute().Unload()
                
                return jsonify({
                    'success': True,
                    'goodsCount': result.Count() if hasattr(result, 'Count') else 'unknown'
                })
                
            except ImportError:
                return jsonify({
                    'success': False,
                    'error': 'win32com не встановлено. Використовуйте "pip install pywin32"'
                }), 500
                
        elif config['mode'] == 'file':
            # Перевірка файлу
            path = config.get('filePath', '')
            if not os.path.exists(path):
                return jsonify({
                    'success': False,
                    'error': f'Файл не знайдено: {path}'
                }), 404
            
            # Читаємо перші рядки
            if path.endswith('.xlsx'):
                df = pd.read_excel(path, nrows=5)
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()[:500]
            
            return jsonify({
                'success': True,
                'goodsCount': 'unknown (file accessible)'
            })
            
        elif config['mode'] == 'api':
            # OData API
            try:
                auth = (config['login'], config['password']) if config.get('login') else None
                test_url = f"{config['url']}/Catalog_Номенклатура?$top=1"
                
                resp = requests.get(test_url, auth=auth, timeout=10)
                
                if resp.status_code == 200:
                    return jsonify({
                        'success': True,
                        'goodsCount': 'unknown (API accessible)'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'HTTP {resp.status_code}: {resp.text[:200]}'
                    }), 502
                    
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        else:
            return jsonify({'error': 'Невідомий режим'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/1c/sync', methods=['POST'])
def sync_from_1c():
    """Синхронізація даних з 1С"""
    config = request.json
    
    try:
        goods = []
        
        if config['mode'] == 'com':
            # COM підключення
            v83 = win32com.client.Dispatch("V83.COMConnector")
            
            if config.get('connectionString'):
                conn = v83.Connect(config['connectionString'])
            else:
                conn = win32com.client.Dispatch("V83.Application")
                conn.Connect("")
            
            # Запит залишків
            query_text = """
                SELECT
                    Товары.Артикул as Article,
                    Товары.Наименование as Name,
                    Товары.Штрихкод as Barcode,
                    Товары.ВидНоменклатуры.Наименование as Category,
                    Регистр.КоличествоОстаток as Quantity
                FROM
                    РегистрНакопления.ТоварыНаСкладах.Остатки(,) as Регистр
                    ЛЕВОЕ СОЕДИНЕНИЕ Справочник.Номенклатура as Товары
                    ПО Регистр.Номенклатура = Товары.Ссылка
                WHERE
                    Регистр.КоличествоОстаток > 0
            """
            
            query = conn.NewObject("Query", query_text)
            result = query.Execute().Unload()
            
            for row in result:
                goods.append({
                    'article': row.Article,
                    'name': row.Name,
                    'barcode': row.Barcode,
                    'category': row.Category,
                    'quantity': int(row.Quantity)
                })
                
        elif config['mode'] == 'file':
            # Імпорт з файлу
            path = config['filePath']
            
            if path.endswith('.xlsx'):
                df = pd.read_excel(path)
            elif path.endswith('.csv'):
                df = pd.read_csv(path, encoding='utf-8')
            elif path.endswith('.xml'):
                df = pd.read_xml(path)
            else:
                return jsonify({'error': 'Непідтримуваний формат файлу'}), 400
            
            # Маппінг колонок
            goods = process_dataframe(df)
            
        elif config['mode'] == 'api':
            # OData API
            auth = (config['login'], config['password']) if config.get('login') else None
            url = f"{config['url']}/Catalog_Номенклатура?$format=json"
            
            resp = requests.get(url, auth=auth, timeout=30)
            data = resp.json()
            
            for item in data.get('value', []):
                goods.append({
                    'article': item.get('Артикул', item.get('Code', '')),
                    'name': item.get('Наименование', item.get('Description', '')),
                    'barcode': item.get('Штрихкод', ''),
                    'category': '',
                    'quantity': 0  # Потрібен окремий запит до регістру
                })
        
        # Зберігаємо в БД
        conn = get_db()
        imported = 0
        
        for item in goods:
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO items 
                    (article, name, barcode, category, quantity, source, updated_at, sector_id, shelf)
                    VALUES (?, ?, ?, ?, ?, '1C', ?, 'C1', 'Полиця 1')
                ''', (
                    item['article'], item['name'], item.get('barcode', ''),
                    item.get('category', ''), item.get('quantity', 0),
                    datetime.now().isoformat()
                ))
                imported += 1
            except Exception as e:
                print(f'Помилка імпорту {item}: {e}')
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'imported': imported,
            'total': len(goods)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
# EXCEL / GOOGLE SHEETS
# ==========================================

@app.route('/api/connect-excel', methods=['POST'])
def connect_excel():
    """Підключення до Excel/Google Sheets"""
    config = request.json
    
    try:
        df = None
        
        if config['type'] == 'google':
            # Google Sheets (публічний CSV експорт)
            url = config['url']
            
            # Конвертуємо URL в CSV експорт
            if '/edit' in url:
                sheet_id = url.split('/d/')[1].split('/')[0]
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                if config.get('sheet'):
                    csv_url += f"&gid={config['sheet']}"
            else:
                csv_url = url
            
            df = pd.read_csv(csv_url)
            
        elif config['type'] == 'excel-online':
            # Excel Online (потрібен спеціальний обробник)
            return jsonify({
                'error': 'Excel Online потребує Microsoft Graph API. Використовуйте пряме посилання на файл.'
            }), 501
            
        elif config['type'] == 'direct':
            # Пряме посилання на файл
            response = requests.get(config['url'], timeout=30)
            
            if config['url'].endswith('.csv'):
                from io import StringIO
                df = pd.read_csv(StringIO(response.text))
            else:
                from io import BytesIO
                df = pd.read_excel(BytesIO(response.content))
                
        elif config['type'] == 'local':
            # Локальна мережа - сервер має мати доступ
            if os.path.exists(config['url']):
                if config['url'].endswith('.csv'):
                    df = pd.read_csv(config['url'])
                else:
                    df = pd.read_excel(config['url'])
            else:
                return jsonify({'error': 'Шлях недоступний з сервера'}), 404
        
        if df is None:
            return jsonify({'error': 'Не вдалося прочитати дані'}), 400
        
        # Обробляємо дані
        goods = process_dataframe(df)
        
        # Зберігаємо
        conn = get_db()
        imported = 0
        
        for item in goods:
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO items 
                    (article, name, barcode, category, quantity, source, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'EXCEL', ?)
                ''', (
                    item['article'], item['name'], item.get('barcode', ''),
                    item.get('category', ''), item.get('quantity', 0),
                    datetime.now().isoformat()
                ))
                imported += 1
            except Exception as e:
                print(f'Помилка: {e}')
        
        conn.commit()
        
        # Зберігаємо конфіг для автооновлення
        # (в реальності потрібен планувальник)
        
        return jsonify({
            'success': True,
            'imported': imported,
            'columns': list(df.columns)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def process_dataframe(df):
    """Обробка DataFrame - автовизначення колонок"""
    columns = [str(c).lower() for c in df.columns]
    
    # Шукаємо колонки
    article_col = None
    name_col = None
    qty_col = None
    barcode_col = None
    category_col = None
    
    for i, col in enumerate(columns):
        if any(k in col for k in ['артикул', 'код', 'article', 'sku', 'код товару']):
            article_col = df.columns[i]
        elif any(k in col for k in ['назва', 'номенклатура', 'name', 'товар', 'опис']):
            name_col = df.columns[i]
        elif any(k in col for k in ['кількість', 'количество', 'quantity', 'остаток', 'залишок']):
            qty_col = df.columns[i]
        elif any(k in col for k in ['штрихкод', 'barcode', 'ean']):
            barcode_col = df.columns[i]
        elif any(k in col for k in ['категорія', 'група', 'вид', 'category']):
            category_col = df.columns[i]
    
    goods = []
    
    for _, row in df.iterrows():
        try:
            article = str(row[article_col]).strip() if article_col else ''
            name = str(row[name_col]).strip() if name_col else ''
            
            if not article or not name or article == 'nan':
                continue
            
            qty = 0
            if qty_col:
                try:
                    qty = int(float(row[qty_col]))
                except:
                    qty = 0
            
            goods.append({
                'article': article,
                'name': name,
                'quantity': qty,
                'barcode': str(row[barcode_col]).strip() if barcode_col else '',
                'category': str(row[category_col]).strip() if category_col else ''
            })
        except Exception as e:
            continue
    
    return goods


# ==========================================
# ВІДСТЕЖЕННЯ ПАПКИ (FILE WATCHER)
# ==========================================

file_watcher_thread = None

@app.route('/api/watch-folder', methods=['POST'])
def start_folder_watcher():
    """Запуск відстеження папки"""
    config = request.json
    
    global file_watcher_thread
    
    def watch_folder():
        path = config['path']
        pattern = config['pattern']
        interval = config['interval']
        
        processed_files = set()
        
        while True:
            try:
                # Шукаємо файли
                search_path = os.path.join(path, pattern)
                files = glob.glob(search_path)
                
                for file_path in files:
                    if file_path in processed_files:
                        continue
                    
                    print(f'📁 Знайдено новий файл: {file_path}')
                    
                    try:
                        # Імпортуємо
                        if file_path.endswith('.xlsx'):
                            df = pd.read_excel(file_path)
                        elif file_path.endswith('.csv'):
                            df = pd.read_csv(file_path, encoding='utf-8')
                        else:
                            continue
                        
                        goods = process_dataframe(df)
                        
                        # Зберігаємо в БД
                        conn = get_db()
                        for item in goods:
                            conn.execute('''
                                INSERT OR REPLACE INTO items 
                                (article, name, quantity, source, updated_at)
                                VALUES (?, ?, ?, 'AUTO_IMPORT', ?)
                            ''', (item['article'], item['name'], item['quantity'],
                                  datetime.now().isoformat()))
                        conn.commit()
                        
                        print(f'✅ Імпортовано {len(goods)} товарів з {file_path}')
                        
                        # Обробляємо файл після імпорту
                        if config['deleteAfter'] == 'yes':
                            os.remove(file_path)
                            print(f'🗑️ Видалено {file_path}')
                        elif config['deleteAfter'] == 'move':
                            imported_dir = os.path.join(path, 'Imported')
                            os.makedirs(imported_dir, exist_ok=True)
                            new_path = os.path.join(imported_dir, os.path.basename(file_path))
                            os.rename(file_path, new_path)
                            print(f'📦 Переміщено в {new_path}')
                        
                        processed_files.add(file_path)
                        
                    except Exception as e:
                        print(f'❌ Помилка обробки {file_path}: {e}')
                
                time.sleep(interval)
                
            except Exception as e:
                print(f'❌ Помилка відстеження: {e}')
                time.sleep(interval)
    
    # Запускаємо в окремому потоці
    if file_watcher_thread is None or not file_watcher_thread.is_alive():
        file_watcher_thread = Thread(target=watch_folder, daemon=True)
        file_watcher_thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Відстеження запущено: {config["path"]}'
    })

@app.route('/api/stats')
def api_stats():
    """Отримати статистику складу"""
    return jsonify(get_warehouse_stats())

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Додайте цей новий ендпоінт в кінець файлу app.py перед if __name__ == '__main__'

@app.route('/api/sync', methods=['POST'])
def api_sync():
    """Синхронізація операцій з офлайн режиму"""
    try:
        data = request.json
        operations = data.get('operations', [])
        
        if not operations:
            return jsonify({
                'success': True, 
                'processed': 0, 
                'message': 'Немає операцій для синхронізації'
            })
        
        processed = 0
        errors = []
        
        for op in operations:
            try:
                # Знаходимо товар за артикулом
                article = op.get('itemArticle') or op.get('article')
                item = get_item_by_article(article)
                
                if not item:
                    errors.append(f'Товар з артикулом {article} не знайдено')
                    continue
                
                item_id = item['id']
                
                # Оновлюємо кількість
                if op.get('type') in ['take', 'add', 'correction']:
                    # Знаходимо поточне розташування
                    current_locations = get_item_locations(item_id)
                    
                    # Шукаємо конкретне розташування
                    target_location = None
                    sector_id = op.get('sector_id')
                    shelf = op.get('shelf')
                    
                    for loc in current_locations:
                        if loc.get('sector_id') == sector_id and loc.get('shelf') == shelf:
                            target_location = loc
                            break
                    
                    if target_location:
                        # Оновлюємо існуюче
                        new_qty = max(0, target_location['quantity'] + op.get('delta', 0))
                        update_item_quantity(item_id, sector_id, shelf, new_qty)
                    else:
                        # Створюємо нове розташування
                        new_qty = max(0, op.get('newQuantity', 0) or op.get('delta', 0))
                        add_location(item_id, sector_id, new_qty, shelf)
                
                elif op.get('type') == 'move':
                    # Переміщення товару
                    if 'newSector' in op and 'newShelf' in op:
                        # Зменшуємо на старому місці
                        old_sector = op.get('oldSector')
                        old_shelf = op.get('oldShelf')
                        if old_sector and old_shelf:
                            update_item_quantity(item_id, old_sector, old_shelf, 0)
                        
                        # Додаємо на новому
                        new_sector = op.get('newSector')
                        new_shelf = op.get('newShelf')
                        quantity = op.get('oldQuantity', op.get('quantity', 0))
                        add_location(item_id, new_sector, quantity, new_shelf)
                
                # Записуємо в історію (якщо потрібно)
                if has_movements_table():
                    record_movement(
                        item_id,
                        op.get('oldSector'),
                        op.get('newSector') or op.get('sector_id'),
                        op.get('oldShelf'),
                        op.get('newShelf') or op.get('shelf'),
                        op.get('delta', 0),
                        op.get('worker', 'Система'),
                        op.get('type', 'unknown')
                    )
                
                processed += 1
                
            except Exception as e:
                errors.append(f'Помилка обробки операції: {str(e)}')
        
        return jsonify({
            'success': True,
            'processed': processed,
            'errors': errors,
            'message': f'Оброблено {processed} операцій'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def has_movements_table():
    """Перевіряє чи існує таблиця movements"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movements'")
    result = c.fetchone() is not None
    conn.close()
    return result


def record_movement(item_id, from_sector, to_sector, from_shelf, to_shelf, quantity, user, comment):
    """Запис переміщення в історію (якщо таблиця існує)"""
    if not has_movements_table():
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO movements (item_id, from_sector, to_sector, from_shelf, to_shelf, quantity, user, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (item_id, from_sector, to_sector, from_shelf, to_shelf, quantity, user, comment))
    
    conn.commit()
    conn.close()


@app.route('/api/test', methods=['GET'])
def api_test():
    """Тестовий ендпоінт для перевірки з'єднання"""
    from datetime import datetime
    return jsonify({
        'status': 'ok',
        'message': 'Сервер працює',
        'timestamp': datetime.now().isoformat(),
        'database': DB_PATH
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')