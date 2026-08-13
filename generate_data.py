import pandas as pd
import random
import os
from collections import defaultdict

os.makedirs('data', exist_ok=True)

# ==========================================
# КОНФІГУРАЦІЯ СТЕЛАЖІВ ЗГІДНО 3D-МАПИ
# ==========================================
RACKS = [
    # Північна зона - 7 стелажів (суцільний ряд 11м)
    {'id': 'N1', 'name': 'П1', 'zone': 'north', 'shelves': 6},
    {'id': 'N2', 'name': 'П2', 'zone': 'north', 'shelves': 6},
    {'id': 'N3', 'name': 'П3', 'zone': 'north', 'shelves': 6},
    {'id': 'N4', 'name': 'П4', 'zone': 'north', 'shelves': 6},
    {'id': 'N5', 'name': 'П5', 'zone': 'north', 'shelves': 6},
    {'id': 'N6', 'name': 'П6', 'zone': 'north', 'shelves': 6},
    {'id': 'N7', 'name': 'П7', 'zone': 'north', 'shelves': 6},
    
    # Західна зона
    {'id': 'W1', 'name': 'З1', 'zone': 'west', 'shelves': 6},
    {'id': 'W2', 'name': 'З2', 'zone': 'west', 'shelves': 5},
    {'id': 'W3', 'name': 'З3', 'zone': 'west', 'shelves': 4},
    {'id': 'W4', 'name': 'З4', 'zone': 'west', 'shelves': 4},
    
    # Центральна зона - 5 стелажів
    {'id': 'C1', 'name': 'Ц1', 'zone': 'center', 'shelves': 6},
    {'id': 'C2', 'name': 'Ц2', 'zone': 'center', 'shelves': 6},
    {'id': 'C3', 'name': 'Ц3', 'zone': 'center', 'shelves': 6},
    {'id': 'C4', 'name': 'Ц4', 'zone': 'center', 'shelves': 6},
    {'id': 'C5', 'name': 'Ц5', 'zone': 'center', 'shelves': 6},
    
    # Східна зона
    {'id': 'E1', 'name': 'С1', 'zone': 'east', 'shelves': 5},
    {'id': 'E2', 'name': 'С2', 'zone': 'east', 'shelves': 5},
    {'id': 'E3', 'name': 'С3', 'zone': 'east', 'shelves': 4},
]

# Категорії товарів з відповідними стелажами (розширено)
categories = {
    'Вісі': ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'C1', 'C2'],
    'Підвіска': ['N1', 'N2', 'N3', 'N4', 'N5', 'C1', 'C2', 'C3'],
    'Електрика': ['C1', 'C2', 'C3', 'C4', 'C5', 'E1', 'E2'],
    'Освітлення': ['C1', 'C2', 'C3', 'E1', 'E2'],
    'Фурнітура': ['C3', 'C4', 'C5', 'W1', 'W2', 'W3', 'E1', 'E2', 'E3'],
    'Тенти': ['C4', 'C5', 'W1', 'W2', 'E2', 'E3'],
    'Гальма': ['N1', 'N2', 'N3', 'N4', 'C1', 'C2', 'W1', 'W2'],
    'Колеса': ['W1', 'W2', 'W3', 'W4', 'E1', 'E2', 'E3', 'N5', 'N6', 'N7'],
    'Загальне': ['W1', 'W2', 'W3', 'W4', 'C1', 'C2', 'C3', 'C4', 'C5', 'E1', 'E2', 'E3', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7'],
    'Гідравліка': ['C1', 'C2', 'C3', 'N1', 'N2', 'N3'],
    'Кріплення': ['W1', 'W2', 'W3', 'W4', 'C3', 'C4', 'C5', 'E1', 'E2'],
    'Інструменти': ['W3', 'W4', 'E3', 'C5', 'N7'],
    'Електроніка': ['C1', 'C2', 'C3', 'E1', 'E2'],
    'Причепи': ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7'],
    'Запчастини': ['C1', 'C2', 'C3', 'C4', 'C5', 'W1', 'W2', 'E1', 'E2'],
}

