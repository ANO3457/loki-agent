---
name: loki-development
description: Comprehensive developer guide and runbook for developing, extending, testing, and debugging the LOKI synthetic chaos testing platform.
---

# LOKI Development Skill

Use this skill whenever working on, modifying, or testing the LOKI repository.

## 1. Operating Rules
- **Application Scope**: LOKI is an independent CLI utility, NOT an importable Python library.
- **Language Standard**: Code, docstrings, variable names, CLI output, and commit messages MUST be in English. Conversations with the maintainer are in Spanish.
- **Git Protocol**: Every verified functional milestone must be staged, committed, and pushed to GitHub (`git add . ; git commit -m "..." ; git push`).
- **PowerShell Compatibility**: On Windows PowerShell, chain commands with `;`, never `&&`.
- **Model Standard**: LiteLLM model string for Google Gemini is `gemini/gemini-3.5-flash-lite`.

## 2. Quick Command Runbook
```powershell
# CLI entry help
python -m src.loki.cli --help

# Initialize workspace configuration
python -m src.loki.cli init

# Record interactive user workflow
python -m src.loki.cli record --name checkout_flow

# Run chaos assault (default or guided by recorded journey)
python -m src.loki.cli run
python -m src.loki.cli run -j checkout_flow -p novice-chaotic --headed

# Replay deterministic reproduction script
python -m src.loki.cli replay
python -m src.loki.cli replay --video

# AI root-cause diagnosis and code fix
python -m src.loki.cli fix
```

## 3. Extending Personas
When adding a new persona:
1. Create `src/loki/personas/<name>.py` extending `BasePersona`.
2. Implement `attack(self, page: Page, duration: int)`.
3. Implement `attack_step(self, page: Page, step: dict)` using `force=True` on clicks.
4. Add to `PersonaChoice` enum and wire into `src/loki/cli.py`.
