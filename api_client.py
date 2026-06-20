import aiohttp
import asyncio
import random
from typing import Optional, Any
from config import get_headers, REQUEST_TIMEOUT, CONNECTOR_LIMIT, CONNECTOR_LIMIT_PER_HOST, MIN_DELAY, MAX_DELAY
from logger import logger

class ApiClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=CONNECTOR_LIMIT,
            limit_per_host=CONNECTOR_LIMIT_PER_HOST,
            ssl=False,
            force_close=False,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, connect=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            cookie_jar=aiohttp.CookieJar()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            await asyncio.sleep(0.5)
    
    async def get(self, url: str, as_json: bool = False, max_retries: int = 7) -> Any:
        for attempt in range(max_retries):
            try:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)
                
                headers = get_headers()
                
                if 'rozetka.com.ua/ua/' in url and not url.startswith(('https://common-api', 'https://product-api')):
                    headers['Referer'] = 'https://rozetka.com.ua/ua/'
                
                async with self.session.get(url, headers=headers, allow_redirects=True) as response:
                    if response.status == 403:
                        logger.warning(f"403 Forbidden (attempt {attempt + 1}/{max_retries}): {url}")
                        if attempt < max_retries - 1:
                            wait_time = min((3 ** attempt) + random.uniform(2, 5), 60)
                            logger.info(f"Waiting {wait_time:.2f}s before retry...")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    if response.status == 429:
                        logger.warning(f"429 Too Many Requests (attempt {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            wait_time = min((4 ** attempt) + random.uniform(5, 10), 120)
                            logger.info(f"Rate limited. Waiting {wait_time:.2f}s...")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    response.raise_for_status()
                    
                    if as_json:
                        return await response.json()
                    return await response.text()
                    
            except aiohttp.ClientResponseError as e:
                if e.status in [403, 429] and attempt < max_retries - 1:
                    wait_time = min((3 ** attempt) + random.uniform(3, 7), 90)
                    logger.warning(f"{e.status} error, retrying... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Request failed: {url} - {str(e)}")
                if attempt == max_retries - 1:
                    raise
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {url} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    continue
                raise
            except Exception as e:
                logger.error(f"Request failed: {url} - {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    continue
                raise
        
        raise Exception(f"Failed after {max_retries} attempts: {url}")