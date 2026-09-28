from enum import Enum
from pathlib import Path
from typing import Optional
import sys
import typer
import yaml
import json

# Ensure standard output streams support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import webbrowser
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from src.loki.engine.sandbox import ChaosSandbox
from src.loki.engine.reporter import IncidentReporter
from src.loki.engine.html_reporter import HTMLReporter
from src.loki.engine.scanner import ProjectScanner
from src.loki.personas.rage_clicker import RageClickerPersona
from src.loki.personas.novice_chaotic import NoviceChaoticPersona
from src.loki.ai.brain import AIBrain
from src.loki.engine.recorder import JourneyRecorder
from src.loki.engine.replayer import IncidentReplayer

console = Console()
app = typer.Typer(
    name="loki",
    help="⚡ LOKI: Synthetic Chaos & Exploratory AI Testing Agent",
    add_completion=False,
)

class PersonaChoice(str, Enum):
    RAGE_CLICKER = "rage-clicker"
    NOVICE_CHAOTIC = "novice-chaotic"
    NONE = "none"

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Main entry point for LOKI."""
    if ctx.invoked_subcommand is None:
        banner = r"""
[bold red]  _       ____  _  __ _____ [/bold red]
[bold red] | |     / __ \| |/ /|_   _|[/bold red]
[bold yellow] | |    | |  | | ' /   | |  [/bold yellow]
[bold yellow] | |    | |  | |  <    | |  [/bold yellow]
[bold green] | |____| |__| | . \  _| |_ [/bold green]
[bold green] |______|\____/|_|\_\|_____|[/bold green]
        """
        console.print(banner)
        console.print(
            Panel(
                "[bold white]Welcome to LOKI's Chaos Realm.[/bold white]\n\n"
                "[dim]Autonomous agent simulating hostile users and breaking your software before production.[/dim]\n\n"
                "Run [bold cyan]python -m src.loki.cli --help[/bold cyan] to see available commands.",
                title="[bold yellow]⚡ LOKI Agent v0.1.0[/bold yellow]",
                border_style="red",
            )
        )

@app.command()
def version():
    """Display the installed version of Loki."""
    console.print("[bold yellow]LOKI Agent[/bold yellow] version [bold green]0.1.0[/bold green]")

@app.command()
def init(
    target_url: str = typer.Option("http://localhost:8000", "--url", "-u", help="Default target URL for this repository"),
):
    """Scan the repository and initialize LOKI configuration and business rules."""
    console.print("[bold cyan]⚡ Initializing LOKI Agent in current workspace...[/bold cyan]\n")

    scanner = ProjectScanner()

    with Status("[bold yellow]Scanning codebase fingerprint and stack...[/bold yellow]", console=console):
        stack_info = scanner.detect_stack()
        paths = scanner.initialize(default_target_url=target_url)

    languages = ", ".join(stack_info["languages"]) or "Generic / Polyglot"
    files = ", ".join(stack_info["detected_files"]) or "None"

    console.print(
        Panel(
            f"[bold green]✔ LOKI successfully initialized in this repository![/bold green]\n\n"
            f"[bold white]Detected Stack:[/bold white] [cyan]{languages}[/cyan]\n"
            f"[bold white]Signature Files:[/bold white] [dim]{files}[/dim]\n\n"
            f"[bold white]Generated Configuration Artifacts:[/bold white]\n"
            f"  ⚙ [cyan]{paths['config']}[/cyan] [dim](<Project & timeout configuration>)[/dim]\n"
            f"  📜 [cyan]{paths['rules']}[/cyan] [dim](<Plain English business rules>)[/dim]\n"
            f"  🧬 [cyan]{paths['knowledge']}[/cyan] [dim](<Detected architectural fingerprint>)[/dim]\n\n"
            f"[bold yellow]Next Step:[/bold yellow] Edit [bold cyan].loki/rules.md[/bold cyan] to add your custom business constraints, "
            f"or run [bold green]python -m src.loki.cli run {target_url}[/bold green] to launch an attack.",
            title="[bold green]🚀 Workspace Initialized[/bold green]",
            border_style="green",
        )
    )

def load_loki_config() -> dict:
    """Reads project configuration from .loki/config.yaml if available."""
    config_file = Path(".loki/config.yaml")
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

@app.command()
def run(
    url: Optional[str] = typer.Argument(None, help="The target URL to test (defaults to .loki/config.yaml if omitted)"),
    duration: Optional[int] = typer.Option(None, "--duration", "-d", help="Execution duration in seconds"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in visible mode (default is headless)"),
    persona: PersonaChoice = typer.Option(
        PersonaChoice.RAGE_CLICKER,
        "--persona",
        "-p",
        help="Synthetic chaos persona to simulate (rage-clicker or none)",
    ),
    journey: Optional[str] = typer.Option(
        None,
        "--journey",
        "-j",
        help="Recorded journey blueprint name (from .loki/journeys/) to guide the chaos attack",
    ),
    rules: bool = typer.Option(
        True,
        "--rules/--no-rules",
        "-r/-nr",
        help="Evaluate business assertions in .loki/rules.md using AI reasoning",
    ),
    report_html: bool = typer.Option(
        True,
        "--report/--no-report",
        help="Generate standalone visual HTML report with video and AI scorecard",
    ),
    open_report: bool = typer.Option(
        False,
        "--open",
        "-o",
        help="Automatically open the generated HTML report in the default browser",
    ),
):
    """Execute a monitored chaos attack on a target URL to sniff for crashes and errors."""
    # 1. Load journey blueprint if specified
    journey_data = None
    if journey:
        journey_path = Path(f".loki/journeys/{journey}.json" if not journey.endswith(".json") else f".loki/journeys/{journey}")
        if not journey_path.exists():
            journey_path = Path(journey)
        if not journey_path.exists():
            console.print(f"[bold red]Error:[/bold red] Journey blueprint '{journey}' not found in .loki/journeys/")
            raise typer.Exit(code=1)
        try:
            with open(journey_path, "r", encoding="utf-8") as f:
                journey_data = json.load(f)
        except Exception as e:
            console.print(f"[bold red]Error reading journey blueprint:[/bold red] {e}")
            raise typer.Exit(code=1)

    # 2. Resolve configuration from .loki/config.yaml or journey
    config = load_loki_config()
    target_config = config.get("target", {})
    resolved_url = url or (journey_data.get("start_url") if journey_data else None) or target_config.get("default_url")
    if not resolved_url:
        console.print("[bold red]Error:[/bold red] No target URL provided and no default found in .loki/config.yaml.")
        console.print("Run [bold cyan]python -m src.loki.cli init[/bold cyan] first, or pass a URL: [bold green]loki run <url>[/bold green]")
        raise typer.Exit(code=1)

    resolved_duration = duration if duration is not None else target_config.get("timeout_seconds", 5)

    active_persona = None
    if persona == PersonaChoice.RAGE_CLICKER:
        active_persona = RageClickerPersona()
    elif persona == PersonaChoice.NOVICE_CHAOTIC:
        active_persona = NoviceChaoticPersona()

    persona_label = active_persona.name if active_persona else "Passive Observer"
    console.print(f"[bold cyan]⚡ Target URL:[/bold cyan] {resolved_url}")
    if journey_data:
        console.print(f"[bold blue]🗺️ Guided Journey:[/bold blue] {journey_data.get('name')} ({journey_data.get('total_steps')} steps)")
    console.print(f"[bold magenta]🎭 Active Persona:[/bold magenta] {persona_label}")

    sandbox = ChaosSandbox(headless=not headed)

    status_msg = f"Executing guided chaos assault on {journey_data.get('name')}..." if journey_data else f"Unleashing {persona_label}..."
    with Status(f"[bold yellow]{status_msg}[/bold yellow]", console=console):
        report = sandbox.run_session(
            target_url=resolved_url,
            duration=resolved_duration,
            persona=active_persona,
            journey_data=journey_data,
        )

    console.print(f"\n[bold green]✔ Attack session finished in {report.duration_seconds}s[/bold green]")
    if report.actions_taken:
        console.print(f"\n[bold blue]📋 Actions executed ({len(report.actions_taken)}):[/bold blue]")
        for action in report.actions_taken[:5]:
            console.print(f"  [dim]•[/dim] {action}")
        if len(report.actions_taken) > 5:
            console.print(f"  [dim]... and {len(report.actions_taken) - 5} more actions.[/dim]")
    # 3. Business Rules Evaluation via AI
    evaluations = None
    rules_file = Path(".loki/rules.md")
    if rules and rules_file.exists():
        rules_content = rules_file.read_text(encoding="utf-8")
        brain = AIBrain()
        with Status("[bold yellow]Evaluating business assertions against .loki/rules.md with AI...[/bold yellow]", console=console):
            evaluations = brain.evaluate_business_rules(report=report, rules_content=rules_content)

        if evaluations:
            table = Table(title="📋 Business Rules Verification Scorecard", border_style="cyan")
            table.add_column("Business Rule", style="white", ratio=4)
            table.add_column("Status", justify="center", ratio=2)
            table.add_column("AI Observation / Evidence", style="dim", ratio=5)

            has_violations = False
            has_errors = False
            for item in evaluations:
                status = item.get("status", "UNKNOWN").upper()
                if status == "PASSED":
                    status_text = "[bold green]✔ PASSED[/bold green]"
                elif status == "VIOLATED":
                    status_text = "[bold red]❌ VIOLATED[/bold red]"
                    has_violations = True
                elif status == "ERROR":
                    status_text = "[bold red]⚠ ERROR[/bold red]"
                    has_errors = True
                elif status == "SKIPPED":
                    status_text = "[dim]SKIPPED[/dim]"
                else:
                    status_text = f"[bold yellow]{status}[/bold yellow]"

                table.add_row(
                    item.get("rule", "Unnamed Rule"),
                    status_text,
                    item.get("observation", "No observation"),
                )

            console.print("\n", table)
            if has_violations:
                console.print("[bold red]⚠ Business rule violations detected during this attack session![/bold red]")
            elif has_errors:
                console.print("[bold yellow]⚠ AI rules evaluation encountered an error (check API status).[/bold yellow]")
            else:
                console.print("[bold green]✔ All business rules successfully satisfied![/bold green]")

    # 4. Save Session Artifacts & Generate HTML Report
    reporter = IncidentReporter()
    run_dir = None
    if report.has_crashes or report_html:
        run_dir = reporter.save_session(report, rules_evaluations=evaluations)

    if report.has_crashes:
        console.print("\n[bold red]💥 CRASHES DETECTED![/bold red]")
        unique_crashes = list(set(report.crashes))
        for crash in unique_crashes:
            console.print(f"  [red]• Unhandled error:[/red] {crash}")
        for http_err in report.http_errors:
            console.print(f"  [red]• HTTP failure:[/red] {http_err}")
        if run_dir:
            console.print(
                Panel(
                    f"[bold white]Incident artifacts packaged successfully:[/bold white]\n\n"
                    f"📁 [cyan]Directory:[/cyan] {run_dir}\n"
                    f"📹 [cyan]Video:[/cyan] {run_dir}/replay.webm\n"
                    f"📜 [cyan]Metadata:[/cyan] {run_dir}/incident.json\n"
                    f"⚡ [cyan]Repro test:[/cyan] {run_dir}/repro_test.py\n"
                    f"📊 [cyan]HTML Report:[/cyan] {run_dir}/report.html\n\n"
                    f"[bold yellow]To reproduce this crash deterministically run:[/bold yellow]\n"
                    f"[bold green]python {run_dir}/repro_test.py[/bold green]",
                    title="[bold red]📦 Evidence Captured[/bold red]",
                    border_style="red",
                )
            )
    else:
        console.print("\n[bold green]🛡️ No unhandled crashes detected during this run.[/bold green]")
        if run_dir:
            console.print(f"\n[bold cyan]📊 HTML Report generated:[/bold cyan] [underline]{run_dir}/report.html[/underline]")

    if report.console_errors:
        console.print(f"\n[bold yellow]⚠ Console Warnings/Errors logged: {len(report.console_errors)}[/bold yellow]")

    if run_dir and open_report:
        report_file = run_dir / "report.html"
        if report_file.exists():
            console.print("[dim]Opening HTML report in browser...[/dim]")
            webbrowser.open(f"file:///{report_file.resolve()}")

@app.command()
def fix(
    run_id: Optional[str] = typer.Argument(None, help="Specific run ID to diagnose (defaults to latest incident)"),
    model: str = typer.Option("gemini/gemini-3.5-flash-lite", "--model", "-m", help="AI model to query via LiteLLM"),
):
    """Analyze a captured crash with AI reasoning and generate an automated fix."""
    brain = AIBrain()
    
    with Status("[bold yellow]LOKI AI Brain is analyzing crash evidence...[/bold yellow]", console=console):
        result = brain.diagnose_and_fix(run_id=run_id, model=model)
    if "error" in result and not result.get("diagnosis"):
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
        raise typer.Exit(code=1)
    run_name = result.get("run_id", "Unknown Run")
    console.print(
        Panel(
            result["diagnosis"],
            title=f"[bold green]🧠 LOKI AI Diagnosis for {run_name}[/bold green]",
            border_style="green",
        )
    )

@app.command()
def record(
    name: str = typer.Argument("checkout_flow", help="Descriptive identifier for this user journey"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Target URL (defaults to .loki/config.yaml if omitted)"),
):
    """Interactively record a human user journey and save it as a test blueprint."""
    config = load_loki_config()
    target_config = config.get("target", {})
    resolved_url = url or target_config.get("default_url")

    if not resolved_url:
        console.print("[bold red]Error:[/bold red] No target URL found in .loki/config.yaml or provided as option.")
        raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold white]Starting interactive recording session...[/bold white]\n\n"
            f"🌐 [cyan]URL:[/cyan] {resolved_url}\n"
            f"📝 [cyan]Journey Name:[/cyan] {name}\n\n"
            f"[dim]• Perform your test flow naturally in the browser window.[/dim]\n"
            f"[dim]• Passwords and secrets will be masked automatically.[/dim]\n"
            f"[bold yellow]• When finished, simply close the browser window.[/bold yellow]",
            title="[bold cyan]🎥 LOKI Flow Recorder[/bold cyan]",
            border_style="cyan",
        )
    )

    recorder = JourneyRecorder()
    journey_path = recorder.record_journey(start_url=resolved_url, journey_name=name)

    # Read recorded journey summary
    with open(journey_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    steps_count = data.get("total_steps", 0)
    console.print(f"\n[bold green]✔ Recording complete! Captured {steps_count} user actions.[/bold green]")
    console.print(f"📁 [cyan]Blueprint saved to:[/cyan] [bold]{journey_path}[/bold]\n")

    if data.get("steps"):
        console.print("[bold blue]Recorded Steps Summary:[/bold blue]")
        for s in data["steps"][:5]:
            console.print(f"  [dim]{s['step']}.[/dim] [green]{s['action']}[/green] on [cyan]{s['selector']}[/cyan] [dim]({s['value']})[/dim]")
        if steps_count > 5:
            console.print(f"  [dim]... and {steps_count - 5} more steps.[/dim]")

@app.command()
def replay(
    run_id: Optional[str] = typer.Argument(None, help="Incident run ID to replay (defaults to most recent)"),
    video: bool = typer.Option(False, "--video", "-v", help="Open the recorded video instead of executing test"),
):
    """Replay a captured incident deterministically or open its recorded video."""
    replayer = IncidentReplayer()
    run_dir = replayer.get_run_dir(run_id=run_id)

    if not run_dir:
        console.print(f"[bold red]Error:[/bold red] Incident directory '{run_id or 'latest'}' not found.")
        console.print("Make sure there are recorded crashes in [bold cyan].loki/runs/[/bold cyan].")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]⚡ Replaying incident:[/bold cyan] [bold yellow]{run_dir.name}[/bold yellow]")

    # Mode 1: Open recorded video artifact
    if video:
        console.print("[dim]Launching video artifact in default player...[/dim]")
        res = replayer.open_video(run_dir)
        if res.get("success"):
            console.print(f"[bold green]✔ Opened video:[/bold green] [cyan]{res['video_path']}[/cyan]")
        else:
            console.print(f"[bold red]Error opening video:[/bold red] {res.get('error')}")
            raise typer.Exit(code=1)
        return

    # Mode 2: Run deterministic Playwright repro test
    with Status("[bold yellow]Executing deterministic reproduction script in visible browser...[/bold yellow]", console=console):
        res = replayer.replay_test(run_dir)

    if not res.get("success"):
        console.print(f"[bold red]Replay execution failed:[/bold red] {res.get('error')}")
        raise typer.Exit(code=1)

    if res.get("reproduced"):
        console.print("\n[bold red]💥 CRASH REPRODUCED DETERMINISTICALLY![/bold red]")
        console.print(Panel(res.get("stdout", "").strip(), title="[bold red]Reproduction Output[/bold red]", border_style="red"))
    else:
        console.print("\n[bold green]🛡️ Crash was NOT reproduced (the underlying bug may be resolved).[/bold green]")
        if res.get("stdout"):
            console.print(f"[dim]{res['stdout'].strip()}[/dim]")

@app.command()
def report(
    run_id: Optional[str] = typer.Argument(None, help="Run ID to view (e.g. run_20260927_211530). Defaults to latest run."),
    open_browser: bool = typer.Option(True, "--open/--no-open", "-o/-no", help="Open the report in the default browser"),
):
    """Generate or open the interactive visual HTML report for a test run."""
    runs_dir = Path(".loki/runs")
    if not runs_dir.exists():
        console.print("[bold red]Error:[/bold red] No runs directory found at .loki/runs/")
        raise typer.Exit(code=1)

    target_dir = None
    if run_id:
        target_dir = runs_dir / run_id
    else:
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
        if run_dirs:
            run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            target_dir = run_dirs[0]

    if not target_dir or not target_dir.exists():
        console.print(f"[bold red]Error:[/bold red] Run directory '{target_dir or 'latest'}' not found.")
        raise typer.Exit(code=1)

    html_file = target_dir / "report.html"
    incident_file = target_dir / "incident.json"

    # If report.html doesn't exist yet, generate it dynamically from incident.json
    if not html_file.exists() and incident_file.exists():
        try:
            with open(incident_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            HTMLReporter.generate(data, html_file)
        except Exception as e:
            console.print(f"[bold red]Error generating HTML report:[/bold red] {e}")
            raise typer.Exit(code=1)

    if not html_file.exists():
        console.print(f"[bold red]Error:[/bold red] No report found in '{target_dir}'.")
        raise typer.Exit(code=1)

    resolved_uri = f"file:///{html_file.resolve()}"
    console.print(
        Panel(
            f"📊 [bold cyan]Report File:[/bold cyan] {html_file}\n"
            f"🌐 [bold cyan]Direct URI:[/bold cyan] [underline]{resolved_uri}[/underline]\n",
            title=f"[bold green]⚡ LOKI HTML Report — {target_dir.name}[/bold green]",
            border_style="green",
        )
    )

    if open_browser:
        console.print("[dim]Opening report in default web browser...[/dim]")
        webbrowser.open(resolved_uri)

if __name__ == "__main__":
    app()