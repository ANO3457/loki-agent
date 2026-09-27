import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from playwright.sync_api import sync_playwright, Page, Response, Error


@dataclass
class IncidentReport:
    """Stores all anomalies and crash data captured during an execution."""
    target_url: str
    crashes: List[str] = field(default_factory=list)
    console_errors: List[str] = field(default_factory=list)
    http_errors: List[str] = field(default_factory=list)
    video_path: Optional[str] = None
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

    def run_session(self, target_url: str, duration: int = 5) -> IncidentReport:
        """Launches the target URL, monitors for crashes, and records the session."""
        report = IncidentReport(target_url=target_url)
        start_time = time.time()

        with sync_playwright() as p:
            # Launch isolated Chromium instance
            browser = p.chromium.launch(headless=self.headless)

            # Create an ephemeral browser context with video recording enabled
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
                # Navigate to the target application
                page.goto(target_url, wait_until="networkidle", timeout=15000)
                # Keep session active for the given duration
                time.sleep(duration)
            except Error as e:
                report.crashes.append(f"Navigation error: {str(e)}")
            finally:
                # Close page and context to flush video recording to disk
                page.close()
                video_obj = page.video
                context.close()
                browser.close()

                if video_obj:
                    report.video_path = video_obj.path()

        report.duration_seconds = round(time.time() - start_time, 2)
        return report