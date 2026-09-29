from pathlib import Path
from typing import Optional
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
