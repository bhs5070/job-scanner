import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.crawlers.base import BaseCrawler
from src.crawlers.schemas import ParsedJobPost, RawJobPost
from src.crawlers.utils.http_client import create_session, polite_get
from src.crawlers.utils.parser import clean_html, extract_requirements

logger = logging.getLogger(__name__)

ROCKETPUNCH_SEARCH_URL = "https://www.rocketpunch.com/api/hiring"


class RocketPunchCrawler(BaseCrawler):
    """Crawler for rocketpunch.com job postings."""

    site_name = "rocketpunch"

    def __init__(self) -> None:
        self.session = create_session()

    def fetch_list(self, keyword: str, page: int = 1) -> list[RawJobPost]:
        """Fetch job listings from RocketPunch."""
        params = {
            "keywords": keyword,
            "page": page,
        }
        headers = {
            "Accept": "application/json",
            "Referer": "https://www.rocketpunch.com/jobs",
        }

        response = polite_get(
            self.session, ROCKETPUNCH_SEARCH_URL, params=params, headers=headers
        )
        data = response.json()

        posts: list[RawJobPost] = []
        # Parse the HTML content returned in the API response
        html_content = data.get("data", {}).get("template", "")
        if not html_content:
            logger.warning(f"[rocketpunch] Empty template in API response for keyword={keyword}")
            return []
        soup = BeautifulSoup(html_content, "lxml")

        for card in soup.select(".company-jobs-content"):
            link_tag = card.select_one("a.job-title")
            company_tag = card.select_one("a.company-name")

            if not link_tag or not company_tag:
                continue

            href = link_tag.get("href", "")
            if not href:
                source_url = ""
            elif href.startswith("http"):
                source_url = href
            else:
                source_url = f"https://www.rocketpunch.com{href}"
            title = link_tag.get_text(strip=True)
            company = company_tag.get_text(strip=True)

            if not source_url or not title:
                continue

            posts.append(RawJobPost(
                source_site=self.site_name,
                source_url=source_url,
                title=title,
                company=company,
                raw_text="",
                tech_tags=[],
                posted_at=None,
                crawled_at=datetime.now(timezone.utc),
            ))

        logger.info(
            f"[rocketpunch] keyword={keyword}, page={page}, found={len(posts)}"
        )
        return posts

    def fetch_detail(self, raw: RawJobPost) -> RawJobPost | None:
        """Fetch detail page for a RocketPunch job posting."""
        try:
            response = polite_get(self.session, raw.source_url)
            soup = BeautifulSoup(response.text, "lxml")

            # Extract job description section
            new_text = raw.raw_text
            jd_section = soup.select_one(".content-description")
            if jd_section:
                new_text = str(jd_section)

            # RocketPunch doesn't provide structured tech tags in all cases
            tag_elements = soup.select(".job-stat-tag")
            new_tags = [tag.get_text(strip=True) for tag in tag_elements]

            return raw.model_copy(update={"raw_text": new_text, "tech_tags": new_tags})
        except Exception as e:
            logger.warning(
                f"[rocketpunch] fetch_detail failed for {raw.source_url}: {e}"
            )
            return None

    def parse(self, raw: RawJobPost) -> ParsedJobPost | None:
        """Parse a raw RocketPunch job post into normalized format."""
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
