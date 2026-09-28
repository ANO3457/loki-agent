# LOKI Agent — Autonomous AI Developer & Agent Operating Manual (`AGENTS.md`)

This document serves as the canonical operating manual and architectural specification for any AI agent (Antigravity, Claude, Cursor, Copilot, ChatGPT, or autonomous coding agents) working on or extending the **LOKI Agent** codebase.

---

## 1. Project Identity & Philosophy

- **Name**: **LOKI** (Synthetic Chaos & Exploratory AI Testing Agent)
- **Nature**: Standalone CLI Application / Autonomous Testing Agent (similar to `docker`, `terraform`, or `gh`). **It is NOT a Python library** intended for third-party `import loki` usage.
- **Mission**: Automate dynamic black-box/gray-box chaos testing, visual workflow recording, AI-driven root cause diagnosis, deterministic reproduction, and natural language business rules enforcement (`rules.md`).

---

## 2. Universal Agent Rules & Policies

Any AI agent interacting with this repository MUST adhere to these non-negotiable rules:

1. **Language Policy**:
   - **User Conversation**: Spanish (when requested by the maintainer).
   - **Repository Artifacts**: **100% English**. All code, file and directory names, variable names, class names, function names, docstrings, terminal output messages, UI copy, and commit messages MUST be in English.
2. **Commit & Push Cadence**:
   - Push to GitHub (`git add . ; git commit -m "..." ; git push`) after **every** completed milestone or verified feature.
   - Use semantic commit messages (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
   - In Windows PowerShell, NEVER use `&&` as command separator; always use `;` (e.g. `git add . ; git commit -m "feat: ..." ; git push`).
3. **Diff & Code Integrity**:
   - When updating existing files, perform minimal targeted modifications (`replace_file_content`) rather than rewriting whole files.
   - Preserve existing comments and docstrings.
4. **Encoding & Windows Compatibility**:
   - Ensure UTF-8 stream handling (`sys.stdout.reconfigure(encoding="utf-8", errors="replace")`).
   - Use `force=True` on synthetic Playwright click bursts so rapid user interactions do not artificially hang on disabled UI elements.

---

## 3. Directory Structure & Architecture

```
d:/Proyectos/agente-ia/
├── .loki/                       # Project-level LOKI configuration and artifacts
│   ├── config.yaml             # Target URL, timeouts, LLM model settings
│   ├── rules.md                # Human-readable business rules evaluated by AI
│   ├── knowledge.json          # Detected tech stack and architectural fingerprint
│   ├── journeys/               # Recorded user workflow blueprints (<name>.json)
│   └── runs/                   # Captured incident bundles (run_<timestamp>/)
│       └── run_YYYYMMDD_HHMMSS/
│           ├── incident.json   # Full incident metadata, crashes, and console logs
│           ├── replay.webm     # Video recording of the failure session
│           ├── network.har     # Sanitized HTTP network archive (tokens & cookies scrubbed)
│           ├── report.html     # Standalone visual HTML dashboard
│           └── repro_test.py   # Standalone deterministic Playwright reproduction test
├── playground/                 # Local testbed for chaos testing and reproduction
│   └── index.html              # Test web application with realistic vulnerabilities
├── src/
│   └── loki/
│       ├── __init__.py
│       ├── cli.py              # Typer CLI application entry point
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── brain.py        # AIBrain: LiteLLM integration, diagnosis, rules evaluation
│       │   └── chat.py         # LokiChatSession: Interactive conversational QA terminal REPL
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── sandbox.py      # ChaosSandbox: Isolated Playwright browser, sniffer, DOM snapshot
│       │   ├── reporter.py     # IncidentReporter: Packages runs, repro scripts & bundles
│       │   ├── html_reporter.py # HTMLReporter: Standalone visual HTML dashboard with video & scorecard
│       │   ├── scrubber.py     # NetworkScrubber: Sanitizes HAR traces, auth tokens & cookies
│       │   ├── recorder.py     # JourneyRecorder: Interactive DOM event recorder & secret masking
│       │   ├── replayer.py     # IncidentReplayer: Deterministic test execution and video player
│       │   └── scanner.py      # ProjectScanner: Tech stack detector for 'loki init'
│       └── personas/
│           ├── __init__.py
│           ├── base.py         # BasePersona abstract base class
│           ├── rage_clicker.py # RageClickerPersona: Burst clicks & race conditions
│           ├── novice_chaotic.py # NoviceChaoticPersona: Input fuzzing, emojis & erratic keys
│           ├── network_tormentor.py # NetworkTormentorPersona: Latency throttling & offline drops
│           ├── adversary.py    # AdversaryPersona: Security probes, disabled locks bypass & tampering
│           └── swarm.py        # SwarmPersona: Orchestrates all chaos personas in multi-vector waves
├── AGENTS.md                   # This instruction manual for AI coding agents
├── requirements.txt            # Core dependencies (typer, rich, playwright, pyyaml, litellm)
└── SPECIFICATION.md            # Product specification and roadmap
```

---

## 4. Core CLI Commands Reference

All commands are run using Python module execution syntax:

```powershell
# 1. Initialize workspace and generate .loki/ configuration
python -m src.loki.cli init

# 2. Record interactive user workflows with credential masking
python -m src.loki.cli record --name checkout_flow

# 3. Execute chaotic testing (unguided, guided by journey, or swarm mode)
python -m src.loki.cli run
python -m src.loki.cli run --swarm          # Run all personas in coordinated assault waves
python -m src.loki.cli run --journey checkout_flow
python -m src.loki.cli run -p novice-chaotic --duration 5 --headed
python -m src.loki.cli run --open       # Automatically open HTML report in browser
python -m src.loki.cli run --no-rules    # Disable AI business rules evaluation

# 4. Generate or open interactive visual HTML report
python -m src.loki.cli report
python -m src.loki.cli report <run_id>
python -m src.loki.cli report --no-open

# 5. Diagnose latest crash and generate code patch using AI Brain
python -m src.loki.cli fix
python -m src.loki.cli fix <run_id>

# 6. Deterministically replay captured incident or open video
python -m src.loki.cli replay
python -m src.loki.cli replay --video

# 7. Launch interactive conversational QA assistant in terminal
python -m src.loki.cli chat
python -m src.loki.cli chat --model gemini/gemini-3.5-flash-lite
```

---

## 5. Subsystem Guidelines for Extending LOKI

### Adding a New Persona
1. Create `src/loki/personas/<persona_name>.py`.
2. Inherit from `BasePersona` (`src.loki.personas.base`).
3. Implement `attack(self, page: Page, duration: int)` for unguided exploratory fuzzing.
4. Implement `attack_step(self, page: Page, step: dict)` for mutating recorded journeys.
5. Register the new persona in `PersonaChoice` enum and in `run()` inside `src/loki/cli.py`.

### AI Brain Integration
- Powered by `litellm`.
- Primary production model: `gemini/gemini-3.5-flash-lite` (fast, cost-effective, high rate limits).
- Supported environment variables: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
- All AI prompts in `AIBrain` must instruct the model to return valid JSON or markdown diff blocks.

### Sniffer & Evidence Engine
- The sniffer listens to `page.on("pageerror")`, `page.on("console")` (error type), and HTTP `response.status >= 500`.
- The DOM snapshot captures concise element metadata (`tag`, `id`, `text`, `disabled`, `visible`) before page teardown, feeding into the AI business rules verification engine.

---

## 6. Testing & Quality Verification

Before committing changes:
1. Run `python -m src.loki.cli --help` to confirm CLI argument parsing is intact.
2. If changing personas or sandbox, run against `http://localhost:8000` (from `playground/index.html`).
3. Verify that both unguided attacks and guided journeys (`--journey`) execute without crashing the CLI.
4. Verify that AI rules evaluation gracefully handles missing API keys (`SKIPPED`) or network timeouts.
