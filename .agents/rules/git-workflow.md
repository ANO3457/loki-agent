# Git & Version Control Protocol (`git-workflow.md`)

## 1. Commit & Push Cadence
- **Atomic Milestones**: Stage, commit, and push changes to GitHub (`origin/main`) immediately after completing and verifying each discrete feature, bug fix, or milestone.
- **Never Leave Work Stale**: Do not accumulate multiple unrelated features in a single uncommitted batch.

## 2. Command Execution in Windows PowerShell
- **Command Chaining**: In Windows PowerShell, NEVER use `&&` as a command separator. Always use `;` to chain commands:
  ```powershell
  # CORRECT:
  git add . ; git commit -m "feat: implement mobile device matrix" ; git push

  # WRONG (fails on many Windows PowerShell versions):
  git add . && git commit -m "..." && git push
  ```

## 3. Semantic Commit Messages
Commit messages MUST follow the Conventional Commits specification:
- `feat: <description>`: Introducing a new user-facing capability or CLI option.
- `fix: <description>`: Resolving a bug, unhandled exception, or unexpected behavior.
- `refactor: <description>`: Code restructuring without changing external behavior.
- `docs: <description>`: Updating README, AGENTS.md, or skill guides.
- `test: <description>`: Adding or improving test cases and validation scripts.
- `chore: <description>`: Maintenance tasks, dependencies updates, or build scripts.

*Rule:* Commit messages MUST be written 100% in English.

## 4. Gitignore Hygiene
Ensure the following are NEVER committed to version control:
- Local run artifacts: `.loki/runs/`
- Temporary backups: `*.loki.bak`
- Python caches & virtualenvs: `__pycache__/`, `.venv/`, `venv/`
- Packaging artifacts: `dist/`, `build/`, `*.spec`
- Secret environment variables or API keys.
