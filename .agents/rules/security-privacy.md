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
