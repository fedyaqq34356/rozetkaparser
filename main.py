import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

async def req(session, url, json=False):
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json() if json else await resp.text()

def get_total_pages(html):
    if match := re.search(r'Знайдено\s*(\d+)', html):
        total_products = int(match.group(1))
        return (total_products + 39) // 40
    return 1

def extract_ids(html):
    return set(re.findall(r'/p(\d+)/', html))

async def main():
    base = input("Enter category URL: ").strip().rstrip('/') + '/'
    print(f"Started parsing category: {base}")
    
    async with aiohttp.ClientSession(headers=HEADERS, connector=aiohttp.TCPConnector(limit=50), timeout=aiohttp.ClientTimeout(total=60)) as session:
        first_html = await req(session, base)
        total_pages = get_total_pages(first_html)
        print(f"Detected {total_pages} pages")
        
        page_urls = [base + (f"page={p}/" if p > 1 else "") for p in range(1, total_pages + 1)]
        page_htmls = await asyncio.gather(*(req(session, url) for url in page_urls))
        
        all_ids = sorted(set(pid for html in page_htmls for pid in extract_ids(html)))
        print(f"Found {len(all_ids)} unique product IDs")
        
        details_base = "https://common-api.rozetka.com.ua/v1/api/product/details?country=UA&lang=ua&ids="
        details_urls = [details_base + ','.join(all_ids[i:i+60]) for i in range(0, len(all_ids), 60)]
        details_jsons = await asyncio.gather(*(req(session, url, True) for url in details_urls))
        
        details_data = {str(p['id']): p for js in details_jsons for p in js.get('data', []) if p.get('id')}
        
        main_urls = [f"https://common-api.rozetka.com.ua/v1/api/pages/product/main?country=UA&lang=ua&id={pid}&isGroup=false" for pid in all_ids]
        main_jsons = await asyncio.gather(*(req(session, url, True) for url in main_urls))
        
        with open('ready.txt', 'w', encoding='utf-8') as f:
            for pid, main_json in zip(all_ids, main_jsons):
                d = details_data.get(pid, {})
                m = main_json.get('data', {}).get('productData', {})
                raw_desc = m.get('description', {}).get('text', '')
                desc = BeautifulSoup(raw_desc, 'lxml').get_text(separator=' ', strip=True) if raw_desc else 'Description is missing'
                
                category = d.get('category', {})
                seller = d.get('seller', {})
                
                f.write(f"ID: {pid}\n")
                f.write(f"Link: {d.get('href', f'https://rozetka.com.ua/ua/p{pid}/')}\n")
                f.write(f"Brand: {d.get('brand', 'N/A')}\n")
                f.write(f"Price: {d.get('price', 'N/A')} ₴\n")
                f.write(f"Old price: {d.get('old_price', 'N/A')} ₴\n")
                f.write(f"Reviews: {d.get('comments_amount', 0)} (rating {d.get('comments_mark', 0)})\n")
                f.write(f"Category ID: {category.get('id', 'N/A')}\n")
                f.write(f"Category link: {category.get('href', 'N/A')}\n")
                f.write(f"Category name: {category.get('title', 'N/A')}\n")
                f.write(f"Root category: {category.get('root_category_title', 'N/A')}\n")
                f.write(f"Seller: {seller.get('title', 'N/A')}\n")
                f.write(f"Description: {desc}\n")
                f.write("-" * 100 + "\n")
    
    print("Parsing completed. All data saved to ready.txt")

if __name__ == '__main__':
    asyncio.run(main())