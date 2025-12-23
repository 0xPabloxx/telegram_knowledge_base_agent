"""Google Gemini LLM adapter using new google-genai SDK."""
from __future__ import annotations

import asyncio
import re
from typing import Optional

from google import genai
from google.genai import types

from .base import BaseLLM, LLMResponse


class GeminiLLM(BaseLLM):
    """LLM adapter for Google Gemini."""

    provider_name = "gemini"

    # Fallback models in order of preference
    FALLBACK_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ]

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        base_url: Optional[str] = None
    ):
        super().__init__(api_key, model, base_url)
        self.client = genai.Client(api_key=api_key)

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        """Send a chat completion request with retry and fallback."""
        # Try current model first, then fallbacks
        models_to_try = [self.model] + [m for m in self.FALLBACK_MODELS if m != self.model]

        last_error = None
        for model in models_to_try:
            try:
                return await self._chat_with_retry(messages, model, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e)
                # If rate limited, try next model
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    continue
                # Other errors, raise immediately
                raise

        # All models exhausted
        raise last_error

    async def _chat_with_retry(
        self,
        messages: list[dict],
        model: str,
        max_retries: int = 3,
        **kwargs
    ) -> LLMResponse:
        """Send chat with retry logic for rate limits."""
        # Extract system instruction and convert messages
        system_instruction = None
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg["content"])]
                ))
            elif msg["role"] == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(text=msg["content"])]
                ))

        # Build config
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
        )

        # Generate response - use full model path
        model_name = model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )

                # Extract usage
                usage = None
                if response.usage_metadata:
                    usage = {
                        "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                        "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                        "total_tokens": response.usage_metadata.total_token_count or 0,
                    }

                return LLMResponse(
                    content=response.text or "",
                    model=model,
                    provider=self.provider_name,
                    usage=usage
                )
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    # Extract retry delay if available
                    delay = self._extract_retry_delay(error_str)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        continue
                raise

        raise Exception(f"Max retries exceeded for model {model}")

    def _extract_retry_delay(self, error_str: str) -> float:
        """Extract retry delay from error message, default to exponential backoff."""
        # Try to find "retry in Xs" pattern
        match = re.search(r'retry.*?(\d+\.?\d*)s', error_str.lower())
        if match:
            return min(float(match.group(1)) + 1, 60)  # Add 1s buffer, max 60s
        return 5.0  # Default 5 seconds
