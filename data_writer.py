import csv
from typing import List, Dict
from datetime import datetime
from config import IMAGES_FILE
from logger import logger

class DataWriter:
    @staticmethod
    def format_date(created_data: Dict) -> str:
        day = created_data.get('day', '')
        month = created_data.get('month', '')
        year = created_data.get('year', '')
        return f"{day}.{month}.{year}" if all([day, month, year]) else ''
    
    @staticmethod
    def write_product_data(products: List[Dict], filename: str):
        logger.info(f"Записую дані {len(products)} товарів у {filename}...")
        
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            if not products:
                return
            
            fieldnames = [
                'ID', 'Посилання', 'Бренд', 'Ціна', 'Стара ціна', 'Знижка', 'Статус продажу',
                'Категорія', 'Опис', 'Кількість відгуків', 'Середня оцінка',
                'Оцінка 1★', 'Оцінка 2★', 'Оцінка 3★', 'Оцінка 4★', 'Оцінка 5★'
            ]
            
            max_chars = max(len(p.get('characteristics', [])) for p in products) if products else 0
            for i in range(max_chars):
                fieldnames.append(f'Характеристика_{i+1}_Назва')
                fieldnames.append(f'Характеристика_{i+1}_Значення')
            
            max_comments = max(len(p.get('comments', [])) for p in products) if products else 0
            for i in range(max_comments):
                fieldnames.append(f'Відгук_{i+1}_Користувач')
                fieldnames.append(f'Відгук_{i+1}_Оцінка')
                fieldnames.append(f'Відгук_{i+1}_Текст')
                fieldnames.append(f'Відгук_{i+1}_Дата')
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in products:
                row = {
                    'ID': product['id'],
                    'Посилання': product['href'],
                    'Бренд': product['brand'],
                    'Ціна': product['price'],
                    'Стара ціна': product['old_price'],
                    'Знижка': product['discount'],
                    'Статус продажу': product['sell_status'],
                    'Категорія': product['category_title'],
                    'Опис': product['description'],
                    'Кількість відгуків': product['comment_count'],
                    'Середня оцінка': product['avg_rating'],
                    'Оцінка 1★': product['marks_1'],
                    'Оцінка 2★': product['marks_2'],
                    'Оцінка 3★': product['marks_3'],
                    'Оцінка 4★': product['marks_4'],
                    'Оцінка 5★': product['marks_5']
                }
                
                for i, char in enumerate(product.get('characteristics', [])):
                    row[f'Характеристика_{i+1}_Назва'] = char['назва']
                    row[f'Характеристика_{i+1}_Значення'] = char['значення']
                
                for i, comment in enumerate(product.get('comments', [])):
                    row[f'Відгук_{i+1}_Користувач'] = comment['user']
                    row[f'Відгук_{i+1}_Оцінка'] = comment['mark']
                    row[f'Відгук_{i+1}_Текст'] = comment['text']
                    row[f'Відгук_{i+1}_Дата'] = comment['date']
                
                writer.writerow(row)
        
        logger.info(f"Дані збережено у {filename}")
    
    @staticmethod
    def write_images_data(images_data: List[Dict]):
        logger.info(f"Записую дані про зображення у {IMAGES_FILE}...")
        
        with open(IMAGES_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Назва товару', 'Посилання на товар', 'Зображення'])
            
            for item in images_data:
                product_title = item['product_title']
                product_url = item['product_url']
                for img_url in item['images']:
                    writer.writerow([product_title, product_url, img_url])
        
        logger.info(f"Дані про зображення збережено у {IMAGES_FILE}")