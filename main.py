import asyncio
import os
import re
from datetime import datetime
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from api_client import ApiClient
from parsers import (
    parse_category_pages,
    extract_product_ids,
    fetch_product_details,
    fetch_all_product_mains,
    fetch_all_comments,
    extract_images,
    extract_characteristics,
    clean_description
)
from data_writer import DataWriter
from logger import logger
from config import LINKS_FILE

async def process_category(client: ApiClient, category_url: str, category_name: str):
    base_url = category_url.strip().rstrip('/') + '/'
    logger.info(f"Обробка категорії: {category_name} ({base_url})")
    
    pages = await parse_category_pages(client, base_url)
    product_ids = await extract_product_ids(client, base_url, pages)
    
    if not product_ids:
        logger.warning(f"Не знайдено товарів для {category_name}")
        return [], []
    
    details = await fetch_product_details(client, product_ids)
    mains = await fetch_all_product_mains(client, product_ids)
    
    products_data = []
    images_data = []
    
    for pid, main_data in zip(product_ids, mains):
        detail = details.get(pid, {})
        
        logger.info(f"Обробка товару {pid}...")
        
        comments_data = await fetch_all_comments(client, pid)
        total_comments_raw = (comments_data.get('data') or {}).get('total_comments', {})
        total_comments = total_comments_raw if isinstance(total_comments_raw, dict) else {}
        comments_list = (comments_data.get('data') or {}).get('comments', [])
        
        href = detail.get('href', f'https://rozetka.com.ua/ua/p{pid}/')
        product_title = main_data.get('title', detail.get('title', 'Н/Д'))
        
        price_str = str(main_data.get('price', detail.get('price', 0)))
        old_price_str = str(main_data.get('old_price', detail.get('old_price', 0)))
        
        try:
            price_val = float(re.sub(r'[^\d.]', '', price_str)) if price_str != '0' else 0
            old_price_val = float(re.sub(r'[^\d.]', '', old_price_str)) if old_price_str != '0' else 0
        except:
            price_val = 0
            old_price_val = 0
        
        discount = 'Так' if (old_price_val > 0 and price_val > 0 and old_price_val > price_val) else 'Ні'
        sell_status = (main_data.get('product') or {}).get('sell_status', 'Н/Д')
        
        product = {
            'id': pid,
            'href': href,
            'brand': main_data.get('brand_name', detail.get('brand', 'Н/Д')),
            'price': f"{price_val} ₴" if price_val > 0 else 'Н/Д',
            'old_price': f"{old_price_val} ₴" if old_price_val > 0 else 'Н/Д',
            'discount': discount,
            'sell_status': sell_status,
            'category_title': (main_data.get('last_category') or {}).get('title', 'Н/Д'),
            'description': clean_description((main_data.get('description') or {}).get('text', '')),
            'characteristics': extract_characteristics(main_data),
            'comment_count': total_comments.get('comment_count_comments', 0),
            'avg_rating': total_comments.get('comment_avg_marks', 0),
            'marks_1': total_comments.get('comment_count_marks_1', 0),
            'marks_2': total_comments.get('comment_count_marks_2', 0),
            'marks_3': total_comments.get('comment_count_marks_3', 0),
            'marks_4': total_comments.get('comment_count_marks_4', 0),
            'marks_5': total_comments.get('comment_count_marks_5', 0),
            'comments': []
        }
        
        for comment in comments_list:
            created = comment.get('created', {})
            product['comments'].append({
                'user': comment.get('usertitle', 'Анонім'),
                'mark': comment.get('mark', 'Н/Д'),
                'text': comment.get('text', ''),
                'date': DataWriter.format_date(created)
            })
        
        products_data.append(product)
        
        images = extract_images(main_data)
        if images:
            images_data.append({
                'product_title': product_title,
                'product_url': href,
                'images': images
            })
    
    return products_data, images_data

def load_categories_from_file():
    if not os.path.exists(LINKS_FILE):
        logger.error(f"Файл {LINKS_FILE} не знайдено!")
        return []
    
    categories = []
    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '|' in line:
                parts = line.split('|', 1)
                url = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else f"Категорія {line_num}"
            else:
                url = line
                name = f"Категорія {line_num}"
            
            categories.append((url, name))
    
    logger.info(f"Завантажено {len(categories)} категорій з {LINKS_FILE}")
    return categories

