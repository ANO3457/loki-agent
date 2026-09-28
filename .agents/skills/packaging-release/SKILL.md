---
name: packaging-release
description: Operational runbook for compiling standalone cross-platform binaries with PyInstaller, publishing GitHub releases, and deploying via uv or pipx.
---

# Packaging & Release Runbook Skill

Use this skill whenever building standalone binaries, releasing a new version, or testing global installation methods.

## 1. Local PyInstaller Compilation

```powershell
# Compile single-file executable locally on Windows
pyinstaller --clean --noconfirm --name loki-windows-amd64 --onedir `
  --collect-all playwright `
  --collect-all litellm `
  --collect-all typer `
  --collect-all rich `
  --collect-all yaml `
  loki_entry.py
```

*Note:* Never commit `dist/`, `build/`, or `*.spec` files to Git.

## 2. GitHub Release & Automated Compilation
- Tagging a new version automatically triggers `.github/workflows/release.yml`:
  ```powershell
  git tag -a v1.1.0 -m "Release v1.1.0: Mobile Matrix & Autonomous Self-Healing"
  git push origin v1.1.0
  ```
- The CI pipeline compiles standalone executables for:
  - Windows: `loki-windows-amd64.exe`
  - Linux: `loki-linux-amd64`
  - macOS (Apple Silicon): `loki-macos-arm64`

## 3. Global Installation with `uv` (Recommended)

```bash
# Install globally in isolated virtualenv
uv tool install git+https://github.com/Elabsurdo984/loki-agent.git

# Run directly via uvx (like npx)
uvx --from git+https://github.com/Elabsurdo984/loki-agent.git loki run http://localhost:8000 --swarm
```
