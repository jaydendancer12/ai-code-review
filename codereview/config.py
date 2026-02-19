"""Configuration management with secure API key handling."""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "base_url": "https://api.openai.com/v1",
    "max_tokens": 2048,
    "temperature": 0.2,
    "language": "en",
    "severity_threshold": "low",
}

CONFIG_PATH: Path = Path.home() / ".codereview" / "config.json"

PROVIDER_DEFAULTS: Dict[str, Dict[str, Any]] = {
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


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def _get_api_key(config: Dict[str, Any]) -> Optional[str]:
    """Resolve API key from environment only — never from config file.

    Priority:
        1. CODEREVIEW_API_KEY env var (universal override)
        2. Provider-specific env var (e.g. GROQ_API_KEY)

    Returns:
        API key string or None if not found.
    """
    env_override: Optional[str] = os.environ.get("CODEREVIEW_API_KEY")
    if env_override and env_override.strip():
        return env_override.strip()

    provider: str = config.get("provider", "openai")
    if provider in PROVIDER_DEFAULTS:
        env_key: Optional[str] = PROVIDER_DEFAULTS[provider].get("env_key")
        if env_key:
            value: Optional[str] = os.environ.get(env_key)
            if value and value.strip():
                return value.strip()

    return None


def validate_api_key(api_key: Optional[str], provider: str) -> bool:
    """Validate that an API key exists and has expected format.

    Args:
        api_key: The key to validate.
        provider: The provider name for format checking.

    Returns:
        True if the key appears valid.

    Raises:
        ConfigError: If the key is missing or clearly malformed.
    """
    if provider == "ollama":
        return True

    if not api_key:
        env_key: str = PROVIDER_DEFAULTS.get(provider, {}).get("env_key", "API_KEY")
        raise ConfigError(
            f"No API key found. Set the {env_key} environment variable.\n"
            f"  export {env_key}=your-key-here\n"
            f"  Or: export CODEREVIEW_API_KEY=your-key-here"
        )

    if len(api_key) < 10:
        raise ConfigError(
            f"API key looks too short ({len(api_key)} chars). "
            f"Check your environment variable."
        )

    return True


def _load_config_file() -> Dict[str, Any]:
    """Load config from disk safely.

    Returns:
        Parsed config dict, or empty dict on failure.
    """
    if not CONFIG_PATH.exists():
        return {}

    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            file_config: Dict[str, Any] = json.load(f)
        file_config.pop("api_key", None)
        return file_config
    except json.JSONDecodeError as e:
        logger.warning(f"Corrupt config file, ignoring: {e}")
        return {}
    except IOError as e:
        logger.warning(f"Cannot read config file: {e}")
        return {}


def _apply_provider_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply provider-specific defaults to config.

    Args:
        config: Current config dict.

    Returns:
        Config with provider defaults applied.
    """
    provider: str = config.get("provider", "openai")
    if provider not in PROVIDER_DEFAULTS:
        return config

    defaults: Dict[str, Any] = PROVIDER_DEFAULTS[provider]

    if not config.get("base_url") or config["base_url"] == DEFAULT_CONFIG["base_url"]:
        config["base_url"] = defaults["base_url"]
    if not config.get("model") or config["model"] == DEFAULT_CONFIG["model"]:
        config["model"] = defaults["model"]

    return config


def load_config() -> Dict[str, Any]:
    """Load config from file, env vars, and defaults.

    API keys are NEVER read from config file — only from environment.

    Returns:
        Complete config dict ready to use.
    """
    config: Dict[str, Any] = DEFAULT_CONFIG.copy()

    file_config: Dict[str, Any] = _load_config_file()
    config.update(file_config)

    config = _apply_provider_defaults(config)
    config["api_key"] = _get_api_key(config)

    env_model: Optional[str] = os.environ.get("CODEREVIEW_MODEL")
    if env_model:
        config["model"] = env_model

    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save config to file. Never persists API keys.

    Args:
        config: Config dict to save.

    Sets file permissions to owner-only (600).
    """
    safe_config: Dict[str, Any] = {
        k: v for k, v in config.items() if k != "api_key"
    }

    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(CONFIG_PATH.parent, 0o700)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(safe_config, f, indent=2)
        os.chmod(CONFIG_PATH, 0o600)
        logger.info(f"Config saved to {CONFIG_PATH}")
    except IOError as e:
        logger.error(f"Failed to save config: {e}")
        raise ConfigError(f"Cannot write config file: {e}")


def init_config(provider: str = "openai") -> Dict[str, Any]:
    """Initialize config for a provider.

    Args:
        provider: One of 'openai', 'anthropic', 'ollama', 'groq'.

    Returns:
        Initialized config dict.
    """
    if provider not in PROVIDER_DEFAULTS:
        raise ConfigError(
            f"Unknown provider: {provider}. "
            f"Choose from: {', '.join(PROVIDER_DEFAULTS.keys())}"
        )

    config: Dict[str, Any] = DEFAULT_CONFIG.copy()
    config["provider"] = provider
    config["base_url"] = PROVIDER_DEFAULTS[provider]["base_url"]
    config["model"] = PROVIDER_DEFAULTS[provider]["model"]

    save_config(config)
    config["api_key"] = _get_api_key(config)

    return config
