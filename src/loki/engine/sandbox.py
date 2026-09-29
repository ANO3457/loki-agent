import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright, Page, Response, Error
from src.loki.personas.base import BasePersona


@dataclass
class IncidentReport:
    """Stores all anomalies and crash data captured during an execution."""
    target_url: str
    persona_name: Optional[str] = None
    device_name: Optional[str] = None
    orientation: str = "portrait"
    crashes: List[str] = field(default_factory=list)
    console_errors: List[str] = field(default_factory=list)
    http_errors: List[str] = field(default_factory=list)
    layout_issues: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    replay_trace: List[Dict[str, Any]] = field(default_factory=list)
    video_path: Optional[str] = None
    har_path: Optional[str] = None
    dom_snapshot: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def has_crashes(self) -> bool:
        """Returns True if any unhandled error or server 500 error occurred."""
        return len(self.crashes) > 0 or len(self.http_errors) > 0

    @property
    def has_layout_issues(self) -> bool:
        """Returns True if any mobile responsive layout violation occurred."""
        return len(self.layout_issues) > 0


def resolve_device(
    device_name: Optional[str],
    orientation: str = "portrait",
    devices: Optional[dict] = None,
) -> tuple[Optional[str], Optional[dict]]:
    """Resolves friendly device aliases (e.g. 'iphone-15', 'pixel-7') to Playwright device descriptors."""
    if not device_name or not devices:
        return None, None

    clean_name = device_name.strip()
    is_landscape = orientation.lower() == "landscape"

    alias_map = {
        "iphone": "iPhone 15",
        "iphone-15": "iPhone 15",
        "iphone15": "iPhone 15",
        "iphone-15-pro": "iPhone 15 Pro",
        "iphone-14": "iPhone 14",
        "iphone14": "iPhone 14",
        "iphone-13": "iPhone 13",
        "iphone13": "iPhone 13",
        "iphone-se": "iPhone SE",
        "pixel": "Pixel 7",
        "pixel-7": "Pixel 7",
        "pixel7": "Pixel 7",
        "pixel-8": "Pixel 8",
        "pixel-9": "Pixel 9",
        "ipad": "iPad Pro 11",
        "ipad-pro": "iPad Pro 11",
        "ipad-mini": "iPad Mini",
        "galaxy": "Galaxy S9+",
    }

    target = alias_map.get(clean_name.lower(), clean_name)

    # Check for landscape variant directly in devices catalog
    if is_landscape:
        landscape_candidate = f"{target} landscape"
        if landscape_candidate in devices:
            return landscape_candidate, dict(devices[landscape_candidate])

    # Direct match in devices catalog
    if target in devices:
        desc = dict(devices[target])
        if is_landscape and "viewport" in desc:
            vp = desc["viewport"]
            desc["viewport"] = {
                "width": max(vp["width"], vp["height"]),
                "height": min(vp["width"], vp["height"]),
            }
        return target, desc

    # Case-insensitive substring lookup
    for key, val in devices.items():
        if target.lower() in key.lower():
            if is_landscape and "landscape" in key.lower():
                return key, dict(val)
            elif not is_landscape and "landscape" not in key.lower():
                return key, dict(val)

    return None, None