# Розширені шаблони назв
templates = {
    'Вісь': ['Вісь AL-KO {}кг', 'Вісь Knott {}кг', 'Вісь BPW {}кг', 'Вісь SMB {}кг', 'Вісь підсилена {}кг'],
    'Ресора': ['Ресора {}-листова {}кг', 'Ресора підсилена {}кг', 'Ресора параболічна {}кг'],
    'Амортизатор': ['Амортизатор гідравлічний {}кг', 'Амортизатор газовий {}кг', 'Амортизатор двосторонній {}кг'],
    'Ліхтар': ['Ліхтар задній LED {}', 'Ліхтар габаритний {}', 'Ліхтар стоп-сигнал {}', 'Ліхтар повороту {}', 'Ліхтар протитуманний {}'],
    'Кабель': ['Кабель {}-контактний {}м', 'Кабель електричний {}мм² {}м', 'Кабель з\'єднувальний {}м'],
    'Замок': ['Замок накладний {}мм', 'Замок врізний {}мм', 'Замок бортовий {}мм', 'Замок люка {}мм'],
    'Петля': ['Петля дверна {}мм', 'Петля люка {}мм', 'Петля борту {}мм', 'Петля посилена {}мм'],
    'Ручка': ['Ручка вантажна {}кг', 'Ручка борту {}мм', 'Ручка дверна {}мм', 'Ручка люка {}мм'],
    'Тент': ['Тент ПВХ {}м', 'Тент тканинний {}м', 'Тент силіконовий {}м', 'Тент брезентовий {}м'],
    'Каркас': ['Каркас тента {}м', 'Каркас даху {}м', 'Каркас борту {}м', 'Дуга тента {}м'],
    'Диск': ['Диск колісний {}x{}', 'Диск сталевий {}x{}', 'Диск литий {}x{}', 'Дикс штампований {}x{}'],
    'Шина': ['Шина причепна {}R{}', 'Шина вантажна {}R{}', 'Шина всесезонна {}R{}', 'Шина зимова {}R{}'],
    'Колодка': ['Колодка гальмівна {}мм', 'Колодка дискова {}мм', 'Колодка стоянкова {}мм'],
    'Циліндр': ['Циліндр гальмівний {}мм', 'Циліндр зчеплення {}мм', 'Циліндр головний {}мм', 'Циліндр робочий {}мм'],
    'Підшипник': ['Підшипник маточини {}', 'Підшипник ступиці {}', 'Підшипник конічний {}', 'Підшипник кульковий {}'],
    'Сальник': ['Сальник маточини {}x{}', 'Сальник редуктора {}x{}', 'Сальник вала {}x{}'],
    'Манжет': ['Манжет гальмівний {}мм', 'Манжет циліндра {}мм', 'Манжет пильовик {}мм'],
    'Шкворень': ['Шкворень поворотний {}мм', 'Шкворень ресори {}мм', 'Шкворень комплект {}мм'],
    'Втулка': ['Втулка ресори {}мм', 'Втулка стабілізатора {}мм', 'Втулка сайлентблок {}мм'],
    'Болт': ['Болт М{}x{}', 'Болт високоміцний М{}x{}', 'Болт колісний {}x{}'],
    'Гайка': ['Гайка М{}', 'Гайка самоконтряща М{}', 'Гайка колісна М{}'],
    'Шайба': ['Шайба {}мм', 'Шайба пружинна {}мм', 'Шайба стопорна {}мм'],
    'Домкрат': ['Домкрат гвинтовий {}т', 'Домкрат гідравлічний {}т', 'Домкрат ромбічний {}т'],
    'Трос': ['Трос буксирувальний {}т {}м', 'Трос зчіпний {}м', 'Трос страхувальний {}м'],
    'Фара': ['Фара головна {}', 'Фара протитуманна {}', 'Фара робоча LED {}', 'Фара габаритна {}'],
    'Рефлектор': ['Рефлектор задній {}', 'Рефлектор боковий {}', 'Рефлектор трикутний {}'],
    'Бризковик': ['Бризковик гумовий {}м', 'Бризковик пластиковий {}', 'Бризковик універсальний'],
    'Наконечник': ['Наконечник рульовий {}мм', 'Наконечник тяги {}мм', 'Наконечник троса {}мм'],
    'Кронштейн': ['Кронштейн фари {}', 'Кронштейн ресори {}', 'Кронштейн запаски {}'],
    'Фільтр': ['Фільтр масляний {}', 'Фільтр повітряний {}', 'Фільтр паливний {}'],
    'Насос': ['Насос гідравлічний {}', 'Насос паливний {}', 'Насос водяний {}'],
    'Радіатор': ['Радіатор охолодження {}', 'Радіатор опалення {}', 'Радіатор масляний {}'],
    'Вентилятор': ['Вентилятор охолодження {}"', 'Вентилятор радіатора {}"', 'Вентилятор витяжний {}"'],
    'Датчик': ['Датчик рівня палива {}', 'Датчик температури {}', 'Датчик тиску {}', 'Датчик ABS {}'],
    'Реле': ['Реле поворотів {}', 'Реле стартера {}', 'Реле бензонасоса {}'],
    'Провід': ['Провід високовольтний {}', 'Провід зварювальний {}мм²', 'Провід акумуляторний {}мм²'],
    'Клема': ['Клема акумуляторна {}', 'Клема маси {}', 'Клема з\'єднувальна {}'],
    'Ізоляція': ['Стрічка ізоляційна {}м', 'Термоусадка {}мм', 'Чохол захисний {}мм'],
}

