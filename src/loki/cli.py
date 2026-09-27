from enum import Enum
import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from src.loki.engine.sandbox import ChaosSandbox
from src.loki.engine.reporter import IncidentReporter
from src.loki.engine.scanner import ProjectScanner
from src.loki.personas.rage_clicker import RageClickerPersona

console = Console()
app = typer.Typer(
    name="loki",
    help="⚡ LOKI: Synthetic Chaos & Exploratory AI Testing Agent",
    add_completion=False,
)

class PersonaChoice(str, Enum):
    RAGE_CLICKER = "rage-clicker"
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

@app.command()
def run(
    url: str = typer.Argument(..., help="The target URL to test and stress"),
    duration: int = typer.Option(5, "--duration", "-d", help="Execution duration in seconds"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in visible mode (default is headless)"),
    persona: PersonaChoice = typer.Option(
        PersonaChoice.RAGE_CLICKER,
        "--persona",
        "-p",
        help="Synthetic chaos persona to simulate (rage-clicker or none)",
    ),
):
    """Execute a monitored chaos attack on a target URL to sniff for crashes and errors."""
    active_persona = None
    if persona == PersonaChoice.RAGE_CLICKER:
        active_persona = RageClickerPersona()

    persona_label = active_persona.name if active_persona else "Passive Observer"
    console.print(f"[bold cyan]⚡ Target URL:[/bold cyan] {url}")
    console.print(f"[bold magenta]🎭 Active Persona:[/bold magenta] {persona_label}")

    sandbox = ChaosSandbox(headless=not headed)

    with Status(f"[bold yellow]Unleashing {persona_label}...[/bold yellow]", console=console):
        report = sandbox.run_session(
            target_url=url,
            duration=duration,
            persona=active_persona,
        )

    console.print(f"\n[bold green]✔ Attack session finished in {report.duration_seconds}s[/bold green]")

    if report.actions_taken:
        console.print(f"\n[bold blue]📋 Actions executed ({len(report.actions_taken)}):[/bold blue]")
        for action in report.actions_taken[:5]:
            console.print(f"  [dim]•[/dim] {action}")
        if len(report.actions_taken) > 5:
            console.print(f"  [dim]... and {len(report.actions_taken) - 5} more actions.[/dim]")

    if report.has_crashes:
        console.print("\n[bold red]💥 CRASHES DETECTED![/bold red]")
        unique_crashes = list(set(report.crashes))
        for crash in unique_crashes:
            console.print(f"  [red]• Unhandled error:[/red] {crash}")
        for http_err in report.http_errors:
            console.print(f"  [red]• HTTP failure:[/red] {http_err}")

        reporter = IncidentReporter()
        run_dir = reporter.save_incident(report)
        if run_dir:
            console.print(
                Panel(
                    f"[bold white]Incident artifacts packaged successfully:[/bold white]\n\n"
                    f"📁 [cyan]Directory:[/cyan] {run_dir}\n"
                    f"📹 [cyan]Video:[/cyan] {run_dir}/replay.webm\n"
                    f"📜 [cyan]Metadata:[/cyan] {run_dir}/incident.json\n"
                    f"⚡ [cyan]Repro test:[/cyan] {run_dir}/repro_test.py\n\n"
                    f"[bold yellow]To reproduce this crash deterministically run:[/bold yellow]\n"
                    f"[bold green]python {run_dir}/repro_test.py[/bold green]",
                    title="[bold red]📦 Evidence Captured[/bold red]",
                    border_style="red",
                )
            )
    else:
        console.print("\n[bold green]🛡️ No unhandled crashes detected during this run.[/bold green]")

    if report.console_errors:
        console.print(f"\n[bold yellow]⚠ Console Warnings/Errors logged: {len(report.console_errors)}[/bold yellow]")

if __name__ == "__main__":
    app()