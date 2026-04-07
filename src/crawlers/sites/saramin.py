import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.crawlers.base import BaseCrawler
from src.crawlers.schemas import ParsedJobPost, RawJobPost
from src.crawlers.utils.http_client import create_session, polite_get
from src.crawlers.utils.parser import clean_html, extract_requirements

logger = logging.getLogger(__name__)

SARAMIN_SEARCH_URL = "https://www.saramin.co.kr/zf_user/search/recruit"


class SaraminCrawler(BaseCrawler):
    """Crawler for saramin.co.kr job postings."""

    site_name = "saramin"

    def __init__(self) -> None:
        self.session = create_session()

    def fetch_list(self, keyword: str, page: int = 1) -> list[RawJobPost]:
        """Fetch job listings from Saramin search page."""
        params = {
            "searchType": "search",
            "searchword": keyword,
            "recruitPage": page,
            "recruitSort": "relation",
            "recruitPageCount": 40,
        }

        response = polite_get(self.session, SARAMIN_SEARCH_URL, params=params)
        soup = BeautifulSoup(response.text, "lxml")

        posts: list[RawJobPost] = []
        for item in soup.select(".item_recruit"):
            title_tag = item.select_one(".job_tit a")
            company_tag = item.select_one(".corp_name a")

            if not title_tag or not company_tag:
                continue

            href = title_tag.get("href", "")
            if not href:
                continue

            if href.startswith("http"):
                source_url = href
            else:
                source_url = f"https://www.saramin.co.kr{href}"

            title = title_tag.get_text(strip=True)
            company = company_tag.get_text(strip=True)

            if not title or not company:
                continue

            # Extract tech tags from job condition badges
            tech_tags: list[str] = []
            badge_area = item.select(".job_sector span")
            for badge in badge_area:
                text = badge.get_text(strip=True)
                if text:
                    tech_tags.append(text)

            posts.append(RawJobPost(
                source_site=self.site_name,
                source_url=source_url,
                title=title,
                company=company,
                raw_text="",
                tech_tags=tech_tags,
                posted_at=None,
                crawled_at=datetime.now(timezone.utc),
            ))

        logger.info(f"[saramin] keyword={keyword}, page={page}, found={len(posts)}")
        return posts

    def fetch_detail(self, raw: RawJobPost) -> RawJobPost | None:
        """Fetch detail page for a Saramin job posting."""
        try:
            response = polite_get(self.session, raw.source_url)
            soup = BeautifulSoup(response.text, "lxml")

            # Extract job description
            jd_section = soup.select_one(".user_content") or soup.select_one(".wrap_jv_cont")
            new_text = str(jd_section) if jd_section else raw.raw_text

            # Extract additional tech stack from detail page
            new_tags = list(raw.tech_tags)
            skill_elements = soup.select(".wrap_skill .box_item span")
            for el in skill_elements:
                tag = el.get_text(strip=True)
                if tag and tag not in new_tags:
                    new_tags.append(tag)

            return raw.model_copy(update={"raw_text": new_text, "tech_tags": new_tags})
        except Exception as e:
            logger.warning(f"[saramin] fetch_detail failed for {raw.source_url}: {e}")
            return None

    def parse(self, raw: RawJobPost) -> ParsedJobPost | None:
        """Parse a raw Saramin job post into normalized format."""
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
