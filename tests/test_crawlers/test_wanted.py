from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.crawlers.schemas import RawJobPost
from src.crawlers.sites.wanted import WantedCrawler


class TestWantedCrawler:
    def test_parse_valid_post(self) -> None:
        crawler = WantedCrawler()
        raw = RawJobPost(
            source_site="wanted",
            source_url="https://www.wanted.co.kr/wd/12345",
            title="AI Engineer",
            company="TestCorp",
            raw_text="<p>Python, FastAPI 경험자</p>",
            tech_tags=["Python", "FastAPI"],
            crawled_at=datetime.now(timezone.utc),
        )

        result = crawler.parse(raw)

        assert result is not None
        assert result.title == "AI Engineer"
        assert result.company == "TestCorp"
        assert result.tech_stack == ["Python", "FastAPI"]
        assert result.source_site == "wanted"

    def test_parse_returns_none_for_empty_title(self) -> None:
        crawler = WantedCrawler()
        raw = RawJobPost(
            source_site="wanted",
            source_url="https://www.wanted.co.kr/wd/99999",
            title="",
            company="TestCorp",
            raw_text="Some text",
            crawled_at=datetime.now(timezone.utc),
        )

        result = crawler.parse(raw)
        assert result is None

    def test_parse_handles_no_tech_tags(self) -> None:
        crawler = WantedCrawler()
        raw = RawJobPost(
            source_site="wanted",
            source_url="https://www.wanted.co.kr/wd/11111",
            title="Backend Developer",
            company="SomeCo",
            raw_text="Job description here",
            tech_tags=[],
            crawled_at=datetime.now(timezone.utc),
        )

        result = crawler.parse(raw)
        assert result is not None
        assert result.tech_stack is None