# ==========================================
# ФУНКЦІЇ ГЕНЕРАЦІЇ
# ==========================================

def generate_article(cat, rack_id, shelf_num, idx):
    """Генерує артикул на основі категорії та розташування"""
    prefixes = {
        'Вісі': 'AX', 'Підвіска': 'RS', 'Електрика': 'EL', 'Освітлення': 'LED',
        'Фурнітура': 'FR', 'Тенти': 'TN', 'Гальма': 'BR', 'Колеса': 'WH',
        'Загальне': 'GN', 'Гідравліка': 'HY', 'Кріплення': 'MT', 'Інструменти': 'TL',
        'Електроніка': 'EC', 'Причепи': 'TR', 'Запчастини': 'PT'
    }
    prefix = prefixes.get(cat, 'XX')
    # Додаємо код стелажа до артикулу для кращої ідентифікації
    return f"{prefix}-{rack_id}{shelf_num}-{idx:04d}"

def generate_barcode(article):
    """Генерує штрихкод на основі артикулу"""
    # Беремо тільки цифри з артикулу
    digits = ''.join(filter(str.isdigit, article))
    if len(digits) < 9:
        digits = digits.zfill(9)
    base = "200" + digits[:9]
    # Простий checksum для EAN-13
    checksum = sum(int(base[i]) * (1 if i % 2 == 0 else 3) for i in range(12))
    check_digit = (10 - (checksum % 10)) % 10
    return base + str(check_digit)

def generate_name():
    """Генерує назву товару з шаблону"""
    cat = random.choice(list(templates.keys()))
    template = random.choice(templates[cat])
    
    try:
        if 'кг' in template and '{}' in template:
            val = random.choice([350, 500, 750, 1000, 1200, 1350, 1500, 1800, 2000, 2500, 3000, 3500])
            return template.format(val)
        elif 'м' in template and 'мм' not in template and '{}' in template:
            if '{}м' in template or '{}м' in template:
                val = random.choice([2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 10, 12, 15, 20])
                return template.format(val)
            else:
                val = random.choice([2, 3, 4, 5, 6, 7, 8, 10, 12])
                return template.format(val)
        elif 'мм' in template:
            if template.count('{}') == 2:
                val1 = random.choice([20, 25, 30, 35, 38, 40, 45, 50, 60, 80, 100, 120])
                val2 = random.choice([10, 15, 20, 25, 30, 40, 50, 60])
                return template.format(val1, val2)
            else:
                val = random.choice([20, 25, 30, 35, 38, 40, 45, 50, 60, 80, 100, 120, 150, 200])
                return template.format(val)
        elif 'контактний' in template:
            pins = random.choice([7, 13])
            length = random.choice([3, 4, 5, 6, 7, 8, 10, 12, 15])
            return template.format(pins, length)
        elif 'R' in template:
            width = random.choice([145, 155, 165, 175, 185, 195, 205, 215, 225, 235, 245, 255, 265])
            diameter = random.choice([13, 14, 15, 16, 17, 18, 19, 20, 22])
            return template.format(width, diameter)
        elif 'x' in template.lower():
            if '{}x{}' in template or '{}x' in template:
                val1 = random.choice([10, 12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36])
                val2 = random.choice([1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0])
                return template.format(val1, val2)
            else:
                val1 = random.randint(10, 200)
                val2 = random.randint(5, 100)
                return template.format(val1, val2)
        elif 'т' in template and '{}' in template:
            val = random.choice([1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 15])
            return template.format(val)
        else:
            return template.format(random.randint(10, 500))
    except:
        return template

def generate_description():
    """Генерує опис товару"""
    return random.choice([
        'Оригінальна якість', 'Аналог високої якості', 'Виробництво Польща',
        'Виробництво Німеччина', 'Виробництво Туреччина', 'Виробництво Україна',
        'Виробництво Китай', 'Сертифікований товар', 'Гарантія 12 місяців',
        'Гарантія 24 місяці', 'Оптова ціна', 'Роздрібна ціна',
        'Спеціальна пропозиція', 'Нове надходження', 'Хіт продажів',
        'Акційний товар', 'Обмежена кількість', 'Під замовлення',
        'В наявності', 'Останні одиниці', 'Популярний товар',
        'Рекомендуємо', 'Бестселер', 'Розпродаж', 'Уцінка'
    ])

