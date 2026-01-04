"""
Consciousness Orchestrator Entry Point

Run with: python -m consciousness [OPTIONS]

OIDA Loop: Observe → Infer → Decide → Act → (repeat)
"""

import asyncio
import signal
import sys
from pathlib import Path

import typer
from rich.console import Console

from .config import ConsciousnessConfig
from .orchestrator import ConsciousnessOrchestrator

app = typer.Typer(
    name="consciousness",
    help="Autonomous Consciousness Orchestrator - OIDA Loop Implementation",
)
console = Console()


def setup_signal_handlers(orchestrator: ConsciousnessOrchestrator) -> None:
    """Set up graceful shutdown handlers."""

    def signal_handler(sig: int, frame) -> None:
        console.print("\n[yellow]Received shutdown signal, gracefully stopping...[/yellow]")
        orchestrator.request_shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


@app.command()
def run(
    config_path: Path = typer.Option(
        None,
        "--config", "-c",
        help="Path to consciousness.yaml configuration file",
    ),
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Run in development mode with verbose logging",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run without executing actions (observation and decision only)",
    ),
    thinking_interval: float = typer.Option(
        5.0,
        "--interval", "-i",
        help="Seconds between thinking cycles",
    ),
) -> None:
    """
    Start the Consciousness Orchestrator.

    The orchestrator runs a continuous OIDA loop:
    - OBSERVE: Watch file system, processes, git status
    - INFER: Use LM Studio to interpret observations
    - DECIDE: Determine if action is needed (confidence > 0.7)
    - ACT: Delegate tasks to Claude API
    """
    console.print("[bold blue]═══ CONSCIOUSNESS ORCHESTRATOR ═══[/bold blue]")
    console.print("[dim]OIDA Loop: Observe → Infer → Decide → Act[/dim]\n")

    # Load configuration
    config = ConsciousnessConfig.load(config_path)

    if dev:
        config.logging.level = "DEBUG"
        console.print("[yellow]Development mode enabled[/yellow]")

    if dry_run:
        config.decision.dry_run = True
        console.print("[yellow]Dry-run mode: Actions will be logged but not executed[/yellow]")

    config.decision.thinking_interval_seconds = thinking_interval

    # Initialize orchestrator
    orchestrator = ConsciousnessOrchestrator(config)
    setup_signal_handlers(orchestrator)

    console.print(f"[green]Configuration loaded from: {config_path or 'defaults'}[/green]")
    console.print(f"[green]LM Studio endpoint: {config.lm_studio.base_url}[/green]")
    console.print(f"[green]Thinking interval: {thinking_interval}s[/green]")
    console.print(f"[green]Confidence threshold: {config.decision.min_confidence_to_act}[/green]\n")

    console.print("[bold green]Starting consciousness loop...[/bold green]\n")

    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutdown complete.[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


@app.command()
def status() -> None:
    """Check the status of a running consciousness daemon."""
    console.print("[dim]Checking consciousness status...[/dim]")
    # TODO: Check launchd status or PID file
    console.print("[yellow]Status check not yet implemented[/yellow]")


@app.command()
def observe() -> None:
    """Run a single observation cycle (debugging)."""
    console.print("[dim]Running single observation cycle...[/dim]")
    config = ConsciousnessConfig.load()
    orchestrator = ConsciousnessOrchestrator(config)

    async def single_observe():
        observations = await orchestrator._observe()
        console.print(observations)

    asyncio.run(single_observe())


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
