"""
Consciousness Orchestrator Entry Point

Run with: python -m consciousness [OPTIONS]

OIDA Loop: Observe -> Infer -> Decide -> Act -> (repeat)
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
    HAS_TYPER = True
except ImportError:
    HAS_TYPER = False

from .config import ConsciousnessConfig, load_config
from .daemon import ConsciousnessDaemon, setup_signal_handlers


if HAS_TYPER:
    app = typer.Typer(
        name="consciousness",
        help="Autonomous Consciousness Orchestrator - OIDA Loop Implementation",
    )
    console = Console()

    @app.command()
    def run(
        config_path: Optional[Path] = typer.Option(
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
        - OBSERVE: Watch file system for changes
        - INFER: Use LM Studio to interpret observations
        - DECIDE: Determine if action is needed (confidence > 0.7)
        - ACT: Delegate tasks to Claude Code
        """
        console.print("[bold blue]═══ CONSCIOUSNESS ORCHESTRATOR ═══[/bold blue]")
        console.print("[dim]OIDA Loop: Observe → Infer → Decide → Act[/dim]\n")

        # Load configuration
        config = load_config(config_path)

        # Override config settings from CLI
        config.decision.thinking_interval_seconds = int(thinking_interval)

        if dev:
            config.logging.level = "DEBUG"
            console.print("[yellow]Development mode enabled[/yellow]")

        # Initialize daemon
        daemon = ConsciousnessDaemon(config)
        setup_signal_handlers(daemon)

        console.print(f"[green]Configuration loaded from: {config_path or 'defaults'}[/green]")
        console.print(f"[green]LM Studio endpoint: {config.lm_studio.base_url}[/green]")
        console.print(f"[green]Thinking interval: {thinking_interval}s[/green]")
        console.print(f"[green]Confidence threshold: {config.decision.min_confidence}[/green]")
        console.print(f"[green]Working directory: {daemon.root_path}[/green]\n")

        console.print("[bold green]Starting consciousness loop...[/bold green]\n")

        try:
            asyncio.run(daemon.run())
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutdown complete.[/yellow]")
        except Exception as e:
            console.print(f"[red]Fatal error: {e}[/red]")
            sys.exit(1)


    @app.command()
    def status() -> None:
        """Check the status of a running consciousness daemon."""
        console.print("[dim]Checking consciousness status...[/dim]")

        config = load_config()
        db_path = Path(config.state.database_path)

        if db_path.exists():
            import sqlite3
            conn = sqlite3.connect(db_path)

            # Get counts
            cursor = conn.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM thoughts")
            thought_count = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM actions")
            action_count = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM actions WHERE success = 1")
            success_count = cursor.fetchone()[0]

            # Get last thought
            cursor = conn.execute(
                "SELECT timestamp, confidence, response FROM thoughts ORDER BY timestamp DESC LIMIT 1"
            )
            last_thought = cursor.fetchone()

            conn.close()

            console.print(f"[green]Database found: {db_path}[/green]")
            console.print(f"  Events logged: {event_count}")
            console.print(f"  Thoughts logged: {thought_count}")
            console.print(f"  Actions logged: {action_count}")
            console.print(f"  Successful actions: {success_count}")

            if last_thought:
                console.print(f"\n[bold]Last thought:[/bold]")
                console.print(f"  Timestamp: {last_thought[0]}")
                console.print(f"  Confidence: {last_thought[1]:.2f}")
                response_preview = last_thought[2][:200] if last_thought[2] else ""
                console.print(f"  Response: {response_preview}...")
        else:
            console.print("[yellow]No consciousness database found. Daemon may not have run yet.[/yellow]")


    @app.command()
    def observe() -> None:
        """Run a single observation cycle (debugging)."""
        console.print("[dim]Running single observation cycle...[/dim]")

        from .watcher import ConsciousnessWatcher

        config = load_config()
        root_path = Path(config.watcher.root_path).resolve()

        watcher = ConsciousnessWatcher(
            root_path=root_path,
            ignore_patterns=config.watcher.ignore_patterns,
            debounce_ms=config.watcher.debounce_ms,
        )

        async def single_observe():
            console.print(f"[dim]Watching: {root_path}[/dim]")
            console.print("[dim]Waiting for changes (5 seconds)...[/dim]")

            # Simple timeout-based watch
            import time
            start = time.time()

            async for changes in watcher.watch():
                if changes:
                    observations = watcher.format_for_llm(changes)
                    console.print("\n[bold]Observations:[/bold]")
                    console.print(observations)
                    break

                if time.time() - start > 5:
                    console.print("[yellow]No changes detected in 5 seconds.[/yellow]")
                    break

            watcher.stop()

        asyncio.run(single_observe())


    @app.command()
    def think(
        observation: str = typer.Argument(
            ...,
            help="Observation text to analyze",
        ),
    ) -> None:
        """Run a single thinking cycle on provided observation."""
        console.print("[dim]Thinking about observation...[/dim]\n")

        from .thinker import ConsciousnessThinker
        import json

        config = load_config()

        thinker = ConsciousnessThinker(
            base_url=config.lm_studio.base_url,
            model=config.lm_studio.model,
            temperature=config.lm_studio.temperature,
            max_tokens=config.lm_studio.max_tokens,
        )

        async def single_think():
            # Check connection
            connected = await thinker.check_connection()
            if not connected:
                console.print(f"[red]Cannot connect to LM Studio at {config.lm_studio.base_url}[/red]")
                console.print("[yellow]Make sure LM Studio is running with a model loaded.[/yellow]")
                return

            decision = await thinker.think(observation)

            console.print("[bold]Decision:[/bold]")
            console.print(f"  Type: {decision.decision.value}")
            console.print(f"  Confidence: {decision.confidence:.2f}")
            console.print(f"  Reasoning: {decision.reasoning}")

            if decision.action:
                console.print(f"\n[bold]Action:[/bold]")
                console.print(f"  Type: {decision.action.type.value}")
                console.print(f"  Prompt: {decision.action.prompt[:200]}...")
                console.print(f"  Priority: {decision.action.priority.value}")

            console.print(f"\n[dim]Raw response:[/dim]")
            try:
                formatted = json.dumps(json.loads(decision.raw_response), indent=2)
                console.print(formatted)
            except json.JSONDecodeError:
                console.print(decision.raw_response)

        asyncio.run(single_think())


    @app.command()
    def check() -> None:
        """Check if all required components are available."""
        console.print("[bold]Checking consciousness components...[/bold]\n")

        from .executor import ClaudeCodeExecutor

        config = load_config()

        # Check LM Studio
        console.print("[dim]Checking LM Studio connection...[/dim]")

        from .thinker import ConsciousnessThinker
        thinker = ConsciousnessThinker(base_url=config.lm_studio.base_url)

        async def check_lm_studio():
            return await thinker.check_connection()

        connected = asyncio.run(check_lm_studio())

        if connected:
            console.print(f"[green]✓ LM Studio: Connected ({config.lm_studio.base_url})[/green]")
        else:
            console.print(f"[red]✗ LM Studio: Not connected ({config.lm_studio.base_url})[/red]")

        # Check Claude CLI
        console.print("[dim]Checking Claude CLI...[/dim]")
        executor = ClaudeCodeExecutor(working_dir=Path.cwd())

        if executor.is_available():
            console.print("[green]✓ Claude CLI: Available[/green]")
        else:
            console.print("[red]✗ Claude CLI: Not found[/red]")

        # Check Claude Flow
        console.print("[dim]Checking Claude Flow...[/dim]")
        if executor.is_swarm_available():
            console.print("[green]✓ Claude Flow: Available[/green]")
        else:
            console.print("[yellow]~ Claude Flow: Not available (optional)[/yellow]")

        # Check database path
        console.print("[dim]Checking database...[/dim]")
        db_path = Path(config.state.database_path)
        if db_path.exists():
            console.print(f"[green]✓ Database: Exists ({db_path})[/green]")
        else:
            console.print(f"[yellow]~ Database: Will be created ({db_path})[/yellow]")


    def main() -> None:
        """Main entry point with typer."""
        app()


