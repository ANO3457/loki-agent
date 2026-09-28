# Synthetic Chaos Personas Reference (`personas.md`)

This reference details the attack vectors, behavioral mechanics, and mutation strategies for LOKI's chaos personas.

---

## 1. Rage Clicker (`RageClickerPersona`)
- **Intent**: Emulates frustrated users frantically clicking unresponsive buttons, double-submitting forms, or triggering race conditions.
- **Unguided Attack**:
  - Finds all visible buttons (`button:visible, input[type='submit']:visible, [role='button']:visible`).
  - Dispatches rapid bursts of 5–10 clicks per element with `force=True`, `timeout=1000`, and `no_wait_after=True`.
- **Guided Journey Attack (`attack_step`)**:
  - When the journey encounters a click step, it fires 4 rapid additional clicks immediately following the initial interaction.

---

## 2. Novice Chaotic (`NoviceChaoticPersona`)
- **Intent**: Emulates non-technical or erratic users entering invalid inputs, boundary extremes, and unexpected keys.
- **Unguided Attack**:
  - Dispatches fuzz strings into text inputs: SQL injection probes, multi-byte emojis (`💥👾🚀🔥`), 10,000-character overflow strings, negative numbers, and null bytes.
  - Presses erratic navigation keys: `Escape`, `Tab`, `Backspace`, `Enter`, `PageDown`.
- **Guided Journey Attack (`attack_step`)**:
  - When the journey enters text, it appends bizarre characters or deletes half the string before submitting.

---

## 3. Network Tormentor (`NetworkTormentorPersona`)
- **Intent**: Simulates real-world mobile network conditions: spotty cellular reception, tunnel drops, and high-latency APIs.
- **Mechanics**:
  - Leverages Chrome DevTools Protocol (CDP) session (`page.context.new_cdp_session(page)`).
  - Toggles `Network.emulateNetworkConditions` between Offline, Slow 3G (400ms latency, 400kbps download), and normal throughput.
  - Causes timeouts, connection resets, and inflight request aborts.

---

## 4. Adversary (`AdversaryPersona`)
- **Intent**: Simulates a malicious attacker or power user bypassing client-side locks.
- **Mechanics**:
  - Removes `disabled` and `readonly` attributes from DOM elements via JavaScript evaluation.
  - Forces hidden input fields or obscured buttons to become visible (`display: block !important`).
  - Alters values of disabled submit buttons or hidden checkout totals and triggers form submissions.

---

## 5. Swarm (`SwarmPersona`)
- **Intent**: Multi-vector assault orchestrating all four personas in coordinated waves.
- **Execution Flow**:
  - Divides total session duration into equal time windows.
  - Dispatches `NoviceChaotic` (Wave 1: Input fuzzing) → `Adversary` (Wave 2: Lock tampering) → `NetworkTormentor` (Wave 3: Packet throttling) → `RageClicker` (Wave 4: Race condition click burst).
