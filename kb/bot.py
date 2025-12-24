"""Telegram Bot service for KB."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional
from dataclasses import dataclass, field

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

from .config import load_config, Config
from .llm import create_llm, BaseLLM
from .processors import detect_and_process, extract_urls, ProcessedContent
from .tagger import Tagger
from .publisher import TelegramPublisher

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@dataclass
class PendingContent:
    """Content pending for tag selection and publishing."""
    content: ProcessedContent
    suggested_tags: list[str] = field(default_factory=list)
    extra_tags: list[str] = field(default_factory=list)
    selected_tags: set[str] = field(default_factory=set)
    message_id: Optional[int] = None


class KBBot:
    """Telegram Bot for KB publishing."""

    def __init__(self, config: Config):
        self.config = config
        self.llm: Optional[BaseLLM] = None
        self.tagger: Optional[Tagger] = None
        self.publisher: Optional[TelegramPublisher] = None
        self.application: Optional[Application] = None

        # Pending contents per user (chat_id -> PendingContent)
        self.pending: dict[int, PendingContent] = {}

        # Bot settings
        self.admin_user_id = self._get_admin_user_id()
        self.auto_publish = os.environ.get("KB_BOT_AUTO_PUBLISH", "false").lower() == "true"

    def _get_admin_user_id(self) -> Optional[int]:
        """Get admin user ID from environment."""
        user_id = os.environ.get("KB_BOT_ADMIN_USER_ID", "")
        if user_id:
            try:
                return int(user_id)
            except ValueError:
                logger.warning(f"Invalid KB_BOT_ADMIN_USER_ID: {user_id}")
        return None

    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized to use the bot."""
        if self.admin_user_id is None:
            # No admin configured, allow all (with warning)
            return True
        return user_id == self.admin_user_id

    async def initialize(self) -> bool:
        """Initialize bot services."""
        # Initialize LLM
        try:
            self.llm = create_llm(self.config)
            logger.info(f"LLM initialized: {self.config.llm.default_provider}")
        except ValueError as e:
            logger.warning(f"LLM not available: {e}")
            self.llm = None

        # Initialize tagger
        self.tagger = Tagger(self.config, self.llm)

        # Initialize publisher
        if self.config.telegram.bot_token and self.config.telegram.channel_id:
            self.publisher = TelegramPublisher(self.config)
            logger.info(f"Publisher initialized for channel: {self.config.telegram.channel_id}")
        else:
            logger.error("Telegram not configured")
            return False

        # Initialize application
        self.application = (
            Application.builder()
            .token(self.config.telegram.bot_token)
            .build()
        )

        # Add handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("mode", self.cmd_mode))
        self.application.add_handler(CommandHandler("cancel", self.cmd_cancel))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        return True

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user

        if not self._is_authorized(user.id):
            await update.message.reply_text("⛔ 你没有权限使用此 Bot")
            return

        mode_text = "🚀 直接发布" if self.auto_publish else "👀 预览确认"
        await update.message.reply_text(
            f"👋 你好 {user.first_name}!\n\n"
            f"发送链接给我，我会自动解析并发布到频道。\n\n"
            f"当前模式: {mode_text}\n\n"
            f"命令:\n"
            f"/mode - 切换发布模式\n"
            f"/cancel - 取消当前操作\n"
            f"/help - 帮助信息"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ 你没有权限使用此 Bot")
            return

        await update.message.reply_text(
            "📖 使用说明\n\n"
            "1. 直接发送链接\n"
            "2. 等待解析和摘要生成\n"
            "3. 选择标签（点击按钮）\n"
            "4. 确认发布\n\n"
            "支持的链接类型:\n"
            "• 普通网页\n"
            "• ArXiv 论文\n"
            "• 微信公众号文章\n"
            "• 知乎（受限）\n\n"
            "命令:\n"
            "/mode - 切换直接发布/预览确认模式\n"
            "/cancel - 取消当前操作"
        )

    async def cmd_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle publish mode."""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ 你没有权限使用此 Bot")
            return

        self.auto_publish = not self.auto_publish
        mode_text = "🚀 直接发布" if self.auto_publish else "👀 预览确认"
        await update.message.reply_text(f"已切换到: {mode_text}")

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation."""
        chat_id = update.effective_chat.id
        if chat_id in self.pending:
            del self.pending[chat_id]
            await update.message.reply_text("✅ 已取消")
        else:
            await update.message.reply_text("没有进行中的操作")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (links)."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        text = update.message.text.strip()

        if not self._is_authorized(user.id):
            await update.message.reply_text("⛔ 你没有权限使用此 Bot")
            return

        # Extract URLs from message
        urls = extract_urls(text)
        if not urls:
            await update.message.reply_text(
                "请发送有效的链接\n"
                "例如: https://example.com/article"
            )
            return

        # Process first URL (or the whole text if single URL)
        input_to_process = urls[0] if len(urls) == 1 else text

        if len(urls) > 1:
            await update.message.reply_text(
                f"检测到 {len(urls)} 个链接，将处理第一个:\n{urls[0]}"
            )

        # Send processing status
        status_msg = await update.message.reply_text("⏳ 正在解析...")

        try:
            # Process content
            content = await detect_and_process(input_to_process)

            await status_msg.edit_text("⏳ 正在生成摘要...")

            # Generate bilingual summary
            original_title = content.title
            if self.llm and content.content:
                try:
                    bilingual = await self.llm.summarize_bilingual(
                        content.content,
                        original_title=original_title
                    )
                    if bilingual.get("title_cn"):
                        content.title = bilingual["title_cn"]
                    content.summary = bilingual.get("summary_cn", "")
                    content.title_en = bilingual.get("title_en") or original_title
                    content.summary_en = bilingual.get("summary_en", "")
                except Exception as e:
                    logger.warning(f"Summary generation failed: {e}")

            await status_msg.edit_text("⏳ 正在分析标签...")

            # Get tag suggestions
            suggested_tags = []
            extra_tags = []

            if self.llm and content.content:
                try:
                    suggested_tags = await self.tagger.suggest_tags(content.content)
                    extra_tags = await self.tagger.generate_extra_tags(content.content)
                except Exception:
                    pass

            # Fallback to title-based tags
            if self.llm and not suggested_tags:
                try:
                    suggested_tags, extra_tags = await self.tagger.generate_tags_from_title(
                        content.title, content.source
                    )
                except Exception:
                    pass

            # Delete status message
            await status_msg.delete()

            # Auto publish mode
            if self.auto_publish:
                content.tags = suggested_tags + extra_tags
                await self._publish_content(update, content)
                return

            # Preview mode - show content and tag selection
            all_tags = suggested_tags + extra_tags
            pending = PendingContent(
                content=content,
                suggested_tags=suggested_tags,
                extra_tags=extra_tags,
                selected_tags=set(all_tags),  # Pre-select all suggested tags
            )
            self.pending[chat_id] = pending

            # Show preview with tag selection
            await self._show_preview(update, pending)

        except Exception as e:
            logger.error(f"Processing error: {e}")
            await status_msg.edit_text(f"❌ 处理失败: {e}")

    async def _show_preview(self, update: Update, pending: PendingContent):
        """Show content preview with tag selection buttons."""
        content = pending.content

        # Format preview message
        preview_lines = [
            f"📌 *{self._escape_md(content.title)}*",
        ]

        if content.summary:
            preview_lines.append(f"📝 {self._escape_md(content.summary[:200])}")

        if content.source and content.source != "text":
            preview_lines.append(f"🔗 {content.source}")

        if content.title_en and content.title_en != content.title:
            preview_lines.append("")
            preview_lines.append("─" * 20)
            preview_lines.append("")
            preview_lines.append(f"📌 *{self._escape_md(content.title_en)}*")
            if content.summary_en:
                preview_lines.append(f"📝 {self._escape_md(content.summary_en[:200])}")

        preview_text = "\n".join(preview_lines)

        # Create tag selection keyboard
        keyboard = self._create_tag_keyboard(pending)

        # Send or edit message
        if pending.message_id:
            await update.callback_query.edit_message_text(
                preview_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        else:
            msg = await update.message.reply_text(
                preview_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            pending.message_id = msg.message_id

    def _create_tag_keyboard(self, pending: PendingContent) -> InlineKeyboardMarkup:
        """Create inline keyboard for tag selection."""
        keyboard = []

        # Combine all tags (preset suggestions + extra)
        all_tags = []

        # Add preset tags that are suggested
        for tag in pending.suggested_tags:
            if tag in self.tagger.preset_tags:
                all_tags.append(tag)

        # Add extra generated tags
        all_tags.extend(pending.extra_tags)

        # Add remaining preset tags
        for tag in self.tagger.preset_tags:
            if tag not in all_tags:
                all_tags.append(tag)

        # Create tag buttons (3 per row)
        row = []
        for tag in all_tags[:12]:  # Limit to 12 tags
            is_selected = tag in pending.selected_tags
            button_text = f"✓ {tag}" if is_selected else tag
            row.append(InlineKeyboardButton(button_text, callback_data=f"tag:{tag}"))

            if len(row) == 3:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        # Add action buttons
        selected_count = len(pending.selected_tags)
        keyboard.append([
            InlineKeyboardButton("🔄 清空", callback_data="clear"),
            InlineKeyboardButton("✅ 全选", callback_data="select_all"),
        ])
        keyboard.append([
            InlineKeyboardButton(f"📤 发布 ({selected_count})", callback_data="publish"),
            InlineKeyboardButton("❌ 取消", callback_data="cancel"),
        ])

        return InlineKeyboardMarkup(keyboard)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            return

        pending = self.pending.get(chat_id)
        if not pending:
            await query.edit_message_text("操作已过期，请重新发送链接")
            return

        data = query.data

        if data.startswith("tag:"):
            # Toggle tag selection
            tag = data[4:]
            if tag in pending.selected_tags:
                pending.selected_tags.discard(tag)
            else:
                pending.selected_tags.add(tag)

            # Update keyboard
            keyboard = self._create_tag_keyboard(pending)
            await query.edit_message_reply_markup(reply_markup=keyboard)

        elif data == "clear":
            # Clear all selected tags
            pending.selected_tags.clear()
            keyboard = self._create_tag_keyboard(pending)
            await query.edit_message_reply_markup(reply_markup=keyboard)

        elif data == "select_all":
            # Select all suggested tags
            all_tags = pending.suggested_tags + pending.extra_tags
            for tag in self.tagger.preset_tags[:12]:
                if tag not in all_tags:
                    all_tags.append(tag)
            pending.selected_tags = set(all_tags[:12])
            keyboard = self._create_tag_keyboard(pending)
            await query.edit_message_reply_markup(reply_markup=keyboard)

        elif data == "publish":
            # Publish with selected tags
            pending.content.tags = list(pending.selected_tags)
            await self._publish_content_callback(query, pending.content)
            del self.pending[chat_id]

        elif data == "cancel":
            # Cancel operation
            del self.pending[chat_id]
            await query.edit_message_text("❌ 已取消")

    async def _publish_content(self, update: Update, content: ProcessedContent):
        """Publish content to channel."""
        try:
            url = await self.publisher.publish(content)

            tags_display = " ".join(f"#{tag}" for tag in content.tags) if content.tags else ""
            await update.message.reply_text(
                f"✅ 已发布!\n\n"
                f"🏷️ {tags_display}\n\n"
                f"🔗 {url}"
            )
        except Exception as e:
            logger.error(f"Publish error: {e}")
            await update.message.reply_text(f"❌ 发布失败: {e}")

    async def _publish_content_callback(self, query, content: ProcessedContent):
        """Publish content from callback query."""
        try:
            url = await self.publisher.publish(content)

            tags_display = " ".join(f"#{tag}" for tag in content.tags) if content.tags else ""
            await query.edit_message_text(
                f"✅ 已发布!\n\n"
                f"🏷️ {tags_display}\n\n"
                f"🔗 {url}"
            )
        except Exception as e:
            logger.error(f"Publish error: {e}")
            await query.edit_message_text(f"❌ 发布失败: {e}")

    def _escape_md(self, text: str) -> str:
        """Escape markdown special characters."""
        if not text:
            return ""
        # Only escape characters that need escaping in Markdown V1
        for char in ['_', '*', '[', ']', '`']:
            text = text.replace(char, f'\\{char}')
        return text

    async def run(self):
        """Run the bot."""
        if not await self.initialize():
            logger.error("Failed to initialize bot")
            return

        logger.info("Starting bot...")

        if self.admin_user_id:
            logger.info(f"Admin user ID: {self.admin_user_id}")
        else:
            logger.warning("No admin user ID configured. Bot is open to all users!")
            logger.warning("Set KB_BOT_ADMIN_USER_ID to restrict access.")

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)

        logger.info("Bot is running. Press Ctrl+C to stop.")

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


def run_bot():
    """Entry point for running the bot."""
    config = load_config()

    if not config.telegram.bot_token:
        print("Error: KB_TELEGRAM_BOT_TOKEN not configured")
        print("Set it in .env or environment variables")
        return

    if not config.telegram.channel_id:
        print("Error: KB_TELEGRAM_CHANNEL_ID not configured")
        print("Set it in .env or environment variables")
        return

    bot = KBBot(config)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nBot stopped.")


if __name__ == "__main__":
    run_bot()
