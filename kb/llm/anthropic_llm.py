"""Anthropic Claude LLM adapter."""
from __future__ import annotations

from typing import Optional

from anthropic import AsyncAnthropic

from .base import BaseLLM, LLMResponse


class AnthropicLLM(BaseLLM):
    """LLM adapter for Anthropic Claude."""

    provider_name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: Optional[str] = None
    ):
        super().__init__(api_key, model, base_url)
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url
        )

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        """Send a chat completion request."""
        # Extract system message if present
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        # Build request kwargs
        request_kwargs = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": chat_messages,
        }

        if system_message:
            request_kwargs["system"] = system_message

        response = await self.client.messages.create(**request_kwargs)

        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.provider_name,
            usage=usage
        )
