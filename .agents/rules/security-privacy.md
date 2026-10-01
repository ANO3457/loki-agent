# Security, Privacy & Sanitization Guardrails (`security-privacy.md`)

## 1. Network Archive Scrubbing (HAR Traces)
- All network archives captured during chaos sessions (`network.har`) MUST be sanitized through `NetworkScrubber` before being saved to disk or committed.
- **Sensitive Headers Redacted**: `Authorization`, `Cookie`, `Set-Cookie`, `X-Auth-Token`, `X-Api-Key`, `Proxy-Authorization`.
- Replace sensitive header and cookie values with deterministic mask tokens (e.g. `[REDACTED_BY_LOKI]`).

## 2. Interactive Journey Recording Masking
- When users record workflows (`loki record --name <flow>`), any inputs to password fields (`type="password"`), elements with `autocomplete="current-password"`, or fields containing `token`, `secret`, or `key` in their IDs/names MUST have their typed text masked to `********`.
- Never store raw credentials in `.loki/journeys/*.json`.

## 3. Isolated Sandboxing
- Each test run must launch inside a clean, ephemeral browser context (`browser.new_context()`).
- Cookies, local storage, and session state must be wiped between test sessions to guarantee deterministic reproducibility.

## 4. API Key Hygiene
- API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) must strictly be read from environment variables (`os.environ`).
- Never hardcode or log API keys in terminal outputs, reports, or incident bundles.

## 5. Target Authorization Guardrail
- `run`/`record` (`src/loki/cli.py`) MUST call `ensure_target_authorized()` on the resolved URL before launching any browser session against it.
- Localhost/loopback is always allowed with no friction. Any other host requires an explicit, persisted confirmation (`loki auth add`, the interactive typed-hostname prompt, or `--authorized` for CI) before an attack runs.
- Never add a way to skip, suppress, or auto-confirm this check other than the existing `--authorized` flag and the per-host `.loki/authorized_targets.json` record — including when asked to "just make it work" against a specific target. If a target isn't authorized, that's a stop, not an obstacle to route around.

## 6. Infrastructure Chaos Scope (`src/loki/engine/infra_chaos.py`)
- `loki infra` only ever targets processes/containers reachable on the **local machine** (direct PID/port signaling, or the local Docker daemon). It has no SSH, remote Docker context, or cloud-provider backend, and none should be added without the exact same per-host authorization gate as `safety.py` first — reaching a *remote* host's infrastructure is a categorically bigger trust escalation than attacking a public URL.
- `kill_process`/`pause_process` refuse to target LOKI's own PID/parent PID or anything matching a protected system-process name fragment (`_PROTECTED_NAME_FRAGMENTS`). Never remove or narrow this check to satisfy a specific request.
- `--name` matching targets *any* process whose name contains the given substring, which can be broader than intended (confirmed risky enough that this host's own sandbox classifier refused to let a test run `--name python` against a shared multi-process machine). Prefer `--pid`/`--port` in docs/examples and don't suggest `--name` for anything that isn't obviously a single disposable process.
- `pause_process`'s suspend/resume (`psutil.Process.suspend()`/`resume()`) is the standard OS mechanism (SIGSTOP/SIGCONT on POSIX, `NtSuspendProcess` on Windows) and `kill_process`/`cpu_stress`/`memory_stress` are verified working, but `pause_process` itself could **not** be confirmed to actually halt execution in this project's dev/CI sandbox — `status()` reported "stopped" while the target kept running on schedule regardless. Treat it as unverified until confirmed on a real (non-sandboxed) machine; don't remove the caveat from the README/AGENTS.md without re-testing it for real first.