# ==========================================
# ОСНОВНА ГЕНЕРАЦІЯ
# ==========================================

print("=" * 60)
print("ГЕНЕРАЦІЯ 5000+ ТОВАРІВ ДЛЯ ВСІХ СТЕЛАЖІВ ТА ПОЛИЦЬ")
print("=" * 60)

# Розраховуємо загальну кількість полиць
total_shelves = sum(rack['shelves'] for rack in RACKS)
print(f"📊 Всього стелажів: {len(RACKS)}")
print(f"📊 Всього полиць: {total_shelves}")
print(f"🎯 Ціль: 5000+ товарів (в середньому {5000/total_shelves:.1f} товарів на полицю)")
print("-" * 60)

data = []
item_counter = 1

# Розподіляємо товари по полицях рівномірно
items_per_shelf = {}
shelf_distribution = []

for rack in RACKS:
    for shelf_num in range(1, rack['shelves'] + 1):
        shelf_name = f"Полиця {shelf_num}"
        # Визначаємо скільки товарів буде на цій полиці (від 3 до 15)
        num_items = random.randint(4, 12)
        items_per_shelf[f"{rack['id']}-{shelf_name}"] = num_items
        shelf_distribution.append({
            'rack_id': rack['id'],
            'rack_name': rack['name'],
            'shelf': shelf_name,
            'shelf_num': shelf_num,
            'num_items': num_items
        })

# Коригуємо загальну кількість до 5000+
total_planned = sum(item['num_items'] for item in shelf_distribution)
print(f"📊 Заплановано товарів: {total_planned}")

if total_planned < 5000:
    # Додаємо додаткові товари на найбільш заповнені полиці
    additional_needed = 5000 - total_planned
    print(f"➕ Додаємо ще {additional_needed} товарів...")
    
    for i in range(additional_needed):
        shelf = random.choice(shelf_distribution)
        shelf['num_items'] += 1

# Перераховуємо
total_items = sum(item['num_items'] for item in shelf_distribution)
print(f"📊 Фінальна кількість: {total_items} товарів")
print("-" * 60)

# Генеруємо товари
progress_step = total_items // 20  # для прогрес-бару

for shelf_info in shelf_distribution:
    rack_id = shelf_info['rack_id']
    shelf_name = shelf_info['shelf']
    shelf_num = shelf_info['shelf_num']
    num_items = shelf_info['num_items']
    
    # Обираємо категорії, які можуть бути на цьому стелажі
    possible_categories = [cat for cat, racks in categories.items() if rack_id in racks]
    if not possible_categories:
        possible_categories = ['Загальне']
    
    for i in range(1, num_items + 1):
        category = random.choice(possible_categories)
        
        # Генеруємо артикул з урахуванням розташування
        article = generate_article(category, rack_id, shelf_num, item_counter)
        
        item = {
            'Артикул': article,
            'Найменування': generate_name(),
            'Сектор': rack_id,
            'Кількість': random.randint(1, 200),  # Від 1 до 200 шт
            'Полиця': shelf_name,
            'Категорія': category,
            'Опис': generate_description(),
            'Штрихкод': generate_barcode(article)
        }
        
        data.append(item)
        item_counter += 1
        
        if item_counter % progress_step == 0:
            progress = (item_counter / total_items) * 100
            print(f"⏳ Згенеровано {item_counter}/{total_items} ({progress:.1f}%)...")

# Створюємо DataFrame
df = pd.DataFrame(data)

print("-" * 60)
print("✅ ГЕНЕРАЦІЮ ЗАВЕРШЕНО!")
print(f"📦 Всього згенеровано: {len(df)} товарів")

# ==========================================
# СТАТИСТИКА ПО СТЕЛАЖАХ
# ==========================================

print("\n📊 СТАТИСТИКА ПО СТЕЛАЖАХ:")
print("-" * 60)
rack_stats = df.groupby('Сектор').agg({
    'Найменування': 'count',
    'Кількість': 'sum'
}).rename(columns={'Найменування': 'Товарів', 'Кількість': 'Одиниць'}).sort_values('Товарів', ascending=False)

