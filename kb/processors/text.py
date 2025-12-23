"""Text processor for plain text content."""
from __future__ import annotations

from .base import BaseProcessor, ProcessedContent, ContentType


class TextProcessor(BaseProcessor):
    """Processor for plain text content."""

    async def can_process(self, input_str: str) -> bool:
        """Text processor is the fallback - can always process."""
        # This is used as fallback when other processors don't match
        return True

    async def process(self, input_str: str) -> ProcessedContent:
        """Process plain text content."""
        text = input_str.strip()

        # Try to extract a title from the first line
        lines = text.split("\n")
        first_line = lines[0].strip()

        # Use first line as title if it's short enough
        if len(first_line) <= 100 and len(lines) > 1:
            title = first_line
            content = "\n".join(lines[1:]).strip()
        else:
            # Generate a title from the beginning of the text
            title = text[:50] + "..." if len(text) > 50 else text
            content = text

        return ProcessedContent(
            content_type=ContentType.TEXT,
            title=title,
            source="text",
            content=content,
        )
