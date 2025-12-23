"""Base class for content processors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# Chinese-English tag mapping for auto-translation
TAG_TRANSLATIONS = {
    # Chinese → English
    "多模态": "Multimodal",
    "智能体": "Agent",
    "大模型": "LLM",
    "大语言模型": "LLM",
    "视觉语言模型": "VLM",
    "预训练": "Pretraining",
    "后训练": "Post-training",
    "强化学习": "RL",
    "微调": "Finetuning",
    "提示词": "Prompt",
    "检索增强": "RAG",
    "论文": "Paper",
    "工具": "Tools",
    "教程": "Tutorial",
    "文章": "Article",
    "研究": "Research",
    "编程": "Programming",
    "产品": "Product",
    "设计": "Design",
    "新闻": "News",
    "观点": "Opinion",
    "开源": "OpenSource",
    "模型": "Model",
    "数据集": "Dataset",
    "推理": "Inference",
    "训练": "Training",
    "部署": "Deployment",
    "评测": "Benchmark",
    "对齐": "Alignment",
    "安全": "Safety",
    # English → Chinese
    "Multimodal": "多模态",
    "Multi-modal": "多模态",
    "Agent": "智能体",
    "LLM": "大语言模型",
    "VLM": "视觉语言模型",
    "Pretraining": "预训练",
    "Pre-training": "预训练",
    "Post-training": "后训练",
    "RL": "强化学习",
    "Finetuning": "微调",
    "Fine-tuning": "微调",
    "Prompt": "提示词",
    "RAG": "检索增强",
    "Paper": "论文",
    "Tools": "工具",
    "Tutorial": "教程",
    "Article": "文章",
    "Research": "研究",
    "Programming": "编程",
    "Product": "产品",
    "Design": "设计",
    "News": "新闻",
    "Opinion": "观点",
    "OpenSource": "开源",
    "Model": "模型",
    "Dataset": "数据集",
    "Inference": "推理",
    "Training": "训练",
    "Deployment": "部署",
    "Benchmark": "评测",
    "Alignment": "对齐",
    "Safety": "安全",
    "AI": "人工智能",
}


def get_tag_translation(tag: str) -> Optional[str]:
    """Get translation for a tag if available."""
    # Try exact match first
    if tag in TAG_TRANSLATIONS:
        return TAG_TRANSLATIONS[tag]
    # Try case-insensitive match
    tag_lower = tag.lower()
    for k, v in TAG_TRANSLATIONS.items():
        if k.lower() == tag_lower:
            return v
    return None


class ContentType(Enum):
    """Type of content being processed."""
    LINK = "link"
    FILE = "file"
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"


@dataclass
class ProcessedContent:
    """Processed content ready for publishing."""
    content_type: ContentType
    title: str
    source: str  # URL or file path
    content: str  # Main content text (for summarization)
    summary: Optional[str] = None  # Generated Chinese summary
    tags: list[str] = field(default_factory=list)

    # English versions
    title_en: Optional[str] = None
    summary_en: Optional[str] = None

    # For file-based content
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None

    # For images
    image_description: Optional[str] = None

    # Original raw data
    raw_data: Optional[bytes] = None

    def _get_chinese_tags(self) -> list[str]:
        """Get Chinese tags with translations."""
        chinese_tags = []
        seen = set()
        for tag in self.tags:
            # Remove hyphens for Telegram compatibility
            clean_tag = tag.replace("-", "")
            if not clean_tag:
                continue

            # If tag is Chinese, use directly
            if not clean_tag.isascii():
                if clean_tag not in seen:
                    chinese_tags.append(f"#{clean_tag}")
                    seen.add(clean_tag)
            else:
                # English tag - try to translate to Chinese
                translation = get_tag_translation(tag)
                if translation and not translation.isascii():
                    if translation not in seen:
                        chinese_tags.append(f"#{translation}")
                        seen.add(translation)
                # Also keep the English tag (without hyphen)
                if clean_tag not in seen:
                    chinese_tags.append(f"#{clean_tag}")
                    seen.add(clean_tag)
        return chinese_tags

    def _get_english_tags(self) -> list[str]:
        """Get English tags with translations."""
        english_tags = []
        seen = set()
        for tag in self.tags:
            # If tag is English/ASCII, use directly
            if tag.isascii():
                # Remove hyphens for Telegram compatibility
                clean_tag = tag.replace("-", "")
                if clean_tag and clean_tag not in seen:
                    english_tags.append(f"#{clean_tag}")
                    seen.add(clean_tag)
                # Add lowercase variant
                if clean_tag:
                    variant = clean_tag.lower() if clean_tag[0].isupper() else clean_tag.capitalize()
                    if variant != clean_tag and variant not in seen:
                        english_tags.append(f"#{variant}")
                        seen.add(variant)
            else:
                # Chinese tag - try to translate to English
                translation = get_tag_translation(tag)
                if translation and translation.isascii():
                    # Remove hyphens for Telegram compatibility
                    clean_trans = translation.replace("-", "")
                    if clean_trans and clean_trans not in seen:
                        english_tags.append(f"#{clean_trans}")
                        seen.add(clean_trans)
                    # Add lowercase variant
                    if clean_trans:
                        variant = clean_trans.lower() if clean_trans[0].isupper() else clean_trans.capitalize()
                        if variant != clean_trans and variant not in seen:
                            english_tags.append(f"#{variant}")
                            seen.add(variant)
        return english_tags

    def format_for_telegram(self) -> str:
        """Format the content for Telegram message in bilingual format."""
        lines = []

        # === Chinese Section ===
        # Chinese title
        cn_title = self.title
        lines.append(f"📌 {cn_title}")
        lines.append("")

        # Chinese summary
        if self.summary:
            lines.append(f"📝 {self.summary}")
            lines.append("")

        # Source link (Chinese section)
        if self.source:
            if self.content_type == ContentType.LINK:
                lines.append(f"🔗 {self.source}")
            elif self.file_path:
                lines.append(f"📎 {self.file_path.name}")
            else:
                lines.append(f"🔗 {self.source}")
            lines.append("")

        # Chinese tags
        cn_tags = self._get_chinese_tags()
        if cn_tags:
            lines.append(f"🏷️ {' '.join(cn_tags)}")

        # Separator
        lines.append("")
        lines.append("─" * 20)
        lines.append("")

        # === English Section ===
        # English title
        en_title = self.title_en or self.title
        lines.append(f"📌 {en_title}")
        lines.append("")

        # English summary
        if self.summary_en:
            lines.append(f"📝 {self.summary_en}")
            lines.append("")
        elif self.summary:
            lines.append(f"📝 {self.summary}")
            lines.append("")

        # Source link (English section)
        if self.source:
            if self.content_type == ContentType.LINK:
                lines.append(f"🔗 {self.source}")
            elif self.file_path:
                lines.append(f"📎 {self.file_path.name}")
            else:
                lines.append(f"🔗 {self.source}")
            lines.append("")

        # English tags
        en_tags = self._get_english_tags()
        if en_tags:
            lines.append(f"🏷️ {' '.join(en_tags)}")

        return "\n".join(lines)


class BaseProcessor(ABC):
    """Abstract base class for content processors."""

    @abstractmethod
    async def can_process(self, input_str: str) -> bool:
        """Check if this processor can handle the input."""
        pass

    @abstractmethod
    async def process(self, input_str: str) -> ProcessedContent:
        """Process the input and return structured content."""
        pass