for rack_id, row in rack_stats.iterrows():
    rack_info = next((r for r in RACKS if r['id'] == rack_id), None)
    if rack_info:
        name = rack_info['name']
        zone = rack_info['zone']
        zone_names = {'north': 'Північ', 'west': 'Захід', 'center': 'Центр', 'east': 'Схід'}
        zone_name = zone_names.get(zone, zone)
        print(f"  {name} ({rack_id}) [{zone_name}]: {row['Товарів']:3d} товарів, {row['Одиниць']:5d} одиниць")

print("-" * 60)

# ==========================================
# СТАТИСТИКА ПО КАТЕГОРІЯХ
# ==========================================

print("\n📊 СТАТИСТИКА ПО КАТЕГОРІЯХ:")
print("-" * 60)
cat_stats = df.groupby('Категорія').agg({
    'Найменування': 'count',
    'Кількість': 'sum'
}).rename(columns={'Найменування': 'Товарів', 'Кількість': 'Одиниць'}).sort_values('Товарів', ascending=False)

for category, row in cat_stats.iterrows():
    print(f"  {category:12s}: {row['Товарів']:3d} товарів, {row['Одиниць']:5d} одиниць")

print("-" * 60)

# ==========================================
# ПЕРЕВІРКА РОЗПОДІЛУ ПО ПОЛИЦЯХ
# ==========================================

print("\n📊 ПРИКЛАД РОЗПОДІЛУ ПО ПОЛИЦЯХ (перші 10 стелажів):")
print("-" * 60)

shelf_check = {}
for rack_id in ['N1', 'W1', 'C1', 'E1', 'N4', 'W3', 'C3', 'E3', 'N7', 'C5']:
    rack_data = df[df['Сектор'] == rack_id]
    shelf_counts = rack_data['Полиця'].value_counts().sort_index()
    if not shelf_counts.empty:
        print(f"\n  {rack_id}:")
        for shelf, count in shelf_counts.items():
            print(f"    {shelf}: {count} товарів")

# ==========================================
# КОНВЕРТАЦІЯ ID СТЕЛАЖІВ ДЛЯ СУМІСНОСТІ З 3D-МАПОЮ
# ==========================================

# Маппінг для сумісності зі старими ID (якщо потрібно)
legacy_mapping = {
    'L1': 'W1', 'L2': 'W2', 'BL1': 'W3',
    'R1': 'E1', 'R2': 'E2', 'R3': 'E3',
    'T1': 'C5', 'T2': 'C5', 'T3': 'C5', 'T4': 'C5'
}

# Додаємо колонку з legacy ID для сумісності
df['Сектор_Legacy'] = df['Сектор'].replace(legacy_mapping)
df['Зона'] = df['Сектор'].map(lambda x: next((r['zone'] for r in RACKS if r['id'] == x), 'unknown'))

# ==========================================
# ЗБЕРЕЖЕННЯ
# ==========================================

print("\n💾 ЗБЕРЕЖЕННЯ ФАЙЛІВ...")

# Excel
excel_path = 'data/товари_повні.xlsx'
df.to_excel(excel_path, index=False, engine='openpyxl')
print(f"  ✅ Excel: {excel_path}")

# CSV (UTF-8 з BOM для Excel)
csv_path = 'data/товари_повні.csv'
df.to_csv(csv_path, index=False, encoding='utf-8-sig', sep=';')
print(f"  ✅ CSV: {csv_path}")

# JSON для резервного копіювання
json_path = 'data/товари_повні.json'
df.to_json(json_path, orient='records', indent=2, force_ascii=False)
print(f"  ✅ JSON: {json_path}")

# Статистика по зонах
zone_stats = df.groupby('Зона').size().to_dict()
print(f"\n📊 Розподіл по зонах:")
for zone, count in zone_stats.items():
    zone_names = {'north': 'Північна', 'west': 'Західна', 'center': 'Центральна', 'east': 'Східна', 'unknown': 'Інше'}
    print(f"  {zone_names.get(zone, zone)}: {count} товарів")

print("\n" + "=" * 60)
print("✅ ГОТОВО! Файли збережено в папці 'data/'")
print("=" * 60)

# ==========================================
# ДОДАТКОВА ІНФОРМАЦІЯ
# ==========================================

print("\n📋 ІНСТРУКЦІЯ:")
print("  1. Файли готові для імпорту в 3D-систему")
print("  2. Всі товари розподілені по реальних стелажах та полицях")
print("  3. Кожен товар має унікальний артикул та штрихкод")
print("  4. Сумісність з 3D-мапою: так (ID стелажів N1-N7, W1-W4, C1-C5, E1-E3)")
print("  5. Для використання в index.html: скопіюйте CSV в ту ж папку")