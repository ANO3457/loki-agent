import time
import random
from typing import Optional
from playwright.sync_api import Page
from src.loki.personas.base import BasePersona


class NetworkTormentorPersona(BasePersona):
    """
    Simulates hostile network environments: extreme latency (slow 3G),
    sudden offline connection drops mid-transaction, and aborted API requests.
    """

    def __init__(self):
        super().__init__(
            name="NetworkTormentor",
            description="Injects high network latency, sudden connection loss, and aborted HTTP requests to expose UI hangs.",
        )

    def _apply_slow_network(self, page: Page, latency_ms: int = 1500):
        """Emulates slow network conditions using Chrome DevTools Protocol if available."""
        try:
            cdp = page.context.new_cdp_session(page)
            cdp.send(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": latency_ms,
                    "downloadThroughput": 50 * 1024,  # 50 kb/s (Slow 3G)
                    "uploadThroughput": 20 * 1024,    # 20 kb/s
                },
            )
            self.log_action(f"Throttled network to Slow 3G (latency: {latency_ms}ms, 50kbps down)")
        except Exception as e:
            # Fallback if CDP is not supported
            self.log_action(f"CDP throttling unavailable ({e}), using route delays")

    def _reset_network(self, page: Page):
        """Restores normal network conditions."""
        try:
            page.context.set_offline(False)
            cdp = page.context.new_cdp_session(page)
            cdp.send(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": 0,
                    "downloadThroughput": -1,
                    "uploadThroughput": -1,
                },
            )
            self.log_action("Restored network conditions to normal")
        except Exception:
            try:
                page.context.set_offline(False)
            except Exception:
                pass

    def attack(self, page: Page, duration: int):
        """Executes progressive network chaos assault against the target application."""
        self.log_action(f"Started NetworkTormentor assault session (duration: {duration}s)")
        start_time = time.time()

        # Step 1: Throttle network to Slow 3G
        self._apply_slow_network(page, latency_ms=1200)

        step = 0
        while time.time() - start_time < duration:
            step += 1
            try:
                # Find interactive buttons or inputs
                buttons = page.query_selector_all("button:visible, input[type='submit']:visible, a:visible")
                valid_buttons = [b for b in buttons if b.is_enabled()]

                if valid_buttons:
                    target_btn = random.choice(valid_buttons)
                    btn_text = (target_btn.text_content() or "Action Button").strip()[:30]

                    # Variant A: Trigger click then immediately cut the connection (offline drop mid-flight)
                    if step % 2 == 1:
                        self.log_action(f"Triggering action on '{btn_text}' under high latency")
                        target_btn.click(timeout=1000, no_wait_after=True, force=True)

                        # Sudden connection loss during request in-flight
                        page.wait_for_timeout(200)
                        self.log_action("💥 Pulling the plug: Simulated sudden offline connection drop")
                        page.context.set_offline(True)

                        # Allow UI 1.5s to react to offline state
                        page.wait_for_timeout(1500)

                        # Restore connectivity
                        self.log_action("Reconnecting network (offline -> online recovery)")
                        page.context.set_offline(False)
                        page.wait_for_timeout(500)

                    # Variant B: Rapid repeated clicks while connection is recovering
                    else:
                        self.log_action(f"Stressing '{btn_text}' during network recovery")
                        for _ in range(3):
                            target_btn.click(timeout=800, no_wait_after=True, force=True)
                            page.wait_for_timeout(150)

                else:
                    # If no buttons, simulate offline toggle on page
                    self.log_action("Toggling offline mode during idle page state")
                    page.context.set_offline(True)
                    page.wait_for_timeout(1000)
                    page.context.set_offline(False)

                page.wait_for_timeout(500)

            except Exception as e:
                self.log_action(f"Network assault cycle encountered: {str(e)[:40]}")
                page.wait_for_timeout(500)

        # Cleanup: Ensure page is left in normal online state
        self._reset_network(page)
        self.log_action("Finished NetworkTormentor assault session")

    def attack_step(self, page: Page, step: dict):
        """Mutates a recorded journey step by dropping the network during execution."""
        event_type = step.get("action") or step.get("type")
        selector = step.get("selector")
        target_name = step.get("value") or step.get("text") or step.get("id") or selector

        if event_type == "click":
            self.log_action(f"NetworkTormentor: Intercepting step '{target_name}' with mid-click offline drop")
            try:
                el = page.query_selector(selector)
                if el:
                    el.click(timeout=1000, no_wait_after=True, force=True)
                    page.wait_for_timeout(150)
                    page.context.set_offline(True)
                    self.log_action("💥 Dropped connection immediately after journey click")
                    page.wait_for_timeout(1200)
                    page.context.set_offline(False)
                    self.log_action("Restored connection following journey click")
            except Exception as e:
                self.log_action(f"Error during journey step attack: {e}")
                try:
                    page.context.set_offline(False)
                except Exception:
                    pass
