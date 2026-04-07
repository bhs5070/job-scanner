import logging
from datetime import datetime, timezone

from src.crawlers.base import BaseCrawler
from src.crawlers.schemas import ParsedJobPost, RawJobPost
from src.crawlers.utils.http_client import create_session, polite_get
from src.crawlers.utils.parser import clean_html, extract_requirements

logger = logging.getLogger(__name__)

WANTED_SEARCH_URL = "https://www.wanted.co.kr/api/v4/jobs"


class WantedCrawler(BaseCrawler):
    """Crawler for wanted.co.kr job postings."""

    site_name = "wanted"

    def __init__(self) -> None:
        self.session = create_session()

    def fetch_list(self, keyword: str, page: int = 1) -> list[RawJobPost]:
        """Fetch job listings from Wanted API."""
        params = {
            "country": "kr",
            "job_sort": "job.latest_order",
            "years": -1,
            "locations": "all",
            "limit": 20,
            "offset": (page - 1) * 20,
            "query": keyword,
        }

        response = polite_get(self.session, WANTED_SEARCH_URL, params=params)
        data = response.json()

        posts: list[RawJobPost] = []
        for job in data.get("data", []):
            job_id = job.get("id")
            if not job_id:
                continue

            posts.append(RawJobPost(
                source_site=self.site_name,
                source_url=f"https://www.wanted.co.kr/wd/{job_id}",
                title=job.get("position", ""),
                company=job.get("company", {}).get("name", ""),
                raw_text="",  # Will be filled by fetch_detail
                tech_tags=[],
                posted_at=None,
                crawled_at=datetime.now(timezone.utc),
            ))

        logger.info(f"[wanted] keyword={keyword}, page={page}, found={len(posts)}")
        return posts

    def fetch_detail(self, raw: RawJobPost) -> RawJobPost | None:
        """Fetch detail page for a Wanted job posting."""
        # Wanted detail API endpoint
        job_id = raw.source_url.split("/")[-1]
        detail_url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"

        try:
            response = polite_get(self.session, detail_url)
            data = response.json()
            job = data.get("job", {})

            detail = job.get("detail", {})
            new_text = detail.get("requirements", "") + "\n" + detail.get("main_tasks", "")
            new_tags = [
                skill.get("keyword", "")
                for skill in job.get("skill_tags", [])
                if skill.get("keyword")
            ]

            return raw.model_copy(update={"raw_text": new_text, "tech_tags": new_tags})
        except Exception as e:
            logger.warning(f"[wanted] fetch_detail failed for {raw.source_url}: {e}")
            return None

    def parse(self, raw: RawJobPost) -> ParsedJobPost | None:
        """Parse a raw Wanted job post into normalized format."""
        if not raw.title or not raw.company:
            return None

        cleaned_text = clean_html(raw.raw_text) if raw.raw_text else ""
        requirements = extract_requirements(cleaned_text)

        return ParsedJobPost(
            source_site=self.site_name,
            source_url=raw.source_url,
            title=raw.title,
            company=raw.company,
            description=cleaned_text,
            requirements=requirements,
            tech_stack=raw.tech_tags if raw.tech_tags else None,
            posted_at=raw.posted_at,
            collected_at=raw.crawled_at,
        )