async def run_parser():
    logger.info(f"=== Запуск парсера о {datetime.now().strftime('%H:%M:%S')} ===")
    
    categories = load_categories_from_file()
    
    if not categories:
        logger.error("Не знайдено категорій для парсингу!")
        return
    
    logger.info(f"Початок парсингу {len(categories)} категорій...")
    
    async with ApiClient() as client:
        all_products = []
        all_images = []
        
        for category_url, category_name in categories:
            products, images = await process_category(client, category_url, category_name)
            all_products.extend(products)
            all_images.extend(images)
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = f'ready_{timestamp}.csv'
        
        DataWriter.write_product_data(all_products, output_file)
        DataWriter.write_images_data(all_images)
    
    logger.info(f"Парсинг завершено! Оброблено {len(all_products)} товарів з {len(categories)} категорій")

async def main():
    print("Парсер\n")
    print("1. Запустити парсер зараз")
    print("2. Налаштувати автоматичний запуск за розкладом")
    
    choice = input("\nВиберіть опцію (1 або 2): ").strip()
    
    if choice == '1':
        await run_parser()
    
    elif choice == '2':
        print("\nОберіть періодичність:")
        print("1. Щоденно")
        print("2. Щотижнево")
        print("3. Щомісячно")
        
        period_choice = input("\nВиберіть періодичність (1, 2 або 3): ").strip()
        
        scheduler = AsyncIOScheduler()
        
        if period_choice == '1':
            print("\nВведіть час у форматі ГГ:ХХ (наприклад, 14:30)")
            time_input = input("Час запуску: ").strip()
            
            try:
                hour, minute = map(int, time_input.split(':'))
                
                scheduler.add_job(
                    run_parser,
                    CronTrigger(hour=hour, minute=minute),
                    id='rozetka_parser',
                    name='Rozetka Parser Daily'
                )
                
                logger.info(f"Парсер налаштовано на щоденний запуск о {hour:02d}:{minute:02d}")
                print(f"\n✓ Парсер буде запускатися щодня о {hour:02d}:{minute:02d}")
            except ValueError:
                logger.error("Невірний формат часу! Використовуйте ГГ:ХХ")
                return
        
        elif period_choice == '2':
            print("\nОберіть день тижня:")
            print("0 - Понеділок, 1 - Вівторок, 2 - Середа, 3 - Четвер")
            print("4 - П'ятниця, 5 - Субота, 6 - Неділя")
            day_of_week = int(input("День тижня (0-6): ").strip())
            
            print("\nВведіть час у форматі ГГ:ХХ (наприклад, 14:30)")
            time_input = input("Час запуску: ").strip()
            
            try:
                hour, minute = map(int, time_input.split(':'))
                
                scheduler.add_job(
                    run_parser,
                    CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
                    id='rozetka_parser',
                    name='Rozetka Parser Weekly'
                )
                
                days = ['понеділок', 'вівторок', 'середу', 'четвер', "п'ятницю", 'суботу', 'неділю']
                logger.info(f"Парсер налаштовано на щотижневий запуск у {days[day_of_week]} о {hour:02d}:{minute:02d}")
                print(f"\n✓ Парсер буде запускатися щотижня у {days[day_of_week]} о {hour:02d}:{minute:02d}")
            except ValueError:
                logger.error("Невірний формат!")
                return
        
        elif period_choice == '3':
            print("\nВведіть день місяця (1-31)")
            day = int(input("День місяця: ").strip())
            
            print("\nВведіть час у форматі ГГ:ХХ (наприклад, 14:30)")
            time_input = input("Час запуску: ").strip()
            
            try:
                hour, minute = map(int, time_input.split(':'))
                
                scheduler.add_job(
                    run_parser,
                    CronTrigger(day=day, hour=hour, minute=minute),
                    id='rozetka_parser',
                    name='Rozetka Parser Monthly'
                )
                
                logger.info(f"Парсер налаштовано на щомісячний запуск {day} числа о {hour:02d}:{minute:02d}")
                print(f"\n✓ Парсер буде запускатися щомісяця {day} числа о {hour:02d}:{minute:02d}")
            except ValueError:
                logger.error("Невірний формат!")
                return
        else:
            print("Невірний вибір!")
            return
        
        scheduler.start()
        print("Натисніть Ctrl+C для зупинки\n")
        
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Зупинка планувальника...")
            scheduler.shutdown()
    
    else:
        print("Невірний вибір!")

if __name__ == '__main__':
    asyncio.run(main())