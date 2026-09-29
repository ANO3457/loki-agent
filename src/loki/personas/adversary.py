import time
import random
from typing import List
from playwright.sync_api import Page
from src.loki.personas.base import BasePersona


class AdversaryPersona(BasePersona):
    """
    Simulates a malicious or hostile actor actively probing frontend security:
    forcibly re-enabling disabled UI elements, tampering with hidden/readonly fields,
    and injecting adversarial security vectors (XSS, SQL delimiters, parameter tampering).
    """

    ADVERSARIAL_PAYLOADS = [
        "<script>alert('LOKI_XSS')</script>",
        "<img src=x onerror=console.error('LOKI_INJECTION')>",
        "' OR '1'='1' --",
        "'; DROP TABLE users; --",
        "__proto__[admin]=true",
        "../../../../etc/passwd",
        r"..\..\..\windows\win.ini",
        "{\"isAdmin\": true, \"discount\": 100}",
        "-10000.00",
        "javascript:void(fetch('/api/exfil?c='+document.cookie))",
    ]

    def __init__(self):
        super().__init__(
            name="Adversary",
            description="Bypasses client-side disabled guards, tampers with hidden fields, and injects adversarial security payloads.",
        )

    def _force_enable_disabled_controls(self, page: Page) -> List[str]:
        """Strips disabled and aria-disabled attributes from DOM elements via JavaScript."""
        script = """
        () => {
            const elements = document.querySelectorAll('button:disabled, input:disabled, [aria-disabled="true"], [disabled]');
            const unlocked = [];
            elements.forEach(el => {
                el.removeAttribute('disabled');
                el.removeAttribute('aria-disabled');
                el.style.pointerEvents = 'auto';
                el.style.opacity = '1';
                unlocked.push((el.id || el.getAttribute('name') || el.innerText || el.tagName).trim().substring(0, 30));
            });
            return unlocked;
        }
        """
        try:
            return page.evaluate(script)
        except Exception:
            return []

    def _tamper_hidden_and_readonly(self, page: Page) -> List[str]:
        """Detects and tampers with hidden or readonly inputs."""
        script = """
        () => {
            const targets = document.querySelectorAll('input[type="hidden"], [readonly]');
            const tampered = [];
            targets.forEach(el => {
                el.removeAttribute('readonly');
                el.value = 'ADVERSARY_MODIFIED_ADMIN';
                tampered.push(el.name || el.id || 'hidden_input');
            });
            return tampered;
        }
        """
        try:
            return page.evaluate(script)
        except Exception:
            return []

    def attack(self, page: Page, duration: int):
        """Executes adversarial chaos and security bypass attacks."""
        self.log_action(f"Started Adversary security assault session (duration: {duration}s)")
        start_time = time.time()

        step = 0
        while time.time() - start_time < duration:
            step += 1
            try:
                # Vector 1: Tamper with hidden or readonly state
                tampered = self._tamper_hidden_and_readonly(page)
                if tampered:
                    self.log_action(f"Tampered with {len(tampered)} hidden/readonly fields: {', '.join(tampered[:3])}")

                # Vector 2: Force-unlock disabled buttons (bypassing client UI locks)
                unlocked = self._force_enable_disabled_controls(page)
                if unlocked:
                    self.log_action(f"Bypassed client locks on {len(unlocked)} disabled controls: {', '.join(unlocked[:3])}")

                # Vector 3: Inject adversarial security payloads into visible inputs
                inputs = page.query_selector_all("input:visible:not([type='submit']):not([type='button']), textarea:visible")
                if inputs:
                    target_input = random.choice(inputs)
                    payload = random.choice(self.ADVERSARIAL_PAYLOADS)
                    input_id = target_input.get_attribute("id") or target_input.get_attribute("name") or "field"

                    self.log_action(f"Adversarial probe on '{input_id}' with payload: {payload[:35]}...")
                    target_input.fill(payload)
                    page.wait_for_timeout(100)

                # Vector 4: Forcibly click action buttons even if application tried to lock them
                buttons = page.query_selector_all("button:visible, input[type='submit']:visible")
                if buttons:
                    target_btn = random.choice(buttons)
                    btn_text = (target_btn.text_content() or "Submit").strip()[:30]
                    self.log_action(f"Adversarial force-click on '{btn_text}'")
                    target_btn.click(timeout=800, no_wait_after=True, force=True)

                page.wait_for_timeout(350)

            except Exception as e:
                self.log_action(f"Adversary cycle note: {str(e)[:40]}")
                page.wait_for_timeout(300)

        self.log_action("Finished Adversary security assault session")

    def attack_step(self, page: Page, step: dict):
        """Mutates recorded journey steps with security bypasses and payload injections."""
        event_type = step.get("action") or step.get("type")
        selector = step.get("selector")
        target_name = step.get("value") or step.get("text") or step.get("id") or selector

        if event_type == "input":
            payload = random.choice(self.ADVERSARIAL_PAYLOADS)
            self.log_action(f"Adversary: Mutating journey input '{target_name}' with payload: {payload[:30]}...")
            try:
                el = page.query_selector(selector)
                if el:
                    el.fill(payload)
            except Exception:
                pass

        elif event_type == "click":
            self.log_action(f"Adversary: Executing journey click on '{target_name}'")
            try:
                el = page.query_selector(selector)
                if el:
                    el.click(timeout=500, no_wait_after=True, force=True)
                    page.wait_for_timeout(100)
                    # Forcibly remove disabled and click again to probe server-side idempotency
                    self._force_enable_disabled_controls(page)
                    self.log_action(f"Adversary: Forcing duplicate execution on '{target_name}'")
                    el.click(timeout=500, no_wait_after=True, force=True)
            except Exception:
                pass
