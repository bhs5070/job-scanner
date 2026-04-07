from datetime import datetime

from pydantic import BaseModel


class RawJobPost(BaseModel):
    """Raw data collected from a job listing page."""

    source_site: str
    source_url: str
    title: str
    company: str
    raw_text: str
    tech_tags: list[str] = []
    posted_at: datetime | None = None
    crawled_at: datetime


class ParsedJobPost(BaseModel):
    """Cleaned and normalized job posting ready for DB storage."""

    source_site: str
    source_url: str
    title: str
    company: str
    description: str
    requirements: str | None = None
    tech_stack: list[str] | None = None
    posted_at: datetime | None = None
    collected_at: datetime


class CrawlResult(BaseModel):
    """Result of a crawl job for a single site."""

    site: str
    items: list[ParsedJobPost] = []
    errors: list[str] = []
    total_fetched: int = 0
    total_parsed: int = 0
