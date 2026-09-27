import time
from playwright.sync_api import Page, TimeoutError
from src.loki.personas.base import BasePersona


class RageClickerPersona(BasePersona):
    """Simulates an impatient, aggressive user executing rapid burst clicks."""

    def __init__(self, click_burst_count: int = 5, click_delay: float = 0.05):
        super().__init__(
            name="RageClicker",
            description="Fires rapid consecutive clicks on action elements to trigger race conditions.",
        )
        self.click_burst_count = click_burst_count
        self.click_delay = click_delay

    def attack(self, page: Page, duration: int):
        """Finds interactive buttons and inputs, spamming rapid clicks."""
        start_time = time.time()
        self.log_action("Started RageClicker attack session")

        while time.time() - start_time < duration:
            clickable_selectors = [
                "button:visible",
                "input[type='submit']:visible",
                "a[role='button']:visible",
            ]

            elements = []
            for selector in clickable_selectors:
                try:
                    elements.extend(page.query_selector_all(selector))
                except Exception:
                    pass

            if not elements:
                time.sleep(0.5)
                continue

            for element in elements:
                if time.time() - start_time >= duration:
                    break

                try:
                    element_text = element.inner_text().strip() or "unnamed button"
                    self.log_action(f"Targeting element: '{element_text}' with {self.click_burst_count} rapid clicks")

                    for _ in range(self.click_burst_count):
                        element.click(timeout=1000, no_wait_after=True)
                        time.sleep(self.click_delay)

                except TimeoutError:
                    self.log_action("Element click timed out (possible UI lockup)")
                except Exception as e:
                    self.log_action(f"Failed clicking element: {str(e)}")

                time.sleep(0.3)

        self.log_action("Finished RageClicker attack session")