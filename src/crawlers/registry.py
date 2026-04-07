from src.crawlers.base import BaseCrawler
from src.crawlers.sites.rocketpunch import RocketPunchCrawler
from src.crawlers.sites.wanted import WantedCrawler

CRAWLER_REGISTRY: dict[str, type[BaseCrawler]] = {
    "wanted": WantedCrawler,
    "rocketpunch": RocketPunchCrawler,
}


def get_crawler(site: str) -> BaseCrawler:
    """Get a crawler instance by site name."""
    crawler_cls = CRAWLER_REGISTRY.get(site)
    if crawler_cls is None:
        raise ValueError(
            f"Unknown site: {site}. Available: {list(CRAWLER_REGISTRY.keys())}"
        )
    return crawler_cls()
