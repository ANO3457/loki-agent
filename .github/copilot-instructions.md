# GitHub Copilot Instructions

This repository is governed by the universal agent operating constitution in [**`AGENTS.md`**](../AGENTS.md).

Key guidelines for GitHub Copilot:
1. **Standalone Application**: LOKI is a standalone CLI tool, NOT an importable Python library.
2. **Language Policy**: Maintainer conversation in Spanish; all code, comments, docstrings, commits, and terminal outputs in 100% English.
3. **Windows PowerShell**: Never chain commands with `&&`; always use `;`.
4. **Playwright Interactions**: Always use `force=True`, `timeout=1000`, and `no_wait_after=True` on synthetic chaos click bursts.
5. **Encoding**: Ensure UTF-8 output stream reconfiguration to avoid Windows `charmap` codec crashes.