else:
    # Fallback when typer is not installed
    def main() -> None:
        """Simple entry point without typer."""
        import argparse

        parser = argparse.ArgumentParser(
            description="Consciousness Orchestrator - OIDA Loop Implementation",
        )
        parser.add_argument(
            "-c", "--config",
            type=Path,
            help="Path to consciousness.yaml configuration file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without executing actions",
        )
        parser.add_argument(
            "-i", "--interval",
            type=float,
            default=5.0,
            help="Seconds between thinking cycles",
        )

        args = parser.parse_args()

        print("═══ CONSCIOUSNESS ORCHESTRATOR ═══")
        print("OIDA Loop: Observe → Infer → Decide → Act\n")

        # Load configuration
        config = load_config(args.config)
        config.decision.thinking_interval_seconds = int(args.interval)

        # Initialize and run daemon
        daemon = ConsciousnessDaemon(config)
        setup_signal_handlers(daemon)

        print(f"LM Studio endpoint: {config.lm_studio.base_url}")
        print(f"Thinking interval: {args.interval}s")
        print(f"Confidence threshold: {config.decision.min_confidence}")
        print(f"Working directory: {daemon.root_path}\n")
        print("Starting consciousness loop...\n")

        try:
            asyncio.run(daemon.run())
        except KeyboardInterrupt:
            print("\nShutdown complete.")
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
