<p align="center">
  <img src="assets/logo.png" alt="LOKI Logo" width="180" />
</p>

<h1 align="center">LOKI</h1>

<p align="center">
  <strong>Autonomous AI Testing & Synthetic Chaos Agent</strong>
</p>

<p align="center">
  <a href="https://github.com/Elabsurdo984/loki-agent/actions"><img src="https://img.shields.io/github/actions/workflow/status/Elabsurdo984/loki-agent/loki.yml?branch=main&label=CI%2FCD%20Gate&logo=github" alt="CI Gate" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python Version" /></a>
  <a href="https://playwright.dev/"><img src="https://img.shields.io/badge/Playwright-Chromium-green?logo=playwright" alt="Playwright" /></a>
  <a href="https://litellm.ai/"><img src="https://img.shields.io/badge/AI%20Brain-Gemini%20%2F%20LiteLLM-purple" alt="LiteLLM" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-orange.svg" alt="License" /></a>
</p>

---

## ⚡ Overview

**LOKI** is an autonomous CLI testing agent designed to break, explore, and verify modern web applications before your users do. Operating as a standalone developer tool (similar to `docker`, `terraform`, or `gh`), LOKI combines **synthetic chaos personas**, **automated visual recording**, **AI business rule verification**, and **forensic network analysis** into an end-to-end quality gate.

Unlike traditional testing frameworks that test for "happy paths", LOKI deliberately injects chaos: race conditions, input fuzzing, network drops, and security tampering. When a failure is detected, LOKI packages the incident into a deterministic reproduction script, video replay, and standalone HTML scorecard.

---

## 🌟 Key Capabilities

### 🐝 1. Swarm Mode & 4 Chaos Personas
LOKI simulates realistic, erratic human behaviors through specialized personas:
* **`RageClicker`**: Targets interactive buttons with rapid burst clicks to provoke double-submissions and race conditions.
* **`NoviceChaotic`**: Fuzzes inputs with massive unicode strings, negative values, and erratic keyboard strokes.
* **`NetworkTormentor`**: Dynamically throttles network conditions (Slow 3G, 1200ms latency) and simulates abrupt offline connection drops mid-flight.
* **`Adversary`**: Bypasses client-side UI protections (strips `disabled` and `aria-disabled` attributes), tampers with hidden form fields, and probes with security payloads.
* **`Swarm`** (`--swarm`): Coordinates all personas in multi-vector assault waves.

### 📋 2. AI Business Rules Verification (`rules.md`)
Define human-readable business invariants in `.loki/rules.md`:
```markdown
- "Double clicking payment button must never trigger duplicate charges or unhandled errors."
- "Invalid coupon codes must display an error message and keep checkout button disabled."
```
At the end of an assault session, LOKI's AI Brain (`gemini-3.5-flash-lite` via LiteLLM) observes the live DOM snapshot, console logs, and network events to evaluate each rule as **`PASSED`** or **`VIOLATED`** with detailed evidence.

### 🌐 3. Forensic Network Capture & Privacy Scrubber (`network.har`)
* Automatically captures full HTTP network traffic in standard `.har` format.
* **Network Scrubber**: Automatically redacts sensitive tokens, bearer headers (`Authorization`), session cookies (`Cookie`, `Set-Cookie`), API keys, and passwords before storing archives.

### 📹 4. Standalone Visual HTML Reports & Replay Videos
* Generates interactive, standalone HTML dashboards with embedded `<video>` replays, business rule scorecards, network archives, and chronological timelines.
* Review incidents offline or share reports across your engineering team.

### ⚡ 5. Deterministic Playwright Reproduction (`repro_test.py`)
* When an unhandled crash or HTTP 500 error occurs, LOKI automatically synthesizes a standalone Playwright script that deterministically reproduces the exact incident.

### 💬 6. Conversational QA Terminal Assistant (`loki chat`)
* Launch an interactive terminal REPL connected to LOKI's AI Brain.
* Chat about recent runs, analyze crash traces, inspect rules, and receive actionable refactoring suggestions directly in your console.

### 🛡️ 7. Strict CI/CD Quality Gate
* Seamlessly integrates into GitHub Actions, GitLab CI, or pre-commit pipelines (`--ci`, `--strict`).
* Automatically formats and publishes test summaries to `$GITHUB_STEP_SUMMARY` and enforces deterministic exit codes (`0` on pass, `1` on failure).

### 🚑 8. Autonomous Code Self-Healing (`loki fix --apply` & `loki run --auto-heal`)
* Synthesizes precise, minimal surgical code patches to permanently eliminate the root cause of crashes.
* Safely creates automatic backups (`.loki.bak`), applies the patch to your source code, and runs a closed-loop reproduction verification test.
* If the crash still reproduces, LOKI automatically restores your code safely from backup.

---

## 🚀 Quickstart

### 1. Installation

