"""Authorization guardrail: LOKI refuses to attack a non-local target until the
user has explicitly confirmed (once, remembered) that they own it or have
explicit permission to test it. Localhost is always allowed with no friction —
everything else requires a one-time confirmation per host, persisted in
`.loki/authorized_targets.json`, or the `--authorized` flag for scripted/CI use.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

AUTHORIZED_TARGETS_PATH = Path(".loki/authorized_targets.json")
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def extract_host(url: str) -> str:
    """Extracts the bare hostname from a target URL (or a bare hostname as-is)."""
    candidate = url if "://" in url else f"http://{url}"
    parsed = urlparse(candidate)
    return (parsed.hostname or url).strip().lower()


def is_local_host(url: str) -> bool:
    """True for localhost/loopback — always allowed, no authorization needed."""
    return extract_host(url) in LOCAL_HOSTNAMES


def _load_authorized() -> Dict[str, Any]:
    if AUTHORIZED_TARGETS_PATH.exists():
        try:
            data = json.loads(AUTHORIZED_TARGETS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("hosts", {})
                return data
        except Exception:
            pass
    return {"hosts": {}}


def _save_authorized(data: Dict[str, Any]) -> None:
    AUTHORIZED_TARGETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTHORIZED_TARGETS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_host_authorized(url: str) -> bool:
    return extract_host(url) in _load_authorized()["hosts"]


def authorize_host(url: str, note: str = "") -> str:
    """Records a host as authorized (trust-on-first-use). Returns the bare hostname."""
    host = extract_host(url)
    data = _load_authorized()
    data["hosts"][host] = {
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    _save_authorized(data)
    return host


def revoke_host(host: str) -> bool:
    """Removes a host's authorization record. Returns whether it existed."""
    data = _load_authorized()
    key = host.strip().lower()
    existed = key in data["hosts"]
    if existed:
        del data["hosts"][key]
        _save_authorized(data)
    return existed


def list_authorized_hosts() -> Dict[str, Any]:
    return _load_authorized()["hosts"]
