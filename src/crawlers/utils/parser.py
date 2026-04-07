import re

from bs4 import BeautifulSoup


def clean_html(raw_html: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    soup = BeautifulSoup(raw_html, "lxml")

    # Remove script and style elements
    for element in soup(["script", "style"]):
        element.decompose()

    text = soup.get_text(separator="\n")

    # Normalize whitespace: collapse multiple blank lines
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    return text


def extract_section(text: str, headers: list[str]) -> str | None:
    """Try to extract a section from JD text by matching header patterns.

    Args:
        text: Full JD text.
        headers: List of possible section header strings to match.

    Returns:
        The section content, or None if not found.
    """
    for header in headers:
        pattern = rf"(?:^|\n)\s*{re.escape(header)}\s*\n([\s\S]*?)(?=\n\s*[가-힣A-Z]{{2,}}|\Z)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


REQUIREMENTS_HEADERS = [
    "자격요건",
    "자격 요건",
    "필수 자격",
    "필수자격",
    "Requirements",
    "Qualifications",
    "Required",
]

PREFERRED_HEADERS = [
    "우대사항",
    "우대 사항",
    "Preferred",
    "Nice to have",
    "우대조건",
]


def extract_requirements(text: str) -> str | None:
    """Extract requirements section from JD text."""
    return extract_section(text, REQUIREMENTS_HEADERS)


def extract_preferred(text: str) -> str | None:
    """Extract preferred qualifications from JD text."""
    return extract_section(text, PREFERRED_HEADERS)
