"""Configuration management for KB-CLI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


def _find_project_root() -> Optional[Path]:
    """Find project root by looking for .env or pyproject.toml."""
    # Start from current working directory
    current = Path.cwd()
    for _ in range(10):  # Max 10 levels up
        if (current / ".env").exists() or (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _load_dotenv_files():
    """Load .env files from project directory and home config."""
    # Try to find project root
    project_root = _find_project_root()
    if project_root:
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    # Also try current working directory
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        load_dotenv(cwd_env, override=False)

    # Load from home config directory (lowest priority)
    home_env = Path.home() / ".kb" / ".env"
    if home_env.exists():
        load_dotenv(home_env, override=False)


# Load .env on module import
_load_dotenv_files()


class TelegramConfig(BaseModel):
    """Telegram configuration."""
    bot_token: str = ""
    channel_id: str = ""  # @channel_name or -100xxxxxxxxxx


class LLMProviderConfig(BaseModel):
    """Single LLM provider configuration."""
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = ""
    enabled: bool = True


class LLMConfig(BaseModel):
    """LLM configuration supporting multiple providers."""
    default_provider: str = "openai"

    # Provider configs
    openai: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        model="gpt-4o-mini"
    ))
    anthropic: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        model="claude-3-5-sonnet-20241022"
    ))
    gemini: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        model="gemini-1.5-flash"
    ))
    deepseek: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat"
    ))
    kimi: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        base_url="https://api.moonshot.cn/v1",
        model="moonshot-v1-8k"
    ))
    minimax: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        base_url="https://api.minimax.chat/v1",
        model="abab6.5s-chat"
    ))
    glm: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",
        model="glm-4-flash"
    ))


class TagConfig(BaseModel):
    """Tag configuration."""
    presets: list[str] = Field(default_factory=lambda: [
        "AI", "Tools", "Article", "Tutorial",
        "Research", "Programming", "Product", "Design"
    ])
    allow_new: bool = True


class Config(BaseModel):
    """Main configuration."""
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tags: TagConfig = Field(default_factory=TagConfig)


def get_config_dir() -> Path:
    """Get the configuration directory."""
    config_dir = Path.home() / ".kb"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.yaml"


def load_config() -> Config:
    """Load configuration from file."""
    config_path = get_config_path()

    if not config_path.exists():
        # Create default config
        config = Config()
        save_config(config)
        return config

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Override with environment variables
    _override_from_env(data)

    return Config(**data)


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(
            config.model_dump(),
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )


def _override_from_env(data: dict) -> None:
    """Override config values from environment variables."""
    env_mappings = {
        "KB_TELEGRAM_BOT_TOKEN": ("telegram", "bot_token"),
        "KB_TELEGRAM_CHANNEL_ID": ("telegram", "channel_id"),
        "KB_LLM_PROVIDER": ("llm", "default_provider"),
        "OPENAI_API_KEY": ("llm", "openai", "api_key"),
        "ANTHROPIC_API_KEY": ("llm", "anthropic", "api_key"),
        "GEMINI_API_KEY": ("llm", "gemini", "api_key"),
        "DEEPSEEK_API_KEY": ("llm", "deepseek", "api_key"),
        "KIMI_API_KEY": ("llm", "kimi", "api_key"),
        "MINIMAX_API_KEY": ("llm", "minimax", "api_key"),
        "GLM_API_KEY": ("llm", "glm", "api_key"),
    }

    for env_var, path in env_mappings.items():
        value = os.environ.get(env_var)
        if value:
            _set_nested(data, path, value)

    # Handle preset tags (comma-separated list)
    preset_tags = os.environ.get("KB_PRESET_TAGS")
    if preset_tags:
        tags = [t.strip() for t in preset_tags.split(",") if t.strip()]
        if tags:
            data.setdefault("tags", {})["presets"] = tags


def _set_nested(data: dict, path: tuple, value: str) -> None:
    """Set a nested dictionary value."""
    for key in path[:-1]:
        data = data.setdefault(key, {})
    data[path[-1]] = value


def add_preset_tag(tag: str) -> None:
    """Add a new preset tag."""
    config = load_config()
    if tag not in config.tags.presets:
        config.tags.presets.append(tag)
        save_config(config)


def get_provider_config(config: Config, provider: Optional[str] = None) -> tuple[str, LLMProviderConfig]:
    """Get the provider name and config for a given provider or default."""
    provider = provider or config.llm.default_provider
    provider_config = getattr(config.llm, provider, None)

    if provider_config is None:
        raise ValueError(f"Unknown LLM provider: {provider}")

    return provider, provider_config
