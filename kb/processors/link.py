"""Link processor for web pages."""
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
import trafilatura

from .base import BaseProcessor, ProcessedContent, ContentType


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

        # Fetch the page
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        ) as client:
            response = await client.get(url)
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

    def _extract_title_from_html(self, html: str) -> str:
        """Extract title from HTML as fallback."""
        import re
        match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
