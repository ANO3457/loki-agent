import typer
from rich.console import Console
from rich.panel import Panel

# Initialize styled console and Typer application
console = Console()
app = typer.Typer(
    name="loki",
    help="LOKI: Synthetic Chaos & Exploratory AI Testing Agent",
    add_completion=False,
)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Main entry point for LOKI."""
    if ctx.invoked_subcommand is None:
        # If the user runs 'loki' with no subcommands, show the welcome banner
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
                "Run [bold cyan]python -m src.loki.cli --help[/bold cyan] to see avaiable commands.",
                title="[bold yellow] LOKI Agent v0.1.0[/bold yellow]",
                border_style="red",
            )
        )

@app.command()
def version():
    """Display the installed version of Loki."""
    console.print("[bold yellow]LOKI Agent[/bold yellow] version [bold green]0.1.0[/bold green]")

if __name__ == "__main__":
    app()