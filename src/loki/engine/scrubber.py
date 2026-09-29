import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


class NetworkScrubber:
    """
    Sanitizes captured network archives (HAR) by scrubbing sensitive credentials,
    bearer tokens, session cookies, and private personal information (PII).
    """

    SENSITIVE_HEADERS = {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "apikey",
        "api-key",
        "x-auth-token",
        "x-csrf-token",
        "x-xsrf-token",
        "token",
        "secret",
        "session",
    }

    SENSITIVE_PARAM_PATTERNS = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"token",
            r"api_?key",
            r"secret",
            r"auth",
            r"password",
            r"pwd",
            r"session",
            r"jwt",
            r"access_?token",
            r"refresh_?token",
            r"cvv",
            r"cvc",
            r"card",
        ]
    ]

    @classmethod
    def is_sensitive_key(cls, key: str) -> bool:
        """Determines if a key or parameter name refers to sensitive authentication or data."""
        key_clean = key.strip().lower()
        if key_clean in cls.SENSITIVE_HEADERS:
            return True
        return any(pattern.search(key_clean) for pattern in cls.SENSITIVE_PARAM_PATTERNS)

    @classmethod
    def scrub_url(cls, raw_url: str) -> str:
        """Removes sensitive credentials and query parameters from a URL."""
        try:
            parsed = urlparse(raw_url)
            if not parsed.query:
                return raw_url

            query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
            scrubbed_pairs = []
            for k, v in query_pairs:
                if cls.is_sensitive_key(k):
                    scrubbed_pairs.append((k, "[REDACTED]"))
                else:
                    scrubbed_pairs.append((k, v))

            new_query = urlencode(scrubbed_pairs, safe="[]")
            return urlunparse(parsed._replace(query=new_query))
        except Exception:
            return raw_url

    @classmethod
    def scrub_headers(cls, headers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitizes HTTP request and response headers."""
        scrubbed = []
        for h in headers:
            name = h.get("name", "")
            val = h.get("value", "")
            name_lower = name.lower()

            if name_lower == "authorization":
                # Keep scheme prefix if standard (Bearer, Basic), redact token
                parts = val.split(" ", 1)
                if len(parts) == 2:
                    val = f"{parts[0]} [REDACTED]"
                else:
                    val = "[REDACTED]"
            elif name_lower in ["cookie", "set-cookie"]:
                val = "[REDACTED]"
            elif cls.is_sensitive_key(name):
                val = "[REDACTED]"

            scrubbed.append({"name": name, "value": val})
        return scrubbed

    @classmethod
    def scrub_cookies(cls, cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitizes cookies list by redacting sensitive values."""
        scrubbed = []
        for c in cookies:
            cookie_copy = dict(c)
            # All cookie values are treated as sensitive regardless of name
            cookie_copy["value"] = "[REDACTED]"
            scrubbed.append(cookie_copy)
        return scrubbed

    @classmethod
    def scrub_post_data(cls, post_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Recursively scrubs sensitive parameters in request post data."""
        if not post_data:
            return post_data

        clean_post = dict(post_data)
        text_content = clean_post.get("text")

        # If post body is JSON
        if text_content and isinstance(text_content, str):
            try:
                data = json.loads(text_content)
                if isinstance(data, dict):
                    clean_dict = cls._scrub_dict(data)
                    clean_post["text"] = json.dumps(clean_dict)
            except Exception:
                pass

        # If post body params list exists
        params = clean_post.get("params")
        if params and isinstance(params, list):
            clean_params = []
            for p in params:
                p_copy = dict(p)
                p_name = p_copy.get("name", "")
                if cls.is_sensitive_key(p_name):
                    p_copy["value"] = "[REDACTED]"
                clean_params.append(p_copy)
            clean_post["params"] = clean_params

        return clean_post

    @classmethod
    def _scrub_dict(cls, data: dict) -> dict:
        """Recursively scrubs keys in a JSON object."""
        new_data = {}
        for k, v in data.items():
            if cls.is_sensitive_key(k):
                new_data[k] = "[REDACTED]"
            elif isinstance(v, dict):
                new_data[k] = cls._scrub_dict(v)
            elif isinstance(v, list):
                new_data[k] = [cls._scrub_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                new_data[k] = v
        return new_data

    @classmethod
    def scrub_har_data(cls, har_json: Dict[str, Any]) -> Dict[str, Any]:
        """Processes an entire HAR log structure and returns a fully sanitized copy."""
        log = har_json.get("log", {})
        entries = log.get("entries", [])

        for entry in entries:
            req = entry.get("request", {})
            res = entry.get("response", {})

            # 1. Scrub request URL
            if "url" in req:
                req["url"] = cls.scrub_url(req["url"])

            # 2. Scrub request headers
            if "headers" in req:
                req["headers"] = cls.scrub_headers(req["headers"])

            # 3. Scrub request cookies
            if "cookies" in req:
                req["cookies"] = cls.scrub_cookies(req["cookies"])

            # 4. Scrub request post body
            if "postData" in req:
                req["postData"] = cls.scrub_post_data(req["postData"])

            # 5. Scrub response headers
            if "headers" in res:
                res["headers"] = cls.scrub_headers(res["headers"])

            # 6. Scrub response cookies
            if "cookies" in res:
                res["cookies"] = cls.scrub_cookies(res["cookies"])

        return har_json

    @classmethod
    def scrub_har_file(cls, input_har_path: Path, output_har_path: Path) -> Optional[Path]:
        """Reads a raw HAR file, scrubs all sensitive data, and writes the sanitized output."""
        if not input_har_path.exists():
            return None

        try:
            with open(input_har_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            sanitized = cls.scrub_har_data(data)

            output_har_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_har_path, "w", encoding="utf-8") as f:
                json.dump(sanitized, f, indent=2)

            return output_har_path
        except Exception as e:
            # If scrubbing fails, avoid leaking raw HAR
            return None