class ChaosSandbox:
    """Manages an isolated browser session with live error sniffing and video capture."""

    def __init__(self, output_dir: str = ".loki/runs", headless: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless

    def _sniff_mobile_layout(self, page: Page) -> List[str]:
        """Sniffs for mobile responsiveness issues such as horizontal scroll overflows and missing viewport meta tags."""
        try:
            if page.is_closed():
                return []
            vp = page.viewport_size
            vp_width = vp["width"] if vp else 390
            return page.evaluate("""(vpWidth) => {
                const issues = [];
                const docWidth = Math.max(
                    document.documentElement.scrollWidth || 0,
                    document.body ? document.body.scrollWidth : 0
                );
                
                // Detect horizontal overflow (standard mobile UX bug)
                if (docWidth > vpWidth + 5) {
                    issues.push(`Horizontal scroll overflow detected: page content (${docWidth}px) exceeds mobile viewport width (${vpWidth}px) by ${docWidth - vpWidth}px.`);
                }

                // Detect missing or invalid viewport meta tag
                const metaViewport = document.querySelector('meta[name="viewport"]');
                if (!metaViewport) {
                    issues.push("Missing <meta name='viewport'> tag: mobile devices will render unoptimized scaled desktop view.");
                } else {
                    const content = metaViewport.getAttribute('content') || '';
                    if (!content.includes('width=device-width')) {
                        issues.push("<meta name='viewport'> tag missing 'width=device-width' directive.");
                    }
                }

                return issues;
            }""", vp_width)
        except Exception:
            return []

    def run_session(
        self,
        target_url: str,
        duration: int = 5,
        persona: Optional[BasePersona] = None,
        journey_data: Optional[dict] = None,
        device_name: Optional[str] = None,
        orientation: str = "portrait",
    ) -> IncidentReport:
        """Launches the target URL, applies chaotic attacks, and records evidence."""
        report = IncidentReport(
            target_url=target_url,
            persona_name=persona.name if persona else None,
            orientation=orientation,
        )
        start_time = time.time()
        temp_har_file = self.output_dir / f"temp_network_{int(start_time)}.har"

        with sync_playwright() as p:
            resolved_device_name, device_config = resolve_device(
                device_name=device_name,
                orientation=orientation,
                devices=p.devices,
            )
            report.device_name = resolved_device_name or device_name

            try:
                browser = p.chromium.launch(headless=self.headless)
            except Error as e:
                err_msg = str(e).lower()
                if "executable doesn't exist" in err_msg or "playwright install" in err_msg:
                    import subprocess
                    import sys
                    from rich.console import Console
                    Console().print("[bold yellow]⚡ Chromium browser not found. Installing automatically via Playwright...[/bold yellow]")
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                    browser = p.chromium.launch(headless=self.headless)
                else:
                    raise e

            context_kwargs = {
                "record_video_dir": str(self.output_dir / "videos"),
                "record_har_path": str(temp_har_file),
            }
            if device_config:
                context_kwargs.update(device_config)
                if "viewport" in device_config:
                    context_kwargs["record_video_size"] = device_config["viewport"]
            else:
                context_kwargs["record_video_size"] = {"width": 1280, "height": 720}

            context = browser.new_context(**context_kwargs)
            page: Page = context.new_page()

            # 1. Listen for unhandled JavaScript exceptions
            page.on("pageerror", lambda err: report.crashes.append(str(err)))

            # 2. Listen for console error messages
            page.on(
                "console",
                lambda msg: report.console_errors.append(msg.text)
                if msg.type == "error"
                else None,
            )

            # 3. Listen for HTTP response errors (status >= 500)
            def handle_response(response: Response):
                if response.status >= 500:
                    report.http_errors.append(
                        f"HTTP {response.status} on {response.url}"
                    )

            page.on("response", handle_response)

            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=15000)

                # Sniff initial mobile responsiveness if running under device emulation
                if report.device_name:
                    report.layout_issues.extend(self._sniff_mobile_layout(page))

                # Guided journey execution
                session_trace: List[Dict[str, Any]] = []
                if journey_data and journey_data.get("steps"):
                    report.actions_taken.append(f"Started guided journey: '{journey_data.get('name')}'")
                    for step in journey_data["steps"]:
                        if persona:
                            persona.attack_step(page=page, step=step)
                            session_trace.extend(persona.trace)
                            persona.trace.clear()
                        else:
                            selector = step.get("selector")
                            if step.get("action") == "click" and selector:
                                page.click(selector, timeout=2000)
                                session_trace.append({"kind": "click", "selector": selector})
                            elif step.get("action") == "input" and selector:
                                value = step.get("value", "")
                                page.fill(selector, value)
                                session_trace.append({"kind": "fill", "selector": selector, "value": value})
                        time.sleep(0.2)

                    if persona:
                        report.actions_taken.extend(persona.actions_log)
                elif persona:
                    persona.attack(page=page, duration=duration)
                    report.actions_taken = persona.actions_log
                    session_trace.extend(persona.trace)
                else:
                    time.sleep(duration)
                report.replay_trace = session_trace

            except Error as e:
                report.crashes.append(f"Navigation error: {str(e)}")
            finally:
                # Capture mobile layout state and concise UI state snapshot
                try:
                    if not page.is_closed():
                        if report.device_name:
                            for issue in self._sniff_mobile_layout(page):
                                if issue not in report.layout_issues:
                                    report.layout_issues.append(issue)
                        dom_info = page.evaluate("""() => {
                            const elements = [];
                            document.querySelectorAll('button, input, select, a, .status, .alert, .badge, [role="alert"]').forEach(el => {
                                elements.push({
                                    tag: el.tagName.toLowerCase(),
                                    id: el.id || undefined,
                                    classes: el.className || undefined,
                                    text: (el.innerText || el.value || '').trim(),
                                    disabled: el.disabled !== undefined ? el.disabled : undefined,
                                    visible: el.offsetParent !== null
                                });
                            });
                            return {
                                title: document.title,
                                url: window.location.href,
                                interactive_elements: elements
                            };
                        }""")
                        import json
                        report.dom_snapshot = json.dumps(dom_info, indent=2)
                except Exception:
                    pass

                page.close()
                video_obj = page.video
                context.close()
                browser.close()

                if video_obj:
                    report.video_path = video_obj.path()
                if temp_har_file.exists():
                    report.har_path = str(temp_har_file)

        report.duration_seconds = round(time.time() - start_time, 2)
        return report