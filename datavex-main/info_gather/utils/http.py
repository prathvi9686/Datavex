import time
import random
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Accept-Language": "en-US,en;q=0.7",
    },
]

def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(random.choice(HEADERS_POOL))
    return session

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def safe_get(url: str, session: requests.Session | None = None, timeout: int = 20, **kwargs) -> requests.Response:
    """GET with automatic retry and polite delay."""
    time.sleep(random.uniform(1.0, 2.5))   # polite crawl delay
    s = session or get_session()

    resp = s.get(url, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF given as raw bytes. Pure Python, no C deps."""
    import io
    from pdfminer.high_level import extract_text
    return extract_text(io.BytesIO(pdf_bytes))
