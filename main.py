import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

async def req(s, u, j=False):
    async with s.get(u) as r:
        r.raise_for_status()
        return await r.json() if j else await r.text()

async def main():
    base = input("Enter category URL: ").strip().rstrip('/') + '/'
    print(f"Started parsing category: {base}")
    
    async with aiohttp.ClientSession(headers=HEADERS, connector=aiohttp.TCPConnector(limit=160), timeout=aiohttp.ClientTimeout(total=40)) as s:
        html0 = await req(s, base)
        pages = (int(re.search(r'Знайдено\s*(\d+)', html0).group(1)) + 39) // 40 if re.search(r'Знайдено\s*(\d+)', html0) else 1
        print(f"Detected {pages} pages")
        
        urls = [base + (f"page={p}/" if p > 1 else "") for p in range(1, pages + 1)]
        htmls = await asyncio.gather(*(req(s, u) for u in urls))
        
        ids = sorted(set(pid for h in htmls for pid in re.findall(r'/p(\d+)/', h)))
        print(f"Found {len(ids)} unique product IDs")
        
        det_urls = [f"https://common-api.rozetka.com.ua/v1/api/product/details?country=UA&lang=ua&ids={','.join(ids[i:i+60])}" for i in range(0, len(ids), 60)]
        det_jsons = await asyncio.gather(*(req(s, u, True) for u in det_urls))
        det = {str(p['id']): p for j in det_jsons for p in j.get('data', [])}
        
        mains = await asyncio.gather(*(req(s, f"https://common-api.rozetka.com.ua/v1/api/pages/product/main?country=UA&lang=ua&id={pid}&isGroup=false", True) for pid in ids))
        
        with open('ready.txt', 'w', encoding='utf-8') as f:
            for pid, mj in zip(ids, mains):
                d = det.get(pid, {})
                m = mj.get('data', {}).get('productData', {})
                raw = m.get('description', {}).get('text', '')
                desc = BeautifulSoup(raw, 'lxml').get_text(' ', True) if raw else 'Description is missing'
                c = d.get('category', {})
                sel = d.get('seller', {})
                f.write('\n'.join([
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
                    f"Seller: {sel.get('title', 'N/A')}",
                    f"Description: {desc}",
                    "-" * 100
                ]) + '\n')
    
    print("Parsing completed. All data saved to ready.txt")

asyncio.run(main())