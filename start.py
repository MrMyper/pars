import os
import xml.etree.ElementTree as ET
import requests
import csv
from datetime import datetime
import re

# Функция для скачивания XML файла и сохранения в папку "xmls"
def download_xml(url, folder="xmls"):
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"export_rozetka_{timestamp}.xml"
    file_path = os.path.join(folder, file_name)

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f'Ошибка при скачивании XML: {e}')
        return None

    with open(file_path, 'wb') as file:
        file.write(response.content)

    print(f'XML файл сохранен в: {file_path}')
    return file_path

# Округление
def round_to_nearest_ten(price):
    return round(price / 10) * 13  # менять процент наценки

# Извлечение артикула
def extract_article(name):
    match = re.search(r'ISSA PLUS ([A-ZА-Яa-zа-я0-9\-]+)', name)
    return match.group(1) if match else None

# Парсинг категорий и офферов
def parse_categories(root):
    categories = {}
    for category in root.findall('.//category'):
        category_id = category.attrib['id']
        category_name = category.text.strip() if category.text else 'Без названия'
        categories[category_id] = category_name
    return categories

# Парсинг офферов
def parse_offer(offer, categories):
    data = {}
    original_name = offer.find('name').text or ''
    article = extract_article(original_name) or 'Нет артикула'
    
    # Извлечение параметров "Розмір" и "Колір"
    size = None
    color = None
    params = offer.findall('param')
    for param in params:
        param_name = param.attrib['name']
        data[param_name] = param.text.strip() if param.text else 'Нет значения'
        
        if param_name == "Розмір":
            size = param.text.strip() if param.text else ''
        elif param_name == "Колір":
            color = param.text.strip() if param.text else ''

    # Модификация артикула с учетом размера и цвета
    if size and color:
        data['article'] = f'I{article}{size}{color}'  # Добавление размера и цвета
    else:
        data['article'] = f'I{article}'  # Резервный вариант, если размер или цвет не найдены
    
    price_text = offer.find('price').text
    data['dilerprice'] = price_text
    category_id = offer.find('categoryId').text
    data['category'] = categories.get(category_id, 'Unknown')
    data['dilerurl'] = offer.find('url').text or 'Нет URL'
    
    try:
        original_price = float(data['dilerprice'])
        price_with_markup = original_price * 1.2
        data['price'] = round_to_nearest_ten(price_with_markup)
    except (ValueError, TypeError):
        data['price'] = 'Некорректная цена'
    
    pictures = offer.findall('picture')
    data['pictures'] = ', '.join([pic.text for pic in pictures if pic.text]) or 'Нет изображений'
    
    return data

# Парсинг данных из XML
def parse_xml_data(xml_file_path):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    categories = parse_categories(root)
    offers = root.findall('.//offer')
    parsed_data = [parse_offer(offer, categories) for offer in offers]
    return parsed_data

# Сохранение данных в CSV с переименованными столбцами
def save_to_csv(data, folder):
    if data:
        base_headers = ['article', 'dilerprice', 'price', 'category', 'dilerurl']
        # Маппинг для переименования столбцов
        rename_mapping = {
            'Колір': 'color',
            'Розмір': 'size',
            'Состав': 'Compound',
            'Матеріал': 'Material',
            'pictures': 'Изображения'
        }
        
        # Переименование ключей в каждом элементе данных
        for item in data:
            for old_key, new_key in rename_mapping.items():
                if old_key in item:
                    item[new_key] = item.pop(old_key)
        
        all_keys = get_all_keys(data)
        additional_headers = [key for key in all_keys if key not in base_headers]
        headers = base_headers + additional_headers
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file_name = f'offers_data_{timestamp}.csv'
        csv_file_path = os.path.join(folder, csv_file_name)

        with open(csv_file_path, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=headers, delimiter=';')
            writer.writeheader()
            writer.writerows(data)

        print(f'Данные сохранены в {csv_file_path}')
    else:
        print('Нет данных для записи в CSV.')

# Получение всех ключей из данных
def get_all_keys(data):
    keys = set()
    for item in data:
        keys.update(item.keys())
    return keys

# Главная функция
def main():
    xml_url = 'https://issaplus.com/load/export_rozetka_ua.xml'
    xml_file_path = download_xml(xml_url)
    if xml_file_path:
        offers_data = parse_xml_data(xml_file_path)
        csv_folder = 'csv'
        os.makedirs(csv_folder, exist_ok=True)
        save_to_csv(offers_data, csv_folder)

if __name__ == '__main__':
    main()
