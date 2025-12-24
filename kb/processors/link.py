"""Link processor for web pages."""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import httpx
import trafilatura

from .base import BaseProcessor, ProcessedContent, ContentType


# Zhihu-specific headers to bypass anti-scraping
ZHIHU_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


# Pattern to find URLs anywhere in text
URL_FINDER_PATTERN = re.compile(
    r'https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/[^\s<>\"\'\)]*)?',
    re.IGNORECASE
)


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text."""
    urls = URL_FINDER_PATTERN.findall(text)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for url in urls:
        # Clean trailing punctuation
        url = url.rstrip('.,;:!?)')
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


class LinkProcessor(BaseProcessor):
    """Processor for web links/URLs."""

    # URL pattern for exact match
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def can_process(self, input_str: str) -> bool:
        """Check if input is a valid URL."""
        input_str = input_str.strip()
        return bool(self.URL_PATTERN.match(input_str))

    async def process(self, input_str: str) -> ProcessedContent:
        """Fetch and process a web page."""
        url = input_str.strip()

        # Handle ArXiv PDF URLs - convert to abstract page
        url, original_url = self._normalize_arxiv_url(url)

        parsed_url = urlparse(url)
        source = parsed_url.netloc

        # Check if it's a Zhihu URL
        is_zhihu = "zhihu.com" in url

        # Select appropriate headers
        if is_zhihu:
            headers = ZHIHU_HEADERS
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }

        # Fetch the page
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers=headers
        ) as client:
            response = await client.get(url)

            # Handle Zhihu anti-scraping (403 or CAPTCHA)
            if is_zhihu and (response.status_code == 403 or "安全验证" in response.text):
                # Return with explanation - Zhihu has strong anti-bot protection
                return ProcessedContent(
                    content_type=ContentType.LINK,
                    title="知乎链接 (需要手动复制内容)",
                    source=original_url,
                    content="知乎有严格的反爬虫保护，无法自动抓取内容。请手动复制文章内容后使用文本模式输入。",
                )

            response.raise_for_status()

            # Check content type - if PDF, we can't parse it as HTML
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower():
                # Return basic info for PDF
                return ProcessedContent(
                    content_type=ContentType.LINK,
                    title=original_url,
                    source=original_url,
                    content="PDF document",
                )

            html = response.text

        # Extract content using trafilatura
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )

        # Get metadata
        metadata = trafilatura.extract_metadata(html)

        title = ""
        publish_date = ""
        if metadata:
            title = metadata.title or ""
            # Extract date from metadata
            publish_date = metadata.date or ""

        # Special handling for ArXiv - extract title and date
        if "arxiv.org" in url:
            arxiv_title = self._extract_arxiv_title(html)
            if arxiv_title:
                title = arxiv_title
            arxiv_date = self._extract_arxiv_date(html)
            if arxiv_date:
                publish_date = arxiv_date

        # Special handling for Zhihu - extract title, content, and date
        if is_zhihu:
            zhihu_data = self._extract_zhihu_content(html, url)
            if zhihu_data.get("title"):
                title = zhihu_data["title"]
            if zhihu_data.get("content"):
                extracted = zhihu_data["content"]
            if zhihu_data.get("date"):
                publish_date = zhihu_data["date"]

        # Fallback title extraction
        if not title:
            title = self._extract_title_from_html(html) or url

        content = extracted or ""

        # Use original URL as source (e.g., keep arxiv.org/pdf/... if that was input)
        return ProcessedContent(
            content_type=ContentType.LINK,
            title=title,
            source=original_url,
            content=content[:10000],  # Limit content length for LLM
            publish_date=publish_date if publish_date else None,
        )

    def _normalize_arxiv_url(self, url: str) -> tuple[str, str]:
        """Convert ArXiv PDF URL to abstract URL for better parsing.

        Returns:
            tuple of (normalized_url, original_url)
        """
        original_url = url

        # arxiv.org/pdf/XXXX.XXXXX -> arxiv.org/abs/XXXX.XXXXX
        if "arxiv.org/pdf/" in url:
            url = url.replace("arxiv.org/pdf/", "arxiv.org/abs/")
            # Remove .pdf extension if present
            if url.endswith(".pdf"):
                url = url[:-4]

        return url, original_url

    def _extract_arxiv_title(self, html: str) -> str:
        """Extract paper title from ArXiv page."""
        import re

        # Try meta tag first (most reliable)
        # <meta name="citation_title" content="...">
        match = re.search(r'<meta\s+name="citation_title"\s+content="([^"]+)"', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try og:title meta tag
        match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            # Remove "[XXXX.XXXXX]" prefix if present
            title = re.sub(r'^\[\d+\.\d+\]\s*', '', title)
            return title

        # Try h1.title class (ArXiv abstract page structure)
        match = re.search(r'<h1[^>]*class="title[^"]*"[^>]*>(?:<span[^>]*>Title:</span>)?\s*([^<]+)', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_arxiv_date(self, html: str) -> str:
        """Extract submission/publication date from ArXiv page."""
        import re

        # Try citation_date meta tag (format: YYYY/MM/DD)
        match = re.search(r'<meta\s+name="citation_date"\s+content="([^"]+)"', html, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            # Convert YYYY/MM/DD to YYYY-MM-DD
            return date_str.replace("/", "-")

        # Try citation_online_date
        match = re.search(r'<meta\s+name="citation_online_date"\s+content="([^"]+)"', html, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            return date_str.replace("/", "-")

        # Try to find "Submitted on DD Mon YYYY" pattern
        match = re.search(r'Submitted\s+on\s+(\d{1,2}\s+\w+\s+\d{4})', html, re.IGNORECASE)
        if match:
            return match.group(1)

        # Try dateline class
        match = re.search(r'class="dateline"[^>]*>([^<]+)<', html, re.IGNORECASE)
        if match:
            dateline = match.group(1).strip()
            # Extract date from "Submitted on 2 Dec 2024"
            date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', dateline)
            if date_match:
                return date_match.group(1)

        return ""

    def _extract_zhihu_content(self, html: str, url: str) -> dict:
        """Extract content from Zhihu page."""
        result = {"title": "", "content": "", "date": "", "author": ""}

        # Try to extract from JSON-LD script
        json_ld_match = re.search(
            r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>',
            html, re.IGNORECASE
        )
        if json_ld_match:
            try:
                data = json.loads(json_ld_match.group(1))
                if isinstance(data, dict):
                    result["title"] = data.get("headline", "") or data.get("name", "")
                    result["content"] = data.get("articleBody", "") or data.get("text", "")
                    result["date"] = data.get("datePublished", "") or data.get("dateCreated", "")
                    if "author" in data:
                        author = data["author"]
                        if isinstance(author, dict):
                            result["author"] = author.get("name", "")
                        elif isinstance(author, str):
                            result["author"] = author
            except json.JSONDecodeError:
                pass

        # Try to extract from initial data script (Zhihu stores data here)
        initial_data_match = re.search(
            r'<script[^>]*id="js-initialData"[^>]*>([^<]+)</script>',
            html, re.IGNORECASE
        )
        if initial_data_match and not result["content"]:
            try:
                data = json.loads(initial_data_match.group(1))
                # Navigate the complex Zhihu data structure
                if "initialState" in data:
                    state = data["initialState"]
                    # Extract answer content
                    if "entities" in state and "answers" in state["entities"]:
                        answers = state["entities"]["answers"]
                        for answer_id, answer in answers.items():
                            if not result["content"]:
                                result["content"] = answer.get("content", "")
                                result["date"] = answer.get("createdTime", "") or answer.get("updatedTime", "")
                    # Extract question title
                    if "entities" in state and "questions" in state["entities"]:
                        questions = state["entities"]["questions"]
                        for q_id, question in questions.items():
                            if not result["title"]:
                                result["title"] = question.get("title", "")
            except json.JSONDecodeError:
                pass

        # Fallback: extract from HTML meta tags
        if not result["title"]:
            og_title = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html, re.IGNORECASE)
            if og_title:
                result["title"] = og_title.group(1).strip()

        if not result["content"]:
            # Try to extract from RichText span
            content_match = re.search(r'<span[^>]*class="RichText[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
            if content_match:
                # Remove HTML tags
                content = re.sub(r'<[^>]+>', '', content_match.group(1))
                result["content"] = content.strip()

        # Clean up content - remove HTML tags if present
        if result["content"]:
            result["content"] = re.sub(r'<[^>]+>', '', result["content"])
            result["content"] = result["content"].strip()

        # Format date if it's a timestamp
        if result["date"] and result["date"].isdigit():
            from datetime import datetime
            try:
                dt = datetime.fromtimestamp(int(result["date"]))
                result["date"] = dt.strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pass

        return result

    def _extract_title_from_html(self, html: str) -> str:
        """Extract title from HTML as fallback."""
        import re
        match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
