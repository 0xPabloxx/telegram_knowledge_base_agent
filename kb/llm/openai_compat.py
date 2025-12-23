"""OpenAI-compatible LLM adapter.

Works with:
- OpenAI (ChatGPT)
- DeepSeek
- Kimi (Moonshot)
- MiniMax
- GLM (Zhipu)
- Any OpenAI-compatible API
"""
from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from .base import BaseLLM, LLMResponse


class OpenAICompatibleLLM(BaseLLM):
    """LLM adapter for OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        provider_name: str = "openai"
    ):
        super().__init__(api_key, model, base_url)
        self.provider_name = provider_name
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        """Send a chat completion request."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider_name,
            usage=usage
        )


class DeepSeekLLM(OpenAICompatibleLLM):
    """DeepSeek LLM adapter."""

    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url or "https://api.deepseek.com/v1",
            provider_name="deepseek"
        )


class KimiLLM(OpenAICompatibleLLM):
    """Kimi (Moonshot) LLM adapter."""

    def __init__(self, api_key: str, model: str = "moonshot-v1-8k", base_url: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url or "https://api.moonshot.cn/v1",
            provider_name="kimi"
        )


class MiniMaxLLM(OpenAICompatibleLLM):
    """MiniMax LLM adapter."""

    def __init__(self, api_key: str, model: str = "abab6.5s-chat", base_url: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url or "https://api.minimax.chat/v1",
            provider_name="minimax"
        )


class GLMLLM(OpenAICompatibleLLM):
    """GLM (Zhipu) LLM adapter."""

    def __init__(self, api_key: str, model: str = "glm-4-flash", base_url: Optional[str] = None):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url or "https://open.bigmodel.cn/api/paas/v4",
            provider_name="glm"
        )
