"""Tag system for content categorization."""
from __future__ import annotations

from typing import Optional

from .config import Config, add_preset_tag, load_config
from .llm import BaseLLM


class Tagger:
    """Tag management and suggestion system."""

    def __init__(self, config: Config, llm: Optional[BaseLLM] = None):
        self.config = config
        self.llm = llm

    @property
    def preset_tags(self) -> list[str]:
        """Get preset tags."""
        return self.config.tags.presets

    @property
    def allow_new(self) -> bool:
        """Check if new tags are allowed."""
        return self.config.tags.allow_new

    async def suggest_tags(self, content: str) -> list[str]:
        """Use LLM to suggest tags based on content.

        Args:
            content: The content to analyze

        Returns:
            List of suggested tags from presets
        """
        if not self.llm:
            return []

        if not content.strip():
            return []

        try:
            return await self.llm.suggest_tags(content, self.preset_tags)
        except Exception:
            return []

    async def generate_extra_tags(self, content: str, count: int = 5) -> list[str]:
        """Use LLM to generate additional tags beyond presets.

        Generates specific, searchable tags for better Telegram search.

        Args:
            content: The content to analyze
            count: Number of extra tags to generate

        Returns:
            List of newly generated tags (not in presets)
        """
        if not self.llm:
            return []

        if not content.strip():
            return []

        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""你是一个标签生成助手。为内容生成{count}个具体、可搜索的标签。

规则:
1. 生成具体的标签，如技术名称、产品名、概念等
2. 使用英文或中文单词，不要有空格
3. 标签要便于搜索，例如: LLM, GPT4, RAG, Agent, Python, 机器学习
4. 不要重复这些已有标签: {', '.join(self.preset_tags)}
5. 直接输出标签，用逗号分隔，不要解释"""
                },
                {
                    "role": "user",
                    "content": f"为以下内容生成{count}个标签：\n\n{content[:3000]}"
                }
            ]
            response = await self.llm.chat(messages)
            raw_tags = response.content.strip()

            # Parse tags
            import re
            tags = re.split(r'[,，\s]+', raw_tags)
            result = []

            for tag in tags:
                tag = tag.strip().strip('#')
                # Skip if empty, too long, or already in presets
                if tag and len(tag) <= 30 and tag not in self.preset_tags:
                    result.append(tag)

            return result[:count]
        except Exception:
            return []

    async def generate_tags_from_title(self, title: str, source: str = "") -> tuple[list[str], list[str]]:
        """Generate tags based on title and source when content is unavailable.

        Args:
            title: The title of the content
            source: Optional source URL or path

        Returns:
            Tuple of (preset_tags, extra_tags)
        """
        if not self.llm:
            return [], []

        if not title.strip():
            return [], []

        try:
            context = f"标题: {title}"
            if source:
                context += f"\n来源: {source}"

            tags_str = ", ".join(self.preset_tags)
            messages = [
                {
                    "role": "system",
                    "content": f"""你是一个内容分类专家。根据标题判断内容类别并生成标签。

预设标签: [{tags_str}]

任务:
1. 从预设标签中选择2-3个最相关的
2. 额外生成3-5个具体的技术/概念标签

输出格式 (严格遵守):
预设: tag1, tag2
额外: tag1, tag2, tag3"""
                },
                {
                    "role": "user",
                    "content": context
                }
            ]
            response = await self.llm.chat(messages)
            raw = response.content.strip()

            # Parse response
            import re
            preset_tags = []
            extra_tags = []

            for line in raw.split("\n"):
                line = line.strip()
                if line.startswith("预设:") or line.startswith("预设："):
                    tags_part = line.split(":", 1)[-1] if ":" in line else line.split("：", 1)[-1]
                    tags = re.split(r'[,，\s]+', tags_part)
                    for t in tags:
                        t = t.strip().strip('#')
                        if t and t in self.preset_tags:
                            preset_tags.append(t)
                elif line.startswith("额外:") or line.startswith("额外："):
                    tags_part = line.split(":", 1)[-1] if ":" in line else line.split("：", 1)[-1]
                    tags = re.split(r'[,，\s]+', tags_part)
                    for t in tags:
                        t = t.strip().strip('#')
                        if t and len(t) <= 30 and t not in self.preset_tags:
                            extra_tags.append(t)

            return preset_tags, extra_tags[:5]
        except Exception:
            return [], []

    def validate_tags(self, tags: list[str]) -> tuple[list[str], list[str]]:
        """Validate tags against presets.

        Args:
            tags: List of tags to validate

        Returns:
            Tuple of (valid_tags, new_tags)
        """
        valid_tags = []
        new_tags = []

        for tag in tags:
            tag = tag.strip()
            if not tag:
                continue

            # Remove # prefix if present
            if tag.startswith("#"):
                tag = tag[1:]

            if tag in self.preset_tags:
                valid_tags.append(tag)
            else:
                new_tags.append(tag)

        return valid_tags, new_tags

    def add_new_tag(self, tag: str) -> bool:
        """Add a new tag to presets.

        Args:
            tag: Tag to add

        Returns:
            True if tag was added, False if already exists or not allowed
        """
        if not self.allow_new:
            return False

        tag = tag.strip()
        if tag.startswith("#"):
            tag = tag[1:]

        if tag in self.preset_tags:
            return False

        add_preset_tag(tag)
        # Reload config to get updated presets
        self.config = load_config()
        return True

    def format_tags_display(self, suggested: list[str]) -> str:
        """Format tags for display in CLI.

        Args:
            suggested: Suggested tags from LLM

        Returns:
            Formatted string showing suggested and available tags
        """
        lines = []

        if suggested:
            suggested_str = " ".join(f"[{tag}]" for tag in suggested)
            lines.append(f"建议tag: {suggested_str}")

        all_tags = " | ".join(self.preset_tags)
        lines.append(f"预设tag: {all_tags}")

        return "\n".join(lines)

    def parse_user_input(self, user_input: str) -> list[str]:
        """Parse user input into list of tags.

        Args:
            user_input: Space or comma separated tags

        Returns:
            List of parsed tags
        """
        # Split by space or comma
        import re
        tags = re.split(r'[,\s]+', user_input)
        result = []

        for tag in tags:
            tag = tag.strip()
            if tag.startswith("#"):
                tag = tag[1:]
            if tag:
                result.append(tag)

        return result

    def process_tags(self, user_tags: list[str]) -> list[str]:
        """Process user-provided tags, adding new ones to presets if allowed.

        Args:
            user_tags: Tags from user input

        Returns:
            Final list of tags (all tags, including new ones)
        """
        valid_tags, new_tags = self.validate_tags(user_tags)

        # Add new tags to presets for future use
        if self.allow_new:
            for tag in new_tags:
                self.add_new_tag(tag)

        # Return all tags (both preset and new)
        return valid_tags + new_tags
