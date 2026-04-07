from src.crawlers.registry import get_crawler
from src.crawlers.schemas import CrawlResult


def run_crawl_job(
    site: str, keywords: list[str], max_pages: int = 3
) -> CrawlResult:
    """Main entry point for crawling a single site.

    Called by the Airflow DAG. Returns a CrawlResult with parsed items.
    """
    crawler = get_crawler(site)
    return crawler.crawl(keywords=keywords, max_pages=max_pages)
