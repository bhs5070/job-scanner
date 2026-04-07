import logging
import random
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.common.config import get_settings

logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    """Create a requests session with retry and proper headers."""
    settings = get_settings()

    session = requests.Session()
    session.headers.update({
        "User-Agent": settings.CRAWL_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def polite_get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """Make a GET request with a random delay for politeness."""
    settings = get_settings()

    delay = random.uniform(settings.CRAWL_DELAY_MIN, settings.CRAWL_DELAY_MAX)
    time.sleep(delay)

    logger.debug(f"GET {url}")
    response = session.get(url, timeout=30, **kwargs)
    response.raise_for_status()
    return response
