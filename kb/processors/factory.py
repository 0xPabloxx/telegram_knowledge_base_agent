"""Factory for content processing."""
from __future__ import annotations

from pathlib import Path

from .base import ProcessedContent
from .link import LinkProcessor, extract_urls
from .file import FileProcessor
from .text import TextProcessor


class UnsupportedFileError(Exception):
    """Raised when a file type is not supported."""
    pass


def _clean_path(input_str: str) -> str:
    """Clean file path from drag-drop artifacts."""
    input_str = input_str.strip()

    # Remove quotes
    if (input_str.startswith("'") and input_str.endswith("'")) or \
       (input_str.startswith('"') and input_str.endswith('"')):
        input_str = input_str[1:-1]

    # Handle escaped spaces
    input_str = input_str.replace("\\ ", " ")

    return input_str


def _is_file_path(input_str: str) -> tuple[bool, Path | None]:
    """Check if input looks like a file path."""
    cleaned = _clean_path(input_str)

    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return False, None

    # Check if it looks like a path
    if not (cleaned.startswith("/") or cleaned.startswith("~") or
            cleaned.startswith("./") or "/" in cleaned):
        return False, None

    path = Path(cleaned).expanduser()
    if path.exists() and path.is_file():
        return True, path

    return False, None


async def detect_and_process(input_str: str) -> ProcessedContent:
    """Detect input type and process accordingly.

    Processing order:
    1. Link (URL) - also handles URL mixed with text
    2. File (local file path)
    3. Text (fallback)

    Args:
        input_str: User input (URL, file path, or text)

    Returns:
        Processed content ready for summarization and publishing

    Raises:
        UnsupportedFileError: If a file type is not supported
    """
    input_str = input_str.strip()

    # Check if it's a file path first (for better error messages)
    is_file, file_path = _is_file_path(input_str)
    if is_file and file_path:
        file_processor = FileProcessor()
        if await file_processor.can_process(input_str):
            return await file_processor.process(input_str)
        else:
            # File exists but not supported
            suffix = file_path.suffix.lower()
            supported = ", ".join(FileProcessor.SUPPORTED_EXTENSIONS.keys())
            raise UnsupportedFileError(
                f"不支持的文件类型: {suffix}\n"
                f"文件: {file_path.name}\n"
                f"支持的类型: {supported}"
            )

    # Try link processor for pure URL
    link_processor = LinkProcessor()
    if await link_processor.can_process(input_str):
        return await link_processor.process(input_str)

    # Check if there's a URL embedded in text
    urls = extract_urls(input_str)
    if urls:
        # Extract the first URL and process it
        url = urls[0]
        # Get the extra text (context) by removing the URL
        extra_text = input_str.replace(url, "").strip()

        # Process the URL
        content = await link_processor.process(url)

        # If there's extra text, append it to the content for better context
        if extra_text:
            content.content = f"{extra_text}\n\n{content.content}"

        return content

    # Fallback to text
    text_processor = TextProcessor()
    return await text_processor.process(input_str)


def detect_input_type(input_str: str) -> str:
    """Quickly detect the input type without processing.

    Returns:
        'link', 'file', 'unsupported_file', or 'text'
    """
    input_str = input_str.strip()

    # Check for URL
    if input_str.startswith("http://") or input_str.startswith("https://"):
        return "link"

    # Check for file path
    is_file, file_path = _is_file_path(input_str)
    if is_file and file_path:
        suffix = file_path.suffix.lower()
        if suffix in FileProcessor.SUPPORTED_EXTENSIONS:
            return "file"
        else:
            return "unsupported_file"

    return "text"
