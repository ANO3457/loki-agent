import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

DEFAULT_MODEL = "gemini/gemini-flash-latest"


def load_loki_config() -> dict:
    """Reads project configuration from .loki/config.yaml if available."""
    config_file = Path(".loki/config.yaml")
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


def resolve_model(explicit: Optional[str] = None) -> str:
    """Returns a LiteLLM model id: CLI value, else .loki/config.yaml `ai`, else the default."""
    if explicit:
        return explicit
    ai = load_loki_config().get("ai") or {}
    model = ai.get("model")
    if not model:
        return DEFAULT_MODEL
    if "/" not in model and ai.get("provider"):
        return f"{ai['provider']}/{model}"
    return model


def is_ai_customized(explicit_model: Optional[str] = None) -> bool:
    """True once the caller or .loki/config.yaml points at anything other than
    LOKI's bundled Gemini default. When true, LOKI must try exactly what was
    configured and never silently swap in a different provider's model."""
    ai = load_loki_config().get("ai") or {}
    return bool(explicit_model or ai.get("model") or ai.get("api_base") or ai.get("api_key_env"))


def resolve_ai_connection(explicit_model: Optional[str] = None) -> Dict[str, Any]:
    """Resolves everything needed to call ANY LiteLLM-compatible AI provider — not
    just Gemini/OpenAI/Anthropic — including a fully custom or self-hosted
    OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, an internal gateway,
    OpenRouter, Groq, Mistral, Azure, ...), from .loki/config.yaml's `ai:` section:

        ai:
          provider: mistral             # optional: prefixes `model` if it has no "/"
          model: mistral-large-latest   # any LiteLLM model id: "provider/model", or a
                                         # bare name when using a custom api_base
          api_base: https://host/v1     # optional: point at any self-hosted or
                                         # OpenAI-compatible server
          api_key_env: MY_PROVIDER_KEY  # optional: env var holding the key, when it
                                         # doesn't match the provider's default name

    Returns kwargs ready to splat into litellm.completion(**kwargs, messages=...).
    """
    ai = load_loki_config().get("ai") or {}
    kwargs: Dict[str, Any] = {"model": resolve_model(explicit_model)}

    api_base = ai.get("api_base")
    if api_base:
        kwargs["api_base"] = api_base

    api_key_env = ai.get("api_key_env")
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if api_key:
            kwargs["api_key"] = api_key

    return kwargs
