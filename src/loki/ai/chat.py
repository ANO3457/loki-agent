import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import litellm
litellm.suppress_debug_info = True

from src.loki.config import (
    activate_model_profile,
    add_model_profile,
    clear_active_model_profile,
    get_active_model_profile,
    is_ai_customized,
    list_model_profiles,
    model_source,
    remove_model_profile,
    resolve_ai_connection,
    resolve_model,
)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.status import Status

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter


class LokiChatSession:
    """Interactive conversational terminal REPL for pair QA testing, incident queries, and advice."""

    def __init__(self, model: Optional[str] = None, runs_dir: str = ".loki/runs"):
        self._explicit_model = model
        self.model = resolve_model(model)
        self.runs_dir = Path(runs_dir)
        self.console = Console()
        self.history: List[Dict[str, str]] = []
        self._prompt_session: Optional[PromptSession] = None
        self._use_boxed_prompt = True

    def _load_project_context(self) -> str:
        """Assembles repository context: config, rules, and knowledge."""
        context_parts = []

        # 1. Configuration
        config_file = Path(".loki/config.yaml")
        if config_file.exists():
            context_parts.append(f"### Project Configuration (.loki/config.yaml):\n{config_file.read_text(encoding='utf-8')}")

        # 2. Business Rules
        rules_file = Path(".loki/rules.md")
        if rules_file.exists():
            context_parts.append(f"### Active Business Rules (.loki/rules.md):\n{rules_file.read_text(encoding='utf-8')}")

        # 3. Knowledge / Stack
        knowledge_file = Path(".loki/knowledge.json")
        if knowledge_file.exists():
            context_parts.append(f"### Tech Stack Knowledge (.loki/knowledge.json):\n{knowledge_file.read_text(encoding='utf-8')}")

        # 4. Recent Runs Summary
        recent_runs = self._get_recent_runs_summary(limit=3)
        if recent_runs:
            context_parts.append(f"### Recent Test & Incident Runs:\n{recent_runs}")

        return "\n\n".join(context_parts)

    def _get_recent_runs_summary(self, limit: int = 3) -> str:
        """Summarizes recent test runs and incidents."""
        if not self.runs_dir.exists():
            return "No previous runs recorded."

        run_dirs = [d for d in self.runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
        if not run_dirs:
            return "No previous runs recorded."

        run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        summaries = []

        for d in run_dirs[:limit]:
            meta_file = d / "incident.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    crashes_cnt = data.get("unique_crashes_count", 0)
                    rules_cnt = len(data.get("rules_evaluations", []))
                    summaries.append(
                        f"- Run `{d.name}` ({data.get('timestamp', 'unknown')}): "
                        f"Persona: {data.get('persona', 'unknown')}, "
                        f"Target: {data.get('target_url')}, "
                        f"Crashes: {crashes_cnt}, "
                        f"Rules Evaluated: {rules_cnt}"
                    )
                except Exception:
                    pass

        return "\n".join(summaries) if summaries else "No readable runs found."

    def _display_runs_table(self):
        """Displays a Rich table of recorded runs."""
        if not self.runs_dir.exists():
            self.console.print("[yellow]No runs directory found.[/yellow]")
            return

        run_dirs = [d for d in self.runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
        if not run_dirs:
            self.console.print("[yellow]No recorded runs yet.[/yellow]")
            return

        run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        table = Table(title="📦 LOKI Recorded Test Runs", border_style="cyan")
        table.add_column("Run ID", style="bold cyan")
        table.add_column("Persona", style="magenta")
        table.add_column("Crashes", justify="center")
        table.add_column("Verdict", justify="center")
        table.add_column("HTML Report", style="dim")

        for d in run_dirs[:10]:
            meta_file = d / "incident.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    crashes = data.get("unique_crashes_count", 0)
                    rules = data.get("rules_evaluations", [])
                    has_violation = any(r.get("status") == "VIOLATED" for r in rules)
                    verdict = "[red]FAIL[/red]" if (crashes > 0 or has_violation) else "[green]PASS[/green]"
                    report_path = f"{d.name}/report.html"
                    table.add_row(
                        d.name,
                        data.get("persona", "Unknown"),
                        str(crashes),
                        verdict,
                        report_path,
                    )
                except Exception:
                    continue

        self.console.print(table)

    def _display_rules(self):
        """Displays active business rules from .loki/rules.md."""
        rules_file = Path(".loki/rules.md")
        if not rules_file.exists():
            self.console.print("[yellow]No .loki/rules.md file found.[/yellow]")
            return
        self.console.print(Panel(rules_file.read_text(encoding="utf-8"), title="📋 Active Business Rules", border_style="cyan"))

    def _show_model_status(self):
        """Displays the current effective model, where it came from, and saved profiles."""
        current = resolve_model(self._explicit_model)
        source = model_source(self._explicit_model)
        profiles = list_model_profiles()
        active = get_active_model_profile()
        active_name = active["name"] if active else None

        lines = [f"[bold white]Current model:[/bold white] [cyan]{current}[/cyan] [dim]({source})[/dim]", ""]
        if profiles:
            lines.append("[bold white]Saved profiles:[/bold white]")
            for p in profiles:
                marker = "[bold green]▸[/bold green]" if p.get("name") == active_name else " "
                extra = "".join(
                    f" [dim]{k}={v}[/dim]" for k, v in (("api_base", p.get("api_base")), ("api_key_env", p.get("api_key_env"))) if v
                )
                lines.append(f"  {marker} [bold]{p['name']}[/bold] → {p['model']}{extra}")
        else:
            lines.append("[dim]No saved profiles yet — every LOKI AI feature (chat, rules, fix) is reading straight from .loki/config.yaml.[/dim]")

        lines.extend([
            "",
            "[bold white]Commands:[/bold white]",
            "  [cyan]/model <name>[/cyan]                     — switch to a saved profile",
            "  [cyan]/model add <name> <model-id> [api_base=...] [api_key_env=...][/cyan] — save & switch",
            "  [cyan]/model remove <name>[/cyan]              — delete a saved profile",
            "  [cyan]/model reset[/cyan]                       — revert to .loki/config.yaml's default",
            "",
            "[dim]e.g. /model add local ollama/llama3[/dim]",
            "[dim]e.g. /model add work mistral/mistral-large-latest api_key_env=MISTRAL_API_KEY[/dim]",
        ])
        self.console.print(Panel("\n".join(lines), title="🧠 AI Model", border_style="cyan"))

    def _handle_model_command(self, args: str):
        """Parses and executes a `/model ...` command, switching every LOKI AI
        feature (chat, rules evaluation, fix, auto-heal) to the chosen connection."""
        parts = args.split()
        if not parts:
            self._show_model_status()
            return

        sub = parts[0].lower()

        if sub == "add":
            if len(parts) < 3:
                self.console.print("[yellow]Usage: /model add <name> <model-id> [api_base=<url>] [api_key_env=<VAR>][/yellow]")
                return
            name, model_id = parts[1], parts[2]
            api_base, api_key_env = None, None
            for token in parts[3:]:
                if token.startswith("api_base="):
                    api_base = token.split("=", 1)[1]
                elif token.startswith("api_key_env="):
                    api_key_env = token.split("=", 1)[1]
            add_model_profile(name, model_id, api_base=api_base, api_key_env=api_key_env)
            activate_model_profile(name)
            self._explicit_model = None
            self.model = resolve_model(None)
            self.console.print(f"[bold green]✔ Saved and switched to profile '{name}' → {model_id}[/bold green]")
            return

        if sub == "remove":
            if len(parts) < 2:
                self.console.print("[yellow]Usage: /model remove <name>[/yellow]")
                return
            name = parts[1]
            if remove_model_profile(name):
                self._explicit_model = None
                self.model = resolve_model(None)
                self.console.print(f"[green]✔ Removed profile '{name}'. Now using: {self.model}[/green]")
            else:
                self.console.print(f"[yellow]No profile named '{name}' found.[/yellow]")
            return

        if sub in ("reset", "default"):
            clear_active_model_profile()
            self._explicit_model = None
            self.model = resolve_model(None)
            self.console.print(f"[green]✔ Reverted to .loki/config.yaml's default: {self.model}[/green]")
            return

        # Otherwise: treat the argument as a profile name to switch to
        name = parts[0]
        profile = activate_model_profile(name)
        if not profile and "/" in name:
            # Looks like a bare "provider/model" id rather than a saved profile name
            # — add it under its own name so it's there next time too.
            add_model_profile(name, name)
            profile = activate_model_profile(name)
        if not profile:
            self.console.print(
                f"[yellow]No saved profile named '{name}'.[/yellow] "
                f"Use [bold]/model add {name} <model-id>[/bold] to create it, or [bold]/model[/bold] to see what's saved."
            )
            return

        self._explicit_model = None
        self.model = resolve_model(None)
        self.console.print(f"[bold green]✔ Switched active model to '{profile['name']}' → {profile['model']}[/bold green]")

    def _build_completer(self) -> NestedCompleter:
        """Builds a fresh Tab/as-you-type completer, including saved /model profile names."""
        profile_names = [p["name"] for p in list_model_profiles()]
        model_targets: Dict[str, Any] = {name: None for name in profile_names}
        model_targets.update({
            "add": None,
            "remove": {name: None for name in profile_names} if profile_names else None,
            "reset": None,
            "default": None,
        })
        return NestedCompleter.from_nested_dict({
            "/model": model_targets,
            "/runs": None,
            "/rules": None,
            "/help": None,
            "/clear": None,
            "exit": None,
            "quit": None,
        })

    def _read_input(self) -> str:
        """Renders a boxed input prompt with live command autocomplete instead of a bare
        'loki > ' line. Falls back to a plain prompt for the rest of the session if the
        terminal can't support prompt_toolkit's rendering (e.g. some non-native consoles,
        piped/non-interactive input, or CI)."""
        if self._use_boxed_prompt and not (sys.stdin.isatty() and sys.stdout.isatty()):
            # No real interactive terminal (piped input, CI, some redirected subprocess
            # setups) — skip straight to plain input. Attempting prompt_toolkit here risks
            # it consuming/losing the first line of input before it fails.
            self._use_boxed_prompt = False

        if self._use_boxed_prompt:
            if self._prompt_session is None:
                try:
                    self._prompt_session = PromptSession()
                except Exception:
                    self._use_boxed_prompt = False

        if self._use_boxed_prompt and self._prompt_session is not None:
            width = max(20, min(self.console.width, 100))
            inner = width - 2
            self.console.print(f"[dim red]╭{'─' * inner}╮[/dim red]")
            try:
                text = self._prompt_session.prompt(
                    "│ ",
                    completer=self._build_completer(),
                    complete_while_typing=True,
                )
                self.console.print(f"[dim red]╰{'─' * inner}╯[/dim red]")
                return text.strip().lstrip("﻿")
            except (KeyboardInterrupt, EOFError):
                self.console.print(f"[dim red]╰{'─' * inner}╯[/dim red]")
                raise
            except Exception:
                # Terminal doesn't support prompt_toolkit's rendering — fall back below,
                # for this and every later turn this session.
                self.console.print(f"[dim red]╰{'─' * inner}╯[/dim red]")
                self._use_boxed_prompt = False

        return self.console.input("\n[bold red]❯[/bold red] ").strip().lstrip("﻿")

    def start(self):
        """Launches the interactive REPL chat session."""
        self.console.print(
            Panel(
                fr"""[bold red]  _       ____  _  __ _____     _____ _           _   [/bold red]
[bold red] | |     / __ \| |/ /|_   _|   / ____| |         | |  [/bold red]
[bold red] | |    | |  | | ' /   | |    | |    | |__   __ _| |_ [/bold red]
[bold red] | |    | |  | |  <    | |    | |    | '_ \ / _` | __|[/bold red]
[bold red] | |____| |__| | . \  _| |_   | |____| | | | (_| | |_ [/bold red]
[bold red] |______|\____/|_|\_\|_____|   \_____|_| |_|\__,_|\__|[/bold red]

[bold white]Interactive AI QA & Chaos Testing Assistant[/bold white]
[dim]Powered by LiteLLM ({self.model})[/dim]

[cyan]Commands:[/cyan] [bold]/help[/bold] (commands), [bold]/model[/bold] (switch AI model), [bold]/runs[/bold] (list runs), [bold]/rules[/bold] (view rules), [bold]/clear[/bold] (clear screen), [bold]exit[/bold] (quit)""",
                border_style="red",
            )
        )

        project_context = self._load_project_context()

        system_instruction = f"""You are LOKI, an elite AI Chaos & Software Quality Assurance Engineer.
You specialize in synthetic user simulation, race conditions, edge-case vulnerability testing, and automated root-cause analysis.

You are interacting live with the software developer or QA engineer via an interactive terminal REPL.
Answer questions directly, accurately, and concisely. When explaining crashes or suggesting fixes, provide exact code blocks or actionable guidance.

Project & Testing Context:
{project_context}
"""

        self.history.append({"role": "system", "content": system_instruction})

        while True:
            self.console.print()
            try:
                user_input = self._read_input()
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim]Session terminated. Goodbye![/dim]")
                break

            if not user_input:
                continue

            # Command dispatch
            cmd_lower = user_input.lower()
            if cmd_lower in ["exit", "quit", ":q"]:
                self.console.print("[dim]Exiting LOKI chat. Happy testing![/dim]")
                break

            if cmd_lower == "/help":
                self.console.print(
                    Panel(
                        "• [bold cyan]/model[/bold cyan] — View, switch, or add AI models (e.g. /model add local ollama/llama3)\n"
                        "• [bold cyan]/runs[/bold cyan] — List recent test runs, crashes, and report files\n"
                        "• [bold cyan]/rules[/bold cyan] — Display active business rules from .loki/rules.md\n"
                        "• [bold cyan]/clear[/bold cyan] — Clear terminal screen\n"
                        "• [bold cyan]exit[/bold cyan] / [bold cyan]quit[/bold cyan] — Exit interactive chat session\n"
                        "• Ask any question about QA testing, code bugs, race conditions, or past runs!",
                        title="💡 LOKI Chat Help",
                        border_style="cyan",
                    )
                )
                continue

            if cmd_lower == "/model" or cmd_lower.startswith("/model "):
                self._handle_model_command(user_input[len("/model"):].strip())
                continue

            if cmd_lower == "/runs":
                self._display_runs_table()
                continue

            if cmd_lower == "/rules":
                self._display_rules()
                continue

            if cmd_lower == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue

            # Multi-turn conversational query
            self.history.append({"role": "user", "content": user_input})

            # Prevent context bloat by retaining only recent conversation turns
            active_messages = self.history
            if len(self.history) > 12:
                # Keep system prompt at index 0, take last 10 messages
                active_messages = [self.history[0]] + self.history[-10:]

            # Any LiteLLM-compatible provider works here, not just Gemini/OpenAI/Anthropic.
            # Sibling-model fallbacks (for transient "high demand" errors) only apply to
            # LOKI's own bundled Gemini default — once the user configured `ai:` or
            # --model, try exactly that and nothing else.
            base_kwargs = resolve_ai_connection(self._explicit_model)
            attempts = [base_kwargs] if is_ai_customized(self._explicit_model) else [
                base_kwargs,
                {**base_kwargs, "model": "gemini/gemini-3.6-flash"},
                {**base_kwargs, "model": "gemini/gemini-flash-lite-latest"},
                {**base_kwargs, "model": "gemini/gemini-3.5-flash-lite"},
            ]

            success = False
            reported_error = False
            for kwargs in attempts:
                try:
                    with Status(f"[bold yellow]LOKI is thinking...[/bold yellow]", console=self.console):
                        stream_response = litellm.completion(
                            messages=active_messages,
                            stream=True,
                            timeout=25,
                            num_retries=1,
                            **kwargs,
                        )
                        # Read first token inside the status spinner to ensure response has started
                        first_chunk = ""
                        for chunk in stream_response:
                            delta = chunk.choices[0].delta.content or ""
                            if delta:
                                first_chunk = delta
                                break

                    # Stream text cleanly to stdout
                    self.console.print()
                    sys.stdout.write(first_chunk)
                    sys.stdout.flush()

                    collected = [first_chunk]
                    for chunk in stream_response:
                        delta = chunk.choices[0].delta.content or ""
                        if delta:
                            sys.stdout.write(delta)
                            sys.stdout.flush()
                            collected.append(delta)

                    sys.stdout.write("\n")
                    sys.stdout.flush()

                    full_reply = "".join(collected)
                    self.history.append({"role": "assistant", "content": full_reply})
                    success = True
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if "503" in err_str or "unavailable" in err_str or "timeout" in err_str:
                        # Silently try next fallback model
                        continue
                    else:
                        self.console.print(f"\n[bold red]AI Error:[/bold red] {e}")
                        reported_error = True
                        break

            if not success and not reported_error:
                self.console.print("\n[bold red]AI Error:[/bold red] Service currently experiencing high demand. Please try again in a moment.")
