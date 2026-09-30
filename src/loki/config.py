import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

DEFAULT_MODEL = "gemini/gemini-flash-latest"
MODELS_REGISTRY_PATH = Path(".loki/models.json")


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


# --- Model registry (.loki/models.json) -------------------------------------
#
# A small, chat-editable list of named AI connection profiles (`loki chat`'s
# `/model` command reads and writes this file). Whichever profile is marked
# `active` here takes priority over .loki/config.yaml's `ai:` section for
# EVERY LOKI feature that talks to an LLM (chat, rules evaluation, fix,
# auto-heal) — not just chat — since they all resolve through this module.
# An explicit --model flag still wins over both.

def load_models_registry() -> Dict[str, Any]:
    """Reads the model profile registry, or an empty one if it doesn't exist yet."""
    if MODELS_REGISTRY_PATH.exists():
        try:
            with open(MODELS_REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("active", None)
                    data.setdefault("profiles", [])
                    return data
        except Exception:
            pass
    return {"active": None, "profiles": []}


def save_models_registry(registry: Dict[str, Any]) -> None:
    MODELS_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODELS_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def list_model_profiles() -> List[Dict[str, Any]]:
    return load_models_registry().get("profiles", [])


def get_model_profile(name: str) -> Optional[Dict[str, Any]]:
    name_lower = name.lower()
    for profile in list_model_profiles():
        if str(profile.get("name", "")).lower() == name_lower:
            return profile
    return None


def get_active_model_profile() -> Optional[Dict[str, Any]]:
    registry = load_models_registry()
    active_name = registry.get("active")
    if not active_name:
        return None
    return get_model_profile(active_name)


def add_model_profile(
    name: str, model: str, api_base: Optional[str] = None, api_key_env: Optional[str] = None
) -> Dict[str, Any]:
    """Adds (or updates) a named profile and returns it. Does not activate it."""
    registry = load_models_registry()
    profile: Dict[str, Any] = {"name": name, "model": model}
    if api_base:
        profile["api_base"] = api_base
    if api_key_env:
        profile["api_key_env"] = api_key_env
    name_lower = name.lower()
    registry["profiles"] = [
        p for p in registry.get("profiles", []) if str(p.get("name", "")).lower() != name_lower
    ] + [profile]
    save_models_registry(registry)
    return profile


def remove_model_profile(name: str) -> bool:
    """Removes a profile by name. Clears `active` too if it pointed at it. Returns whether it existed."""
    registry = load_models_registry()
    profiles = registry.get("profiles", [])
    name_lower = name.lower()
    remaining = [p for p in profiles if str(p.get("name", "")).lower() != name_lower]
    existed = len(remaining) != len(profiles)
    registry["profiles"] = remaining
    if str(registry.get("active") or "").lower() == name_lower:
        registry["active"] = None
    if existed:
        save_models_registry(registry)
    return existed


def activate_model_profile(name: str) -> Optional[Dict[str, Any]]:
    """Marks an existing profile as active. Returns it, or None if no such profile exists."""
    profile = get_model_profile(name)
    if not profile:
        return None
    registry = load_models_registry()
    registry["active"] = profile["name"]  # canonical stored casing, not whatever the caller typed
    save_models_registry(registry)
    return profile


def clear_active_model_profile() -> None:
    """Reverts to whatever .loki/config.yaml's `ai:` section (or the bundled default) says."""
    registry = load_models_registry()
    if registry.get("active"):
        registry["active"] = None
        save_models_registry(registry)


# --- Resolution: explicit arg > active registry profile > config.yaml > default

def resolve_model(explicit: Optional[str] = None) -> str:
    """Returns a LiteLLM model id: explicit value, else the active `/model` profile
    (.loki/models.json), else .loki/config.yaml's `ai:` section, else the default."""
    if explicit:
        return explicit
    active = get_active_model_profile()
    if active:
        return active["model"]
    ai = load_loki_config().get("ai") or {}
    model = ai.get("model")
    if not model:
        return DEFAULT_MODEL
    if "/" not in model and ai.get("provider"):
        return f"{ai['provider']}/{model}"
    return model


def model_source(explicit: Optional[str] = None) -> str:
    """Human-readable description of where the resolved model is coming from."""
    if explicit:
        return "--model flag"
    active = get_active_model_profile()
    if active:
        return f"/model profile '{active['name']}'"
    ai = load_loki_config().get("ai") or {}
    if ai.get("model"):
        return ".loki/config.yaml"
    return "bundled default"


def is_ai_customized(explicit_model: Optional[str] = None) -> bool:
    """True once the caller, the active `/model` profile, or .loki/config.yaml points
    at anything other than LOKI's bundled Gemini default. When true, LOKI must try
    exactly what was configured and never silently swap in a different provider's model."""
    if explicit_model or get_active_model_profile():
        return True
    ai = load_loki_config().get("ai") or {}
    return bool(ai.get("model") or ai.get("api_base") or ai.get("api_key_env"))


def resolve_ai_connection(explicit_model: Optional[str] = None) -> Dict[str, Any]:
    """Resolves everything needed to call ANY LiteLLM-compatible AI provider — not
    just Gemini/OpenAI/Anthropic — including a fully custom or self-hosted
    OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, an internal gateway,
    OpenRouter, Groq, Mistral, Azure, ...). Priority: explicit arg > the active
    `/model` profile (.loki/models.json, editable from `loki chat`) > .loki/config.yaml's
    `ai:` section:

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
    if explicit_model:
        # An explicit override (--model) gets a clean connection: just that model,
        # nothing else. .loki/config.yaml's api_base/api_key_env belong to ITS OWN
        # `model` entry — blindly inheriting them here would silently route an
        # unrelated explicit model (and its provider's key) through whatever
        # custom endpoint/key was configured for a different model entirely.
        return {"model": explicit_model}

    active = get_active_model_profile()
    if active:
        kwargs: Dict[str, Any] = {"model": active["model"]}
        if active.get("api_base"):
            kwargs["api_base"] = active["api_base"]
        if active.get("api_key_env"):
            api_key = os.environ.get(active["api_key_env"])
            if api_key:
                kwargs["api_key"] = api_key
        return kwargs

    ai = load_loki_config().get("ai") or {}
    kwargs = {"model": resolve_model(None)}

    api_base = ai.get("api_base")
    if api_base:
        kwargs["api_base"] = api_base

    api_key_env = ai.get("api_key_env")
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if api_key:
            kwargs["api_key"] = api_key

    return kwargs
