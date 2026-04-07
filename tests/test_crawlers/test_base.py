from datetime import datetime, timezone

from src.crawlers.base import BaseCrawler
from src.crawlers.schemas import CrawlResult, ParsedJobPost, RawJobPost


class FakeCrawler(BaseCrawler):
    """Test implementation of BaseCrawler."""

    site_name = "fake"

    def __init__(self, posts: list[RawJobPost] | None = None) -> None:
        self._posts = posts or []

    def fetch_list(self, keyword: str, page: int = 1) -> list[RawJobPost]:
        return self._posts

    def fetch_detail(self, raw: RawJobPost) -> RawJobPost | None:
        return raw

    def parse(self, raw: RawJobPost) -> ParsedJobPost | None:
        return ParsedJobPost(
            source_site=raw.source_site,
            source_url=raw.source_url,
            title=raw.title,
            company=raw.company,
            description=raw.raw_text,
            collected_at=raw.crawled_at,
        )


def _make_raw(url: str = "https://example.com/1") -> RawJobPost:
    return RawJobPost(
        source_site="fake",
        source_url=url,
        title="Test Job",
        company="Test Co",
        raw_text="Description",
        crawled_at=datetime.now(timezone.utc),
    )


class TestBaseCrawler:
    def test_crawl_returns_result(self) -> None:
        posts = [_make_raw()]
        crawler = FakeCrawler(posts=posts)
        result = crawler.crawl(keywords=["test"], max_pages=1)

        assert isinstance(result, CrawlResult)
        assert result.site == "fake"
        assert len(result.items) == 1
        assert result.total_fetched == 1
        assert result.total_parsed == 1

    def test_crawl_deduplicates_by_url(self) -> None:
        posts = [_make_raw("https://example.com/1"), _make_raw("https://example.com/1")]
        crawler = FakeCrawler(posts=posts)
        result = crawler.crawl(keywords=["test"], max_pages=1)

        assert result.total_fetched == 1
        assert len(result.items) == 1

    def test_crawl_handles_empty_results(self) -> None:
        crawler = FakeCrawler(posts=[])
        result = crawler.crawl(keywords=["test"], max_pages=1)

        assert len(result.items) == 0
        assert result.total_fetched == 0
