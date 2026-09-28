import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from playwright.sync_api import sync_playwright, Page, Response, Error
from src.loki.personas.base import BasePersona


@dataclass
class IncidentReport:
    """Stores all anomalies and crash data captured during an execution."""
    target_url: str
    persona_name: Optional[str] = None
    crashes: List[str] = field(default_factory=list)
    console_errors: List[str] = field(default_factory=list)
    http_errors: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    video_path: Optional[str] = None
    dom_snapshot: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def has_crashes(self) -> bool:
        """Returns True if any unhandled error or server 500 error occurred."""
        return len(self.crashes) > 0 or len(self.http_errors) > 0


class ChaosSandbox:
    """Manages an isolated browser session with live error sniffing and video capture."""

    def __init__(self, output_dir: str = ".loki/runs", headless: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless

    def run_session(
        self,
        target_url: str,
        duration: int = 5,
        persona: Optional[BasePersona] = None,
        journey_data: Optional[dict] = None,
    ) -> IncidentReport:
        """Launches the target URL, applies chaotic attacks, and records evidence."""
        report = IncidentReport(
            target_url=target_url,
            persona_name=persona.name if persona else None,
        )
        start_time = time.time()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                record_video_dir=str(self.output_dir / "videos"),
                record_video_size={"width": 1280, "height": 720},
            )
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

                # Guided journey execution
                if journey_data and journey_data.get("steps"):
                    report.actions_taken.append(f"Started guided journey: '{journey_data.get('name')}'")
                    for step in journey_data["steps"]:
                        if persona:
                            persona.attack_step(page=page, step=step)
                        else:
                            selector = step.get("selector")
                            if step.get("action") == "click" and selector:
                                page.click(selector, timeout=2000)
                            elif step.get("action") == "input" and selector:
                                page.fill(selector, step.get("value", ""))
                        time.sleep(0.2)

                    if persona:
                        report.actions_taken.extend(persona.actions_log)
                elif persona:
                    persona.attack(page=page, duration=duration)
                    report.actions_taken = persona.actions_log
                else:
                    time.sleep(duration)

            except Error as e:
                report.crashes.append(f"Navigation error: {str(e)}")
            finally:
                # Capture concise UI state snapshot for AI business rules evaluation
                try:
                    if not page.is_closed():
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

        report.duration_seconds = round(time.time() - start_time, 2)
        return report