"""Factory for creating LLM instances."""
from __future__ import annotations

from typing import Optional

from ..config import Config, LLMProviderConfig, get_provider_config
from .base import BaseLLM
from .openai_compat import (
    OpenAICompatibleLLM,
    DeepSeekLLM,
    KimiLLM,
    MiniMaxLLM,
    GLMLLM,
)
from .anthropic_llm import AnthropicLLM
from .gemini_llm import GeminiLLM


def create_llm(config: Config, provider: Optional[str] = None) -> BaseLLM:
    """Create an LLM instance based on configuration.

    Args:
        config: Application configuration
        provider: Optional provider name override. If not specified,
                  uses config.llm.default_provider

    Returns:
        An LLM instance for the specified provider

    Raises:
        ValueError: If provider is unknown or API key is missing
    """
    provider_name, provider_config = get_provider_config(config, provider)

    if not provider_config.api_key:
        raise ValueError(
            f"API key not configured for provider '{provider_name}'. "
            f"Set it in ~/.kb/config.yaml or via environment variable."
        )

    return _create_provider_llm(provider_name, provider_config)


def _create_provider_llm(provider_name: str, config: LLMProviderConfig) -> BaseLLM:
    """Create LLM instance for a specific provider."""
    factories = {
        "openai": lambda c: OpenAICompatibleLLM(
            api_key=c.api_key,
            model=c.model,
            base_url=c.base_url,
            provider_name="openai"
        ),
        "anthropic": lambda c: AnthropicLLM(
            api_key=c.api_key,
            model=c.model,
            base_url=c.base_url
        ),
        "gemini": lambda c: GeminiLLM(
            api_key=c.api_key,
            model=c.model
        ),
        "deepseek": lambda c: DeepSeekLLM(
            api_key=c.api_key,
            model=c.model,
            base_url=c.base_url
        ),
        "kimi": lambda c: KimiLLM(
            api_key=c.api_key,
            model=c.model,
            base_url=c.base_url
        ),
        "minimax": lambda c: MiniMaxLLM(
            api_key=c.api_key,
            model=c.model,
            base_url=c.base_url
        ),
        "glm": lambda c: GLMLLM(
            api_key=c.api_key,
            model=c.model,
            base_url=c.base_url
        ),
    }

    factory = factories.get(provider_name)
    if factory is None:
        raise ValueError(f"Unknown LLM provider: {provider_name}")

    return factory(config)


def list_providers() -> list[str]:
    """List all available LLM providers."""
    return ["openai", "anthropic", "gemini", "deepseek", "kimi", "minimax", "glm"]
