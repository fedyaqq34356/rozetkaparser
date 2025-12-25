import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import logging

logging.basicConfig(
    filename='parser.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    encoding='utf-8'
)

async def main():
    category_url = input("Enter category URL: ").strip().rstrip('/') + '/'
    logging.info(f"Started parsing category: {category_url}")
    
    connector = aiohttp.TCPConnector(limit=30)
    timeout = aiohttp.ClientTimeout(total=40)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers) as session:
        first_html = await fetch(session, category_url)
        total_pages = get_total_pages(first_html)
        logging.info(f"Detected total pages: {total_pages}")
        print(f"Detected {total_pages} pages in the category")
        
        page_urls = [category_url if p == 1 else f"{category_url}page={p}/" for p in range(1, total_pages + 1)]
        
        logging.info(f"Fetching {len(page_urls)} category pages")
        page_htmls = await asyncio.gather(*(fetch(session, url) for url in page_urls))
        
        all_ids = set()
        for i, html in enumerate(page_htmls):
            page_num = i + 1
            ids = extract_ids(html)
            all_ids.update(ids)
            logging.info(f"Page {page_num}: found {len(ids)} IDs")
            print(f"Page {page_num}: found {len(ids)} IDs")
        
        all_ids = sorted(all_ids)
        logging.info(f"Total unique IDs: {len(all_ids)}")
        print(f"Found {len(all_ids)} unique product IDs")
        
        details_base = 'https://common-api.rozetka.com.ua/v1/api/product/details?country=UA&lang=ua&ids='
        batch_size = 60
        details_urls = [details_base + ','.join(all_ids[i:i + batch_size]) for i in range(0, len(all_ids), batch_size)]
        
        details_jsons = await asyncio.gather(*(fetch_json(session, url) for url in details_urls))
        
        details_data = {}
        for js in details_jsons:
            for prod in js.get('data', []):
                pid = str(prod.get('id'))
                if pid:
                    details_data[pid] = prod
        
        main_base = 'https://common-api.rozetka.com.ua/v1/api/pages/product/main?country=UA&lang=ua&id='
        main_urls = [f"{main_base}{pid}&isGroup=false" for pid in all_ids]
        
        logging.info(f"Fetching {len(main_urls)} main product pages")
        main_jsons = await asyncio.gather(*(fetch_json(session, url) for url in main_urls))
        
        with open('ready.txt', 'w', encoding='utf-8') as f:
            for i, pid in enumerate(all_ids):
                d = details_data.get(pid, {})
                main_resp = main_jsons[i] if i < len(main_jsons) else {}
                main = main_resp.get('data', {}).get('productData', {})
                
                category = d.get('category', {})
                seller = d.get('seller', {})
                
                raw_desc = main.get('description', {}).get('text')
                if raw_desc:
                    soup_desc = BeautifulSoup(raw_desc, 'lxml')
                    description = soup_desc.get_text(separator=' ', strip=True)
                else:
                    description = 'Опис відсутній'
                
                f.write(f"ID: {pid}\n")
                f.write(f"Посилання: {d.get('href', f'https://rozetka.com.ua/ua/p{pid}/')}\n")
                f.write(f"Бренд: {d.get('brand', 'N/A')}\n")
                f.write(f"Ціна: {d.get('price', 'N/A')} ₴\n")
                f.write(f"Стара ціна: {d.get('old_price', 'N/A')} ₴\n")
                f.write(f"Відгуки: {d.get('comments_amount', 0)} (оцінка {d.get('comments_mark', 0)})\n")
                f.write(f"ID категорії: {category.get('id', 'N/A')}\n")
                f.write(f"Посилання категорії: {category.get('href', 'N/A')}\n")
                f.write(f"Назва категорії: {category.get('title', 'N/A')}\n")
                f.write(f"Root категорія: {category.get('root_category_title', 'N/A')}\n")
                f.write(f"Продавець: {seller.get('title', 'N/A')}\n")
                f.write(f"Опис: {description}\n")
                f.write("-" * 100 + "\n")
        
        logging.info("Parsing completed. Data saved to ready.txt")
        print("Parsing completed. All data saved to ready.txt")

async def fetch(session, url):
    await asyncio.sleep(0.8)
    async with session.get(url) as resp:
        resp.raise_for_status()
        logging.info(f"Fetched: {url} (status {resp.status})")
        return await resp.text()

async def fetch_json(session, url):
    await asyncio.sleep(0.8)
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            logging.warning(f"Failed API: {url} (status {resp.status})")
            return {}
    except Exception as e:
        logging.error(f"Error fetching JSON: {url} | {e}")
        return {}

def get_total_pages(html):
    soup = BeautifulSoup(html, 'lxml')
    total_text = soup.find(string=re.compile(r'Знайдено\s*\d+'))
    if total_text:
        match = re.search(r'(\d+)', total_text.replace(' ', ''))
        if match:
            total_products = int(match.group(1))
            pages = (total_products + 39) // 40
            return pages
    return 1

def extract_ids(html):
    soup = BeautifulSoup(html, 'lxml')
    ids = set()
    for a in soup.find_all('a', href=re.compile(r'/p\d+/$')):
        href = a['href']
        pid = href.split('/p')[-1].rstrip('/')
        if pid.isdigit():
            ids.add(pid)
    return ids

if __name__ == '__main__':
    asyncio.run(main())