#### Option A: Standalone Precompiled Binaries (Zero Python Required)
Download the standalone executable directly from [GitHub Releases](https://github.com/Elabsurdo984/loki-agent/releases):
* **Windows**: `loki-windows-amd64.exe`
* **Linux**: `loki-linux-amd64`
* **macOS (Apple Silicon)**: `loki-macos-arm64`

#### Option B: Global Isolated Install with `uv` (Recommended for developers)
```bash
# Install globally as a standalone command (fastest):
uv tool install git+https://github.com/Elabsurdo984/loki-agent.git

# Or run instantly without installing (like npx):
uvx --from git+https://github.com/Elabsurdo984/loki-agent.git loki run http://localhost:8000 --swarm
```

#### Option C: Global Install with `pipx`
```bash
pipx install git+https://github.com/Elabsurdo984/loki-agent.git
```

#### Option D: Local Development from Source
```bash
git clone https://github.com/Elabsurdo984/loki-agent.git
cd loki-agent

python -m venv .venv
# Activate: .\.venv\Scripts\Activate.ps1 (Windows) or source .venv/bin/activate (Linux/macOS)
pip install -e .
```

### 2. Configure AI Brain (Optional for AI features)
Export your preferred LLM API key (Google Gemini, OpenAI, or Anthropic):
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key"

# Linux / macOS
export GEMINI_API_KEY="your-gemini-api-key"
```

### 3. Initialize Workspace
Analyze your target project and generate `.loki/` configuration:
```bash
loki init
```

### 4. Unleash Chaos
Execute an exploratory chaos attack on your local or remote application:
```bash
# Run 6-second Swarm assault and open visual HTML report
loki run http://localhost:8000 --swarm --duration 6 --open

# Run specific persona in visible browser
loki run http://localhost:8000 -p adversary --headed
```

---

## 📖 CLI Commands Reference

| Command | Description |
| :--- | :--- |
| `loki init` | Detect project tech stack and initialize `.loki/` config and rules |
| `loki record --name <flow>` | Interactively record a user journey blueprint with credential masking |
| `loki run [url]` | Execute chaos attack session against target URL |
| `loki run --swarm` | Orchestrate all 4 chaos personas in coordinated assault waves |
| `loki run --auto-heal` | Autonomously synthesize, apply, and verify a code fix on crash |
| `loki run --journey <name>` | Attack a specific recorded journey blueprint |
| `loki run --ci` | Run in strict CI/CD mode (exit code 1 on failures, writes Step Summary) |
| `loki report` | View or generate standalone HTML dashboard for latest or specific run |
| `loki fix` | Diagnose latest captured crash with AI reasoning and generate code patch |
| `loki fix --apply` | Synthesize surgical patch, apply to code, and verify with repro test |
| `loki replay` | Deterministically replay captured incident or open video (`--video`) |
| `loki chat` | Launch conversational QA terminal assistant REPL |

---

## 📁 Repository Structure

```
loki-agent/
├── assets/                     # Brand assets and transparent logos
│   └── logo.png                # Official LOKI flat vector brandmark
├── .github/
│   └── workflows/
│       ├── loki.yml            # Automated CI/CD quality gate workflow
│       └── release.yml         # Cross-platform binary compilation & releases
├── .loki/                      # Local configuration and captured artifacts
│   ├── config.yaml             # Target URL, timeouts, model settings
│   ├── rules.md                # Human-readable business rules evaluated by AI
│   ├── knowledge.json          # Architectural fingerprint of the target app
│   ├── journeys/               # Recorded user workflow blueprints
│   └── runs/                   # Captured incident bundles
│       └── run_YYYYMMDD_HHMMSS/
│           ├── incident.json   # Full incident metadata, crashes, and logs
│           ├── replay.webm     # Video recording of the failure session
│           ├── network.har     # Sanitized HTTP archive (tokens scrubbed)
│           ├── report.html     # Standalone visual HTML dashboard
│           └── repro_test.py   # Standalone Playwright reproduction script
├── playground/                 # Local testbed with intentional edge-case bugs
│   └── index.html              # Interactive e-commerce checkout vulnerability playground
├── src/
│   └── loki/
│       ├── cli.py              # Typer CLI application entry point
│       ├── ai/
│       │   ├── brain.py        # LiteLLM integration, diagnosis, rules reasoning
│       │   └── chat.py         # LokiChatSession: Interactive terminal REPL
│       ├── engine/
│       │   ├── sandbox.py      # ChaosSandbox: Isolated Playwright browser & sniffer
│       │   ├── reporter.py     # Incident packaging and bundle persistence
│       │   ├── html_reporter.py # Standalone visual HTML dashboard renderer
│       │   ├── scrubber.py     # NetworkScrubber: Sanitizes HAR traces & cookies
│       │   ├── recorder.py     # JourneyRecorder: Interactive DOM event recorder
│       │   ├── replayer.py     # IncidentReplayer: Deterministic reproduction
│       │   ├── healer.py       # CodeHealer: Autonomous patch synthesizer & verification
│       │   ├── ci.py           # CIGate: CI environment detection & Step Summary
│       │   └── scanner.py      # ProjectScanner: Tech stack detector
│       └── personas/
│           ├── base.py         # BasePersona abstract class
│           ├── rage_clicker.py # Burst clicks and concurrency racing
│           ├── novice_chaotic.py # Input fuzzing and erratic navigation
│           ├── network_tormentor.py # Latency throttling and offline drops
│           ├── adversary.py    # UI locks bypass and security probes
│           └── swarm.py        # Multi-vector assault orchestrator
├── requirements.txt            # Core dependencies
└── AGENTS.md                   # Canonical operating manual for AI coding agents
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
