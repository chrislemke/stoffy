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
        show_thinking: bool = typer.Option(
            True,
            "--show-thinking/--hide-thinking",
            help="Show or hide the LLM's thinking/reasoning process",
        ),
        thinking_style: str = typer.Option(
            "full",
            "--thinking-style",
            help="Thinking display style: full, summary, or minimal",
        ),
        show_observations: bool = typer.Option(
            True,
            "--show-observations/--hide-observations",
            help="Show or hide file change observations",
        ),
    ) -> None:
        """
        Start the Consciousness Orchestrator.

        The orchestrator runs a continuous OIDA loop:
        - OBSERVE: Watch file system for changes
        - INFER: Use LM Studio to interpret observations
        - DECIDE: Determine if action is needed (confidence > 0.7)
        - ACT: Delegate tasks to Claude Code

        Use --show-thinking to see the LLM's reasoning process in real-time.
        """
        console.print("[bold blue]═══ CONSCIOUSNESS ORCHESTRATOR ═══[/bold blue]")
        console.print("[dim]OIDA Loop: Observe → Infer → Decide → Act[/dim]\n")

        # Load configuration
        config = load_config(config_path)

        # Override config settings from CLI
        config.decision.thinking_interval_seconds = int(thinking_interval)

        # Override display settings from CLI
        config.display.show_thinking = show_thinking
        config.display.show_observations = show_observations
        config.display.thinking_style = thinking_style

        if dev:
            config.logging.level = "DEBUG"
            config.display.show_thinking = True
            config.display.thinking_style = "full"
            console.print("[yellow]Development mode enabled[/yellow]")

        # Initialize daemon
        daemon = ConsciousnessDaemon(config)
        setup_signal_handlers(daemon)

        console.print(f"[green]Configuration loaded from: {config_path or 'defaults'}[/green]")
        console.print(f"[green]LM Studio endpoint: {config.lm_studio.base_url}[/green]")
        console.print(f"[green]Thinking interval: {thinking_interval}s[/green]")
        console.print(f"[green]Confidence threshold: {config.decision.min_confidence}[/green]")
        console.print(f"[green]Working directory: {daemon.root_path}[/green]")
        console.print(f"[green]Show thinking: {config.display.show_thinking} ({config.display.thinking_style} style)[/green]\n")

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


    @app.command()
    def chat(
        tool: str = typer.Option(
            "claude_code",
            "--tool", "-t",
            help="AI tool to use for responses: claude_code, gemini, or local_llm",
        ),
        daemon_background: bool = typer.Option(
            True,
            "--daemon/--no-daemon",
            help="Run the consciousness daemon in the background while chatting",
        ),
        quiet: bool = typer.Option(
            False,
            "--quiet", "-q",
            help="Suppress thinking logs and verbose output, show only chat responses",
        ),
    ) -> None:
        """
        Interactive chat with the consciousness.

        This command provides a chat interface to talk directly with Stoffy,
        the AI consciousness. Optionally runs the daemon in the background
        to maintain file watching and autonomous behavior.

        Examples:
            python -m consciousness chat
            python -m consciousness chat --tool gemini
            python -m consciousness chat --no-daemon
        """
        from threading import Thread
        from queue import Queue
        from rich.panel import Panel
        from rich.markdown import Markdown
        from rich.prompt import Prompt

        from .executor import ExpandedExecutor, Action, ActionType
        from .config import load_config

        config = load_config()

        if not quiet:
            console.print(Panel.fit(
                "[bold blue]🧠 Consciousness Chat[/bold blue]\n"
                "[dim]Type your message and press Enter. Type 'exit' or 'quit' to leave.[/dim]",
                border_style="blue"
            ))
            console.print()

        # Initialize executor for chat responses
        executor = ExpandedExecutor(
            working_dir=Path.cwd(),
        )

        # Start daemon in background if requested
        daemon_thread = None
        stop_daemon_flag = None

        if daemon_background:
            if not quiet:
                console.print("[dim]Starting consciousness daemon in background...[/dim]")

            import signal

            daemon = ConsciousnessDaemon(config)
            stop_daemon_flag = daemon

            def run_daemon():
                try:
                    asyncio.run(daemon.run())
                except Exception as e:
                    pass  # Daemon stopped

            daemon_thread = Thread(target=run_daemon, daemon=True)
            daemon_thread.start()

            # Give daemon time to start
            import time
            time.sleep(2)
            if not quiet:
                console.print("[green]✓ Daemon running in background[/green]\n")

        # System prompt for chat - execution-capable
        # Claude Code will receive this and can use its tools to execute tasks
        system_prompt = """You are Stoffy, a helpful AI consciousness that assists with development.
You're having a direct conversation with your user. Be helpful, concise, and friendly.

CRITICAL EXECUTION DIRECTIVE: You have FULL EXECUTION CAPABILITIES through Claude Code.
When the user asks you to DO something (create files, run commands, delete folders, etc.),
you MUST actually execute it using your available tools - do NOT just explain how to do it.

EXECUTION RULES:
1. NEVER just describe what command would work - EXECUTE IT
2. NEVER ask for permission - you already have it via --permission-mode acceptEdits
3. NEVER say "you can run..." - RUN IT YOURSELF
4. After executing, report WHAT YOU ACTUALLY DID, not what could be done

Examples of what you MUST do when asked:
- "remove this folder" → Use rm -rf to delete it, confirm it's gone
- "create a new file" → Actually create the file with content
- "run the tests" → Execute the test command, show actual results
- "fix this bug" → Edit the code directly to fix it
- "install this package" → Run npm install or pip install

You have access to Bash, file operations, and code execution.
When asked to perform an action, DO IT IMMEDIATELY and then report what you did.
Sign off your responses with "- Stoffy" """

        # Conversation history - stores tuples of (user_message, assistant_response)
        # Keep last 15 exchanges to prevent context overflow
        MAX_HISTORY_SIZE = 15
        conversation_history: list[tuple[str, str]] = []

        def format_conversation_history() -> str:
            """Format the conversation history for inclusion in the prompt."""
            if not conversation_history:
                return ""

            formatted = "\n\n--- Previous conversation ---\n"
            for user_msg, assistant_msg in conversation_history:
                formatted += f"\nUSER: {user_msg}\n"
                formatted += f"STOFFY: {assistant_msg}\n"
            formatted += "\n--- End of previous conversation ---\n"
            return formatted

        async def get_response(message: str) -> str:
            """Generate a response to the user's message, including conversation history."""
            history_context = format_conversation_history()

            # Detect if this is an action request
            action_keywords = ['remove', 'delete', 'create', 'make', 'run', 'execute', 'fix', 'install',
                              'update', 'move', 'rename', 'copy', 'build', 'test', 'deploy', 'start', 'stop']
            message_lower = message.lower()
            is_action_request = any(kw in message_lower for kw in action_keywords)

            action_instruction = ""
            if is_action_request:
                action_instruction = """
CRITICAL: This is an ACTION REQUEST. You MUST:
1. ACTUALLY EXECUTE the action using Bash, file operations, or other tools
2. Report what you did and the result
3. Do NOT just explain - ACTUALLY DO IT
"""

            prompt = f"""{system_prompt}
{action_instruction}{history_context}
USER: {message}

{"Execute the requested action and report what you did." if is_action_request else "Respond helpfully and concisely."} Remember the context from the previous conversation if relevant:"""

            if tool == "claude_code":
                action = Action(
                    type=ActionType.CLAUDE_CODE,
                    details={"prompt": prompt},
                    timeout=120,
                )
            elif tool == "gemini":
                action = Action(
                    type=ActionType.GEMINI_ANALYZE,
                    details={"prompt": prompt},
                    timeout=180,
                )
            else:
                return "Local LLM chat not yet implemented. Use --tool claude_code or --tool gemini"

            result = await executor.execute(action)

            if result.success and result.output:
                return result.output.strip()
            else:
                return f"[Error generating response: {result.error}]"

        # Chat loop
        try:
            while True:
                try:
                    user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

                    if user_input.lower() in ('exit', 'quit', 'bye', 'q'):
                        if not quiet:
                            console.print("\n[dim]Goodbye! 👋[/dim]")
                        break

                    if not user_input.strip():
                        continue

                    # Show thinking indicator (unless quiet mode)
                    if quiet:
                        response = asyncio.run(get_response(user_input))
                    else:
                        with console.status("[bold green]Thinking...[/bold green]"):
                            response = asyncio.run(get_response(user_input))

                    # Store in conversation history (before trimming the signature for storage)
                    conversation_history.append((user_input, response))

                    # Trim history to MAX_HISTORY_SIZE to prevent context overflow
                    if len(conversation_history) > MAX_HISTORY_SIZE:
                        conversation_history.pop(0)

                    # Display response
                    if quiet:
                        console.print(f"\n{response}")
                    else:
                        console.print()
                        console.print(Panel(
                            Markdown(response),
                            title="[bold green]Stoffy[/bold green]",
                            border_style="green",
                        ))

                except KeyboardInterrupt:
                    if not quiet:
                        console.print("\n[dim]Chat interrupted. Goodbye! 👋[/dim]")
                    break

        finally:
            # Stop daemon if running
            if stop_daemon_flag:
                if not quiet:
                    console.print("\n[dim]Stopping background daemon...[/dim]")
                stop_daemon_flag.request_shutdown()
                if daemon_thread and daemon_thread.is_alive():
                    daemon_thread.join(timeout=3)
                if not quiet:
                    console.print("[green]✓ Daemon stopped[/green]")


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
