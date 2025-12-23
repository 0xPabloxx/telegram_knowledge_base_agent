"""Telegram channel publisher."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from .config import Config
from .processors.base import ProcessedContent, ContentType


class TelegramPublisher:
    """Publisher for Telegram channels."""

    def __init__(self, config: Config):
        self.config = config
        self.bot = Bot(token=config.telegram.bot_token)
        self.channel_id = config.telegram.channel_id

    async def publish(self, content: ProcessedContent) -> str:
        """Publish content to Telegram channel.

        Args:
            content: Processed content to publish

        Returns:
            URL to the published message
        """
        message_text = content.format_for_telegram()

        # Handle different content types
        if content.content_type == ContentType.IMAGE and content.file_path:
            return await self._publish_image(content, message_text)
        elif content.content_type == ContentType.PDF and content.file_path:
            return await self._publish_document(content, message_text)
        else:
            return await self._publish_text(message_text)

    async def _publish_text(self, text: str) -> str:
        """Publish text message."""
        message = await self.bot.send_message(
            chat_id=self.channel_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False,
        )
        return self._get_message_url(message.message_id)

    async def _publish_image(self, content: ProcessedContent, caption: str) -> str:
        """Publish image with caption."""
        with open(content.file_path, "rb") as f:
            message = await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=f,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
        return self._get_message_url(message.message_id)

    async def _publish_document(self, content: ProcessedContent, caption: str) -> str:
        """Publish document with caption."""
        with open(content.file_path, "rb") as f:
            message = await self.bot.send_document(
                chat_id=self.channel_id,
                document=f,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
        return self._get_message_url(message.message_id)

    def _get_message_url(self, message_id: int) -> str:
        """Get URL to the published message."""
        channel = self.channel_id
        if channel.startswith("@"):
            channel_name = channel[1:]
            return f"https://t.me/{channel_name}/{message_id}"
        else:
            # For private channels with numeric ID
            # Remove -100 prefix if present
            channel_id = str(channel)
            if channel_id.startswith("-100"):
                channel_id = channel_id[4:]
            return f"https://t.me/c/{channel_id}/{message_id}"

    async def test_connection(self) -> bool:
        """Test connection to Telegram.

        Returns:
            True if connection is successful
        """
        try:
            me = await self.bot.get_me()
            return me is not None
        except Exception:
            return False

    async def get_channel_info(self) -> Optional[dict]:
        """Get channel information.

        Returns:
            Channel info dict or None if failed
        """
        try:
            chat = await self.bot.get_chat(self.channel_id)
            return {
                "id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "username": chat.username,
            }
        except Exception:
            return None
