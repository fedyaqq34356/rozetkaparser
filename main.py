import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

async def request(session, url, json=False):
    await asyncio.sleep(0.8)
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json() if json else await resp.text()

def parse_pages(html):
    soup = BeautifulSoup(html, 'lxml')
    total = 1
    if match := re.search(r'\d+', (text := soup.find(string=re.compile(r'Знайдено\s*\d+')) or '').replace(' ', '')):
        total = (int(match.group(0)) + 39) // 40
    return total

def parse_ids(html):
    return set(re.findall(r'/p(\d+)/', html))

async def main():
    base = input("Enter category URL: ").strip().rstrip('/') + '/'
    print(f"Started parsing category: {base}")
    
    async with aiohttp.ClientSession(headers=HEADERS, connector=aiohttp.TCPConnector(limit=30), timeout=aiohttp.ClientTimeout(total=40)) as session:
        first = await request(session, base)
        pages = parse_pages(first)
        print(f"Detected {pages} pages")
        
        urls = [base + (f"page={p}/" if p > 1 else "") for p in range(1, pages + 1)]
        htmls = await asyncio.gather(*(request(session, u) for u in urls))
        
        ids = sorted(set().union(*(parse_ids(h) for h in htmls)))
        print(f"Found {len(ids)} unique product IDs")
        
        details_urls = [f"https://common-api.rozetka.com.ua/v1/api/product/details?country=UA&lang=ua&ids={','.join(ids[i:i+60])}" for i in range(0, len(ids), 60)]
        details_resp = await asyncio.gather(*(request(session, u, True) for u in details_urls))
        details_dict = {str(p['id']): p for r in details_resp for p in r.get('data', [])}
        
        main_jsons = await asyncio.gather(*(request(session, f"https://common-api.rozetka.com.ua/v1/api/pages/product/main?country=UA&lang=ua&id={pid}&isGroup=false", True) for pid in ids))
        
        with open('ready.txt', 'w', encoding='utf-8') as f:
            for pid, mj in zip(ids, main_jsons):
                d = details_dict.get(pid, {})
                m = mj.get('data', {}).get('productData', {})
                raw = m.get('description', {}).get('text', '')
                desc = BeautifulSoup(raw, 'lxml').get_text(separator=' ', strip=True) if raw else 'Description is missing'
                c = d.get('category', {})
                s = d.get('seller', {})
                lines = [
                    f"ID: {pid}",
                    f"Link: {d.get('href', f'https://rozetka.com.ua/ua/p{pid}/')}",
                    f"Brand: {d.get('brand', 'N/A')}",
                    f"Price: {d.get('price', 'N/A')} ₴",
                    f"Old price: {d.get('old_price', 'N/A')} ₴",
                    f"Reviews: {d.get('comments_amount', 0)} (rating {d.get('comments_mark', 0)})",
                    f"Category ID: {c.get('id', 'N/A')}",
                    f"Category link: {c.get('href', 'N/A')}",
                    f"Category name: {c.get('title', 'N/A')}",
                    f"Root category: {c.get('root_category_title', 'N/A')}",
                    f"Seller: {s.get('title', 'N/A')}",
                    f"Description: {desc}",
                    "-" * 100
                ]
                f.write('\n'.join(lines) + '\n')
    
    print("Parsing completed. All data saved to ready.txt")

if __name__ == '__main__':
    asyncio.run(main())