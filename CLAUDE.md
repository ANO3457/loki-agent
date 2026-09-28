# Claude Code Operating Instructions

This repository is governed by the universal agent operating constitution in [**`AGENTS.md`**](./AGENTS.md).

All coding agents, including Claude Code, must strictly comply with the guidelines defined in `AGENTS.md`, notably:
1. **Language Policy**: Conversation with maintainer in Spanish; 100% English for code, commits, and documentation.
2. **Platform Rule**: On Windows PowerShell, NEVER use `&&`; always chain commands with `;` (e.g. `git add . ; git commit -m "..." ; git push`).
3. **Execution**: Use the virtual environment interpreter (`.\.venv\Scripts\python.exe` or `python -m src.loki.cli`).
4. **Subagents & Skills**: Consult [.agents/skills/](./.agents/skills/) and [.agents/rules/](./.agents/rules/) for domain-specific runbooks.
