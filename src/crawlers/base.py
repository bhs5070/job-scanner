import logging
from abc import ABC, abstractmethod

from src.crawlers.schemas import CrawlResult, ParsedJobPost, RawJobPost

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base class for all site-specific crawlers."""

    site_name: str = ""

    @abstractmethod
    def fetch_list(self, keyword: str, page: int = 1) -> list[RawJobPost]:
        """Fetch job listing page and return raw posts."""
        ...

    @abstractmethod
    def fetch_detail(self, raw: RawJobPost) -> RawJobPost | None:
        """Fetch detail page to enrich a raw post. Returns None on failure."""
        ...

    @abstractmethod
    def parse(self, raw: RawJobPost) -> ParsedJobPost | None:
        """Parse and clean a raw post. Returns None on failure."""
        ...

    def crawl(self, keywords: list[str], max_pages: int = 3) -> CrawlResult:
        """Run the full crawl pipeline: list -> detail -> parse.

        This is the main entry point called by the Airflow DAG.
        """
        all_raw: list[RawJobPost] = []
        errors: list[str] = []

        for keyword in keywords:
            for page in range(1, max_pages + 1):
                try:
                    posts = self.fetch_list(keyword, page)
                    all_raw.extend(posts)
                except Exception as e:
                    msg = f"[{self.site_name}] fetch_list failed: keyword={keyword}, page={page}, error={e}"
                    logger.warning(msg)
                    errors.append(msg)

        # Deduplicate by source_url
        seen_urls: set[str] = set()
        unique_raw: list[RawJobPost] = []
        for raw in all_raw:
            if raw.source_url not in seen_urls:
                seen_urls.add(raw.source_url)
                unique_raw.append(raw)

        # Enrich with detail pages
        enriched: list[RawJobPost] = []
        for raw in unique_raw:
            try:
                detail = self.fetch_detail(raw)
                enriched.append(detail if detail else raw)
            except Exception as e:
                msg = f"[{self.site_name}] fetch_detail failed: url={raw.source_url}, error={e}"
                logger.warning(msg)
                errors.append(msg)
                enriched.append(raw)

        # Parse
        parsed: list[ParsedJobPost] = []
        for raw in enriched:
            try:
                result = self.parse(raw)
                if result:
                    parsed.append(result)
            except Exception as e:
                msg = f"[{self.site_name}] parse failed: url={raw.source_url}, error={e}"
                logger.warning(msg)
                errors.append(msg)

        return CrawlResult(
            site=self.site_name,
            items=parsed,
            errors=errors,
            total_fetched=len(unique_raw),
            total_parsed=len(parsed),
        )
