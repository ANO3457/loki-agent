import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import litellm
litellm.suppress_debug_info = True

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.status import Status


class LokiChatSession:
    """Interactive conversational terminal REPL for pair QA testing, incident queries, and advice."""

    def __init__(self, model: str = "gemini/gemini-3.6-flash", runs_dir: str = ".loki/runs"):
        self.model = model
        self.runs_dir = Path(runs_dir)
        self.console = Console()
        self.history: List[Dict[str, str]] = []

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

[cyan]Commands:[/cyan] [bold]/help[/bold] (commands), [bold]/runs[/bold] (list runs), [bold]/rules[/bold] (view rules), [bold]/clear[/bold] (clear screen), [bold]exit[/bold] (quit)""",
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
            try:
                user_input = self.console.input("\n[bold red]loki > [/bold red]").strip()
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

            # Models to attempt with fallback if 503 high demand occurs
            candidate_models = [self.model]
            for fallback in ["gemini/gemini-3.6-flash", "gemini/gemini-flash-lite-latest", "gemini/gemini-3.5-flash-lite"]:
                if fallback not in candidate_models:
                    candidate_models.append(fallback)

            success = False
            for target_model in candidate_models:
                try:
                    with Status(f"[bold yellow]LOKI is thinking...[/bold yellow]", console=self.console):
                        stream_response = litellm.completion(
                            model=target_model,
                            messages=active_messages,
                            stream=True,
                            timeout=25,
                            num_retries=1,
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
                        break

            if not success:
                self.console.print("\n[bold red]AI Error:[/bold red] Service currently experiencing high demand. Please try again in a moment.")
