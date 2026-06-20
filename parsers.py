import re
import asyncio
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from api_client import ApiClient
from config import API_BASE, PRODUCT_API_BASE, BATCH_SIZE, COMMENTS_PER_PAGE
from logger import logger

async def parse_category_pages(client: ApiClient, base_url: str) -> int:
    html = await client.get(base_url)
    match = re.search(r'Знайдено\s*(\d+)', html)
    if match:
        total = int(match.group(1))
        pages = (total + 39) // 40
        logger.info(f"Знайдено {total} товарів, {pages} сторінок")
        return pages
    logger.warning("Не вдалося визначити кількість сторінок")
    return 1

async def extract_product_ids(client: ApiClient, base_url: str, pages: int) -> List[str]:
    urls = [
        base_url + (f"page={p}/" if p > 1 else "")
        for p in range(1, pages + 1)
    ]
    
    logger.info(f"Отримання ID товарів з {pages} сторінок...")
    
    ids = set()
    batch_size = 2
    
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i:i+batch_size]
        logger.info(f"Обробка сторінок {i+1}-{min(i+batch_size, len(urls))} з {len(urls)}")
        
        htmls = await asyncio.gather(*[client.get(url) for url in batch_urls])
        
        for html in htmls:
            ids.update(re.findall(r'/p(\d+)/', html))
        
        if i + batch_size < len(urls):
            await asyncio.sleep(2)
    
    ids = sorted(ids)
    logger.info(f"Отримано {len(ids)} унікальних ID товарів")
    return ids

async def fetch_product_details(client: ApiClient, ids: List[str]) -> Dict[str, Dict]:
    batches = [ids[i:i+BATCH_SIZE] for i in range(0, len(ids), BATCH_SIZE)]
    logger.info(f"Отримання деталей товарів у {len(batches)} пакетах...")
    
    details = {}
    
    for idx, batch in enumerate(batches, 1):
        logger.info(f"Обробка пакета {idx}/{len(batches)}")
        
        try:
            result = await client.get(
                f"{API_BASE}/product/details?country=UA&lang=ua&ids={','.join(batch)}",
                as_json=True
            )
            
            for p in result.get('data', []):
                details[str(p['id'])] = p
            
            if idx < len(batches):
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Помилка в пакеті {idx}: {e}")
            continue
    
    logger.info(f"Отримано деталі для {len(details)} товарів")
    return details

async def fetch_product_main(client: ApiClient, product_id: str) -> Dict:
    url = f"{API_BASE}/pages/product/main?country=UA&lang=ua&id={product_id}&isGroup=false"
    result = await client.get(url, as_json=True)
    return result.get('data', {}).get('productData', {})

async def fetch_all_product_mains(client: ApiClient, ids: List[str]) -> List[Dict]:
    logger.info(f"Отримання основних даних для {len(ids)} товарів...")
    
    batch_size = 3
    results = []
    
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        logger.info(f"Отримання даних для товарів {i+1}-{min(i+batch_size, len(ids))} з {len(ids)}")
        
        batch_results = await asyncio.gather(*[fetch_product_main(client, pid) for pid in batch])
        results.extend(batch_results)
        
        if i + batch_size < len(ids):
            await asyncio.sleep(1.5)
    
    return results

async def fetch_comments_page(client: ApiClient, product_id: str, page: int, seller_id: int = 5) -> Dict:
    url = (f"{PRODUCT_API_BASE}/comments/get?country=UA&lang=ua&goods={product_id}"
           f"&limit={COMMENTS_PER_PAGE}&page={page}&sort=from_buyer&topSellerId={seller_id}&type=comment")
    return await client.get(url, as_json=True)

async def fetch_all_comments(client: ApiClient, product_id: str) -> Dict:
    first_page = await fetch_comments_page(client, product_id, 1)
    
    pages_count = first_page.get('data', {}).get('pages', {}).get('count', 1)
    
    if pages_count <= 1:
        return first_page
    
    logger.info(f"Товар {product_id}: отримання {pages_count} сторінок відгуків")
    
    remaining_pages = await asyncio.gather(*[
        fetch_comments_page(client, product_id, page)
        for page in range(2, pages_count + 1)
    ])
    
    all_comments = first_page.get('data', {}).get('comments', [])
    for page_data in remaining_pages:
        all_comments.extend(page_data.get('data', {}).get('comments', []))
    
    first_page['data']['comments'] = all_comments
    return first_page

def extract_images(main_data: Dict) -> List[str]:
    images = []
    
    product_images = (main_data.get('product') or {}).get('images', [])
    for img in product_images:
        if 'original' in img and 'url' in img['original']:
            images.append(img['original']['url'])
    
    var_params = (main_data.get('varParams') or {}).get('options', [])
    for option in var_params:
        for value in option.get('values', []):
            if 'bgImageUrl' in value and value['bgImageUrl']:
                images.append(value['bgImageUrl'])
            if 'product' in value and 'image' in value['product']:
                images.append(value['product']['image'])
    
    return list(dict.fromkeys(images))

def extract_characteristics(main_data: Dict) -> List[Dict[str, str]]:
    chars = []
    characteristics = main_data.get('characteristics') or []
    
    for group in characteristics:
        for option in (group.get('options') or []):
            title = option.get('title', '')
            values = option.get('values') or []
            for value in values:
                chars.append({
                    'назва': title,
                    'значення': value.get('title', '')
                })
    
    return chars

def clean_description(html_text: str) -> str:
    if not html_text:
        return 'Опис відсутній'
    soup = BeautifulSoup(html_text, 'lxml')
    return soup.get_text(' ', strip=True) or 'Опис відсутній'