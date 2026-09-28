# Coding Standards & Python Engineering (`coding-standards.md`)

## 1. Architectural Philosophy
- **Standalone CLI Application**: LOKI is a standalone developer tool / CLI application (like `docker`, `terraform`, or `gh`). It is **NOT** a Python library designed for third-party `import loki` usage.
- **Minimal External Dependencies**: Keep core dependencies focused (`typer`, `rich`, `playwright`, `pyyaml`, `litellm`, `tenacity`). Avoid bloat.

## 2. Python & Code Style Conventions
- **Target Version**: Python 3.10+.
- **Type Annotations**: Enforce strict type hints (`Optional`, `List`, `Dict`, `Union`, `Tuple`, `Path`) across all function signatures, public methods, and dataclass fields.
- **Targeted Modifications**: When editing existing code, make minimal, surgical replacements (`replace_file_content`). Never rewrite entire modules if only a few lines need updating.
- **Preserve Documentation**: Always preserve existing docstrings, module documentation, and inline comments unrelated to your changes.

## 3. Platform & Encoding Guardrails (Windows & POSIX)
- **UTF-8 Output Encoding**: Windows PowerShell often defaults to CP1252/`charmap`, causing unhandled codec crashes when printing emojis or unicode symbols. Every entrypoint or script generating terminal output must ensure UTF-8 streams:
  ```python
  import sys
  if hasattr(sys.stdout, "reconfigure"):
      try:
          sys.stdout.reconfigure(encoding="utf-8", errors="replace")
          sys.stderr.reconfigure(encoding="utf-8", errors="replace")
      except Exception:
          pass
  ```
- **File I/O**: Always specify `encoding="utf-8"` when reading or writing files:
  ```python
  with open(filepath, "w", encoding="utf-8") as f:
      ...
  ```

## 4. Playwright & Browser Automation Guardrails
- **Synthetic Click Bursts**: Real users and chaos personas click aggressively. In Playwright, buttons that get briefly disabled or obscured will cause clicks to hang indefinitely on actionability checks unless forced:
  ```python
  # Always use force=True and short timeouts on chaos bursts
  element.click(timeout=1000, force=True, no_wait_after=True)
  ```
- **Safe Evaluation**: Wrap in-browser JavaScript evaluations in try/except blocks or fallback handling so unresponsive or terminating pages do not crash the agent runner.
- **Context Teardown**: Always ensure `context.close()` and `browser.close()` are called in `finally` blocks to prevent zombie browser processes.
