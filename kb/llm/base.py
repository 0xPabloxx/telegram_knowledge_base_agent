"""Base class for LLM adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    provider: str
    usage: Optional[dict] = None


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str = "base"

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        """Send a chat completion request."""
        pass

    async def summarize(self, content: str, max_length: int = 200) -> str:
        """Generate a summary of the content (Chinese only, for backward compatibility)."""
        result = await self.summarize_bilingual(content, max_length)
        return result.get("summary_cn", "")

    async def summarize_bilingual(
        self,
        content: str,
        max_length: int = 200,
        original_title: str = ""
    ) -> dict:
        """Generate bilingual summaries and titles.

        Args:
            content: The content to summarize
            max_length: Maximum length for summaries
            original_title: Optional original title to translate (instead of generating new one)

        Returns:
            dict with keys: title_cn, summary_cn, title_en, summary_en
        """
        # If we have an original title, ask LLM to translate it
        if original_title:
            system_prompt = f"""你是专业翻译。任务：翻译标题+生成摘要。

【必须翻译的原始标题】: {original_title}

【输出格式】:
标题中文: <在这里写原始标题的完整中文翻译>
摘要中文: <中文摘要，不超过{max_length}字>
标题英文: {original_title}
摘要英文: <English summary, max {max_length} words>

【翻译示例】:
- "Attention Is All You Need" → "注意力机制是你所需要的一切"
- "Stabilizing Reinforcement Learning with LLMs: Formulation and Practices" → "稳定大语言模型强化学习：公式化方法与实践"
- "Chain-of-Thought Prompting Elicits Reasoning" → "思维链提示激发推理能力"

【严格要求】:
- 中文标题必须翻译原标题的【所有单词】，不能遗漏任何部分
- 如果原标题是 "A: B" 格式，中文也必须是 "A：B" 格式
- 英文标题保持原样不变：{original_title}"""
        else:
            system_prompt = f"""你是一个双语内容摘要专家。请为内容生成中英双语的标题和摘要。

输出格式（严格遵守）:
标题中文: [中文标题，简洁有力，不超过30字]
摘要中文: [中文摘要，不超过{max_length}字]
标题英文: [English title, concise and informative]
摘要英文: [English summary, max {max_length} words]

要求:
1. 标题要简洁有力，能概括内容核心
2. 摘要要抓住重点，突出价值和亮点
3. 中英文内容要对应，但不必是直译
4. 直接按格式输出，不要有其他内容"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下内容生成双语标题和摘要：\n\n{content[:5000]}"}
        ]
        response = await self.chat(messages)
        raw = response.content.strip()

        # Parse response
        result = {
            "title_cn": "",
            "summary_cn": "",
            "title_en": original_title,  # Default to original title
            "summary_en": ""
        }

        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("标题中文:") or line.startswith("标题中文："):
                result["title_cn"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            elif line.startswith("摘要中文:") or line.startswith("摘要中文："):
                result["summary_cn"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            elif line.startswith("标题英文:") or line.startswith("标题英文："):
                result["title_en"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            elif line.startswith("摘要英文:") or line.startswith("摘要英文："):
                result["summary_en"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()

        # Ensure English title falls back to original if not parsed
        if not result["title_en"] and original_title:
            result["title_en"] = original_title

        # Validate Chinese title - if too short, it's probably incomplete
        if original_title and result["title_cn"]:
            en_word_count = len(original_title.split())
            cn_char_count = len(result["title_cn"])
            # If Chinese title has fewer chars than English words, it's likely incomplete
            # A proper translation should have at least 1.5x chars as English words
            if cn_char_count < en_word_count * 1.2:
                # Try to generate a better translation
                result["title_cn"] = await self._translate_title(original_title)

        return result

    async def _translate_title(self, title: str) -> str:
        """Translate a title from English to Chinese."""
        messages = [
            {
                "role": "system",
                "content": "你是翻译专家。将英文标题翻译为中文，要求完整准确，不遗漏任何单词。只输出翻译结果，不要其他内容。"
            },
            {
                "role": "user",
                "content": f"翻译: {title}"
            }
        ]
        response = await self.chat(messages)
        return response.content.strip()

    async def suggest_tags(self, content: str, preset_tags: list[str]) -> list[str]:
        """Suggest tags for the content based on preset tags.

        Returns ALL matching preset tags, no limit on number.
        """
        tags_str = ", ".join(preset_tags)
        messages = [
            {
                "role": "system",
                "content": f"""你是一个内容分类专家。你的任务是分析内容并从预设标签中选择所有相关的标签。

预设标签列表: [{tags_str}]

分析步骤:
1. 仔细阅读内容，理解其主题、领域和关键概念
2. 对照每个预设标签，判断内容是否与该标签相关
3. 选择所有相关的标签（不限数量，只要相关就选）

标签含义参考:
- AI: 人工智能相关
- LLM: 大语言模型相关
- VLM: 视觉语言模型相关
- Agent: AI Agent、智能体相关
- Paper: 学术论文
- 预训练/后训练: 模型训练相关
- 强化学习/RL: 强化学习相关
- 多模态/Multi-modal: 多模态相关
- Research: 研究相关
- Tutorial: 教程相关
- Programming: 编程相关
- Model: 模型相关
- Dataset: 数据集相关

输出要求:
- 只输出标签名，用英文逗号分隔
- 必须从预设标签中选择，完全匹配（包括大小写）
- 选择所有相关的标签，不要遗漏
- 不要输出任何解释"""
            },
            {
                "role": "user",
                "content": f"分析以下内容并选择所有相关的预设标签：\n\n{content[:3000]}"
            }
        ]
        response = await self.chat(messages)
        # Parse tags from response
        raw_tags = response.content.strip()
        tags = [t.strip() for t in raw_tags.replace("，", ",").split(",")]
        # Filter to only include valid preset tags (case-insensitive matching)
        preset_lower = {t.lower(): t for t in preset_tags}
        valid_tags = []
        for t in tags:
            if t in preset_tags:
                valid_tags.append(t)
            elif t.lower() in preset_lower:
                valid_tags.append(preset_lower[t.lower()])
        return valid_tags if valid_tags else []
