"""Configuration management."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_CONFIG = {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "base_url": "https://api.openai.com/v1",
    "max_tokens": 2048,
    "temperature": 0.2,
    "language": "en",
    "severity_threshold": "low",
}

CONFIG_PATH = Path.home() / ".codereview" / "config.json"

PROVIDER_DEFAULTS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo",
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-haiku-20240307",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3",
        "env_key": None,
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
}


def _get_api_key(config: Dict[str, Any]) -> Optional[str]:
    """Resolve API key from environment only — never store in config file."""
    env_override = os.environ.get("CODEREVIEW_API_KEY")
    if env_override:
        return env_override

    provider = config.get("provider", "openai")
    if provider in PROVIDER_DEFAULTS:
        env_key = PROVIDER_DEFAULTS[provider].get("env_key")
        if env_key:
            return os.environ.get(env_key)

    return None


def load_config() -> Dict[str, Any]:
    """Load config from file and env vars. API keys come from env only."""
    config = DEFAULT_CONFIG.copy()

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                file_config = json.load(f)
            file_config.pop("api_key", None)
            config.update(file_config)
        except (json.JSONDecodeError, IOError):
            pass

    provider = config.get("provider", "openai")
    if provider in PROVIDER_DEFAULTS:
        defaults = PROVIDER_DEFAULTS[provider]
        if not config.get("base_url") or config["base_url"] == DEFAULT_CONFIG["base_url"]:
            config["base_url"] = defaults["base_url"]
        if not config.get("model") or config["model"] == DEFAULT_CONFIG["model"]:
            config["model"] = defaults["model"]

    config["api_key"] = _get_api_key(config)

    env_model = os.environ.get("CODEREVIEW_MODEL")
    if env_model:
        config["model"] = env_model

    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save config to file. Never persists API keys."""
    safe_config = {k: v for k, v in config.items() if k != "api_key"}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_PATH.parent, 0o700)
    with open(CONFIG_PATH, "w") as f:
        json.dump(safe_config, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


def init_config(provider: str = "openai") -> Dict[str, Any]:
    """Initialize config for a provider."""
    config = DEFAULT_CONFIG.copy()
    config["provider"] = provider
    if provider in PROVIDER_DEFAULTS:
        defaults = PROVIDER_DEFAULTS[provider]
        config["base_url"] = defaults["base_url"]
        config["model"] = defaults["model"]
    save_config(config)
    config["api_key"] = _get_api_key(config)
    return config
