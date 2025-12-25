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
    async with aiohttp.ClientSession(headers=HEADERS, connector=aiohttp.TCPConnector(limit=300, limit_per_host=100), timeout=aiohttp.ClientTimeout(total=60)) as s:
        html0 = await req(s, base)
        pages = (int(m.group(1)) + 39) // 40 if (m := re.search(r'Знайдено\s*(\d+)', html0)) else 1
        
        ids = sorted({pid for h in await asyncio.gather(*(req(s, base + (f"page={p}/" if p > 1 else "")) for p in range(1, pages + 1)))
                      for pid in re.findall(r'/p(\d+)/', h)})
        
        det = {str(p['id']): p for j in await asyncio.gather(*(req(s, f"https://common-api.rozetka.com.ua/v1/api/product/details?country=UA&lang=ua&ids={','.join(ids[i:i+60])}", True)
                                                              for i in range(0, len(ids), 60)))
               for p in j.get('data', [])}
        
        mains = await asyncio.gather(*(req(s, f"https://common-api.rozetka.com.ua/v1/api/pages/product/main?country=UA&lang=ua&id={pid}&isGroup=false", True) for pid in ids))
        
        with open('ready.txt', 'w', encoding='utf-8') as f:
            for pid, mj in zip(ids, mains):
                d = det.get(pid, {})
                m = mj.get('data', {}).get('productData', {})
                raw_desc = m.get('description', {}).get('text') or ''
                desc = BeautifulSoup(raw_desc, 'lxml').get_text(' ', True) or 'Description is missing'
                c, sel = d.get('category', {}), d.get('seller', {})
                f.write(f"ID: {pid}\nLink: {d.get('href', f'https://rozetka.com.ua/ua/p{pid}/')}\nBrand: {d.get('brand', 'N/A')}\n"
                        f"Price: {d.get('price', 'N/A')} ₴\nOld price: {d.get('old_price', 'N/A')} ₴\n"
                        f"Reviews: {d.get('comments_amount', 0)} (rating {d.get('comments_mark', 0)})\n"
                        f"Category ID: {c.get('id', 'N/A')}\nCategory link: {c.get('href', 'N/A')}\n"
                        f"Category name: {c.get('title', 'N/A')}\nRoot category: {c.get('root_category_title', 'N/A')}\n"
                        f"Seller: {sel.get('title', 'N/A')}\nDescription: {desc}\n{'-'*100}\n")

    print(f"Parsing completed: {len(ids)} products saved to ready.txt")

asyncio.run(main())