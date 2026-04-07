from src.crawlers.utils.parser import clean_html, extract_requirements


class TestCleanHtml:
    def test_removes_tags(self) -> None:
        html = "<p>Hello <b>World</b></p>"
        result = clean_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "<p>" not in result
        assert "<b>" not in result

    def test_removes_script_and_style(self) -> None:
        html = "<div>Text<script>alert('x')</script><style>.a{}</style></div>"
        result = clean_html(html)
        assert "alert" not in result
        assert ".a{}" not in result
        assert "Text" in result

    def test_collapses_whitespace(self) -> None:
        html = "<p>Line1</p>\n\n\n<p>Line2</p>"
        result = clean_html(html)
        assert "Line1" in result
        assert "Line2" in result


class TestExtractRequirements:
    def test_extracts_korean_header(self) -> None:
        text = "주요업무\n서비스 개발\n\n자격요건\nPython 3년 이상\nFastAPI 경험\n\n우대사항\nK8s"
        result = extract_requirements(text)
        assert result is not None
        assert "Python" in result

    def test_returns_none_when_not_found(self) -> None:
        text = "This is a simple job description without sections."
        result = extract_requirements(text)
        assert result is None
