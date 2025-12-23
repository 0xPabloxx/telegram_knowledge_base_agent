"""File processor for PDFs, images, and other files."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from PIL import Image
import io

from .base import BaseProcessor, ProcessedContent, ContentType


class FileProcessor(BaseProcessor):
    """Processor for local files (PDF, images, etc.)."""

    SUPPORTED_EXTENSIONS = {
        # Documents
        ".pdf": ContentType.PDF,
        # Images
        ".jpg": ContentType.IMAGE,
        ".jpeg": ContentType.IMAGE,
        ".png": ContentType.IMAGE,
        ".gif": ContentType.IMAGE,
        ".webp": ContentType.IMAGE,
        ".bmp": ContentType.IMAGE,
    }

    async def can_process(self, input_str: str) -> bool:
        """Check if input is a valid file path."""
        input_str = input_str.strip()

        # Remove quotes that might come from drag-drop
        if (input_str.startswith("'") and input_str.endswith("'")) or \
           (input_str.startswith('"') and input_str.endswith('"')):
            input_str = input_str[1:-1]

        # Handle escaped spaces from drag-drop
        input_str = input_str.replace("\\ ", " ")

        # Check if it looks like a file path
        if input_str.startswith("http://") or input_str.startswith("https://"):
            return False

        # Check if it looks like a file path (starts with / or ~ or contains path separators)
        if not (input_str.startswith("/") or input_str.startswith("~") or
                input_str.startswith("./") or "/" in input_str or "\\" in input_str):
            return False

        path = Path(input_str).expanduser()
        if not path.exists():
            return False

        suffix = path.suffix.lower()
        return suffix in self.SUPPORTED_EXTENSIONS

    def is_file_path(self, input_str: str) -> bool:
        """Check if input looks like a file path (even if unsupported)."""
        input_str = input_str.strip()

        # Remove quotes
        if (input_str.startswith("'") and input_str.endswith("'")) or \
           (input_str.startswith('"') and input_str.endswith('"')):
            input_str = input_str[1:-1]

        input_str = input_str.replace("\\ ", " ")

        if input_str.startswith("http://") or input_str.startswith("https://"):
            return False

        path = Path(input_str).expanduser()
        return path.exists() and path.is_file()

    async def process(self, input_str: str) -> ProcessedContent:
        """Process a local file."""
        input_str = input_str.strip()

        # Remove quotes that might come from drag-drop
        if (input_str.startswith("'") and input_str.endswith("'")) or \
           (input_str.startswith('"') and input_str.endswith('"')):
            input_str = input_str[1:-1]

        # Handle escaped spaces from drag-drop
        input_str = input_str.replace("\\ ", " ")

        path = Path(input_str).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        content_type = self.SUPPORTED_EXTENSIONS.get(suffix, ContentType.FILE)
        mime_type, _ = mimetypes.guess_type(str(path))

        # Read file
        with open(path, "rb") as f:
            raw_data = f.read()

        file_size = len(raw_data)

        # Process based on type
        if content_type == ContentType.PDF:
            content, title = await self._process_pdf(path, raw_data)
        elif content_type == ContentType.IMAGE:
            content, title = await self._process_image(path, raw_data)
        else:
            content = ""
            title = path.stem

        return ProcessedContent(
            content_type=content_type,
            title=title or path.stem,
            source=str(path),
            content=content[:10000],  # Limit for LLM
            file_path=path,
            file_size=file_size,
            mime_type=mime_type,
            raw_data=raw_data,
        )

    async def _process_pdf(self, path: Path, raw_data: bytes) -> tuple[str, str]:
        """Extract text from PDF."""
        reader = PdfReader(io.BytesIO(raw_data))

        # Try to get title from metadata
        title = ""
        if reader.metadata:
            title = reader.metadata.get("/Title", "") or ""

        # Extract text from all pages
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        content = "\n\n".join(text_parts)

        return content, title

    async def _process_image(self, path: Path, raw_data: bytes) -> tuple[str, str]:
        """Process image file."""
        # Get basic image info
        img = Image.open(io.BytesIO(raw_data))
        width, height = img.size
        format_name = img.format or path.suffix.upper().replace(".", "")

        # Create a description for context
        content = f"Image: {path.name}\nFormat: {format_name}\nSize: {width}x{height} pixels"

        title = path.stem

        return content, title
