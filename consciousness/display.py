"""
Consciousness Display Module

Rich console output for displaying the consciousness's thinking process,
observations, decisions, and actions in the CLI.

This module provides beautiful, formatted output so users can see what
the consciousness is thinking in real-time.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import textwrap

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.progress import Progress, SpinnerColumn, TextColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

if TYPE_CHECKING:
    from .config import DisplayConfig
    from .decision.engine import EngineDecision
    from .thinker import Decision


@dataclass
class ThinkingDisplay:
    """
    Handles displaying the consciousness's thinking process in the CLI.

    Provides rich, formatted output showing:
    - Observations (what was detected)
    - Thinking/Reasoning (the LLM's thought process)
    - Decisions (what action to take)
    - Actions (execution results)
    """

    config: "DisplayConfig"
    console: Optional["Console"] = None

    def __post_init__(self):
        if HAS_RICH and self.console is None:
            self.console = Console(
                color_system="auto" if self.config.use_colors else None,
                width=self.config.panel_width,
            )

    def _print_fallback(self, title: str, content: str, style: str = "") -> None:
        """Fallback printing when Rich is not available."""
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print('=' * 60)
        print(content)
        print()

    def show_cycle_start(self, cycle_number: int) -> None:
        """Display the start of a new thinking cycle."""
        if not HAS_RICH or not self.console:
            print(f"\n--- Cycle {cycle_number} ---")
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.print()
        self.console.rule(
            f"[bold cyan]Cycle {cycle_number}[/bold cyan] [dim]@ {timestamp}[/dim]",
            style="cyan"
        )

    def show_observations(self, observations: str, change_count: int = 0) -> None:
        """Display what the consciousness observed."""
        if not self.config.show_observations:
            return

        if not HAS_RICH or not self.console:
            self._print_fallback("OBSERVATIONS", observations)
            return

        title = f"[bold blue]👁️  OBSERVATIONS[/bold blue]"
        if change_count > 0:
            title += f" [dim]({change_count} changes)[/dim]"

        # Truncate very long observations
        display_obs = observations
        if len(observations) > 2000 and self.config.thinking_style == "summary":
            display_obs = observations[:2000] + "\n... (truncated)"

        panel = Panel(
            Text(display_obs),
            title=title,
            border_style="blue",
            padding=(0, 1),
        )
        self.console.print(panel)

    def show_thinking(
        self,
        reasoning: str,
        observation_summary: str = "",
        expected_outcome: str = "",
        confidence: float = 0.0,
    ) -> None:
        """
        Display the consciousness's thinking/reasoning process.

        This is the main feature - showing what the LLM is thinking.
        """
        if not self.config.show_thinking:
            return

        if not HAS_RICH or not self.console:
            content = f"Summary: {observation_summary}\n\n"
            content += f"Reasoning:\n{reasoning}\n\n"
            content += f"Expected Outcome: {expected_outcome}\n"
            content += f"Confidence: {confidence:.1%}"
            self._print_fallback("THINKING", content)
            return

        # Build thinking content based on style
        if self.config.thinking_style == "minimal":
            # Just show a one-liner
            summary = reasoning.split('\n')[0] if reasoning else "No reasoning provided"
            self.console.print(
                f"[yellow]💭 Thinking:[/yellow] {summary[:100]}... "
                f"[dim](confidence: {confidence:.1%})[/dim]"
            )
            return

        # Full or summary style
        content_parts = []

        if observation_summary:
            content_parts.append(
                f"[bold]📝 Summary:[/bold]\n{observation_summary}"
            )

        if reasoning:
            # Format reasoning nicely
            if self.config.thinking_style == "summary" and len(reasoning) > 500:
                # Truncate for summary mode
                display_reasoning = reasoning[:500] + "..."
            else:
                display_reasoning = reasoning

            content_parts.append(
                f"\n[bold]🧠 Reasoning:[/bold]\n{display_reasoning}"
            )

        if expected_outcome:
            content_parts.append(
                f"\n[bold]🎯 Expected Outcome:[/bold]\n{expected_outcome}"
            )

        # Build confidence bar
        conf_bar = self._build_confidence_bar(confidence)
        content_parts.append(f"\n[bold]📊 Confidence:[/bold] {conf_bar}")

        content = "\n".join(content_parts)

        panel = Panel(
            Text.from_markup(content),
            title="[bold yellow]💭 THINKING[/bold yellow]",
            border_style="yellow",
            padding=(0, 1),
        )
        self.console.print(panel)

    def _build_confidence_bar(self, confidence: float) -> str:
        """Build a visual confidence bar."""
        filled = int(confidence * 10)
        empty = 10 - filled

        if confidence >= 0.8:
            color = "green"
        elif confidence >= 0.5:
            color = "yellow"
        else:
            color = "red"

        bar = f"[{color}]{'█' * filled}[/{color}][dim]{'░' * empty}[/dim]"
        return f"{bar} {confidence:.1%}"

    def show_decision(
        self,
        should_act: bool,
        action_type: str = "",
        action_description: str = "",
        priority: str = "medium",
    ) -> None:
        """Display the decision made by the consciousness."""
        if not self.config.show_decisions:
            return

        if not HAS_RICH or not self.console:
            status = "ACT" if should_act else "WAIT"
            self._print_fallback("DECISION", f"{status}: {action_description}")
            return

        if should_act:
            icon = "✅"
            color = "green"
            status = "ACT"
        else:
            icon = "⏸️"
            color = "dim"
            status = "WAIT"

        content_parts = [f"[bold]Status:[/bold] [{color}]{status}[/{color}]"]

        if action_type:
            content_parts.append(f"[bold]Action Type:[/bold] {action_type}")

        if action_description:
            # Wrap long descriptions
            wrapped = textwrap.fill(action_description, width=80)
            content_parts.append(f"[bold]Description:[/bold]\n{wrapped}")

        if priority:
            priority_colors = {
                "critical": "red bold",
                "high": "red",
                "medium": "yellow",
                "low": "dim",
            }
            p_color = priority_colors.get(priority.lower(), "white")
            content_parts.append(f"[bold]Priority:[/bold] [{p_color}]{priority}[/{p_color}]")

        content = "\n".join(content_parts)

        panel = Panel(
            Text.from_markup(content),
            title=f"[bold {color}]{icon} DECISION[/bold {color}]",
            border_style=color,
            padding=(0, 1),
        )
        self.console.print(panel)

    def show_action_start(self, action_type: str, description: str) -> None:
        """Display that an action is starting."""
        if not self.config.show_actions:
            return

        if not HAS_RICH or not self.console:
            print(f">>> Executing: {action_type} - {description}")
            return

        self.console.print(
            f"[bold magenta]⚡ EXECUTING:[/bold magenta] "
            f"[cyan]{action_type}[/cyan] - {description[:80]}..."
        )

    def show_action_result(
        self,
        success: bool,
        output: str = "",
        error: str = "",
        duration: float = 0.0,
    ) -> None:
        """Display the result of an action."""
        if not self.config.show_actions:
            return

        if not HAS_RICH or not self.console:
            status = "SUCCESS" if success else "FAILED"
            print(f"<<< {status} ({duration:.2f}s)")
            if output:
                print(f"Output: {output[:500]}")
            if error:
                print(f"Error: {error}")
            return

        if success:
            icon = "✓"
            color = "green"
            status = "SUCCESS"
        else:
            icon = "✗"
            color = "red"
            status = "FAILED"

        content_parts = [
            f"[bold]Status:[/bold] [{color}]{status}[/{color}]",
            f"[bold]Duration:[/bold] {duration:.2f}s",
        ]

        if output:
            # Truncate long output
            display_output = output[:1000] if len(output) > 1000 else output
            if len(output) > 1000:
                display_output += "\n... (truncated)"
            content_parts.append(f"[bold]Output:[/bold]\n[dim]{display_output}[/dim]")

        if error:
            content_parts.append(f"[bold red]Error:[/bold red]\n{error}")

        content = "\n".join(content_parts)

        panel = Panel(
            Text.from_markup(content),
            title=f"[bold {color}]{icon} RESULT[/bold {color}]",
            border_style=color,
            padding=(0, 1),
        )
        self.console.print(panel)

    def show_engine_decision(self, decision: "EngineDecision") -> None:
        """Display a full EngineDecision with all its details."""
        # Show thinking
        self.show_thinking(
            reasoning=decision.reasoning,
            observation_summary=decision.observation_summary,
            expected_outcome=decision.expected_outcome,
            confidence=decision.confidence,
        )

        # Show decision
        action_type = ""
        action_description = ""
        priority = "medium"

        if decision.action:
            action_type = decision.action.type.value
            action_description = decision.action.description
            priority = decision.action.priority.value

        self.show_decision(
            should_act=decision.should_act,
            action_type=action_type,
            action_description=action_description,
            priority=priority,
        )

    def show_status_line(
        self,
        cycle: int,
        decisions: int,
        actions: int,
        mode: str = "autonomous",
    ) -> None:
        """Show a compact status line."""
        if not HAS_RICH or not self.console:
            print(f"[Cycle {cycle}] Decisions: {decisions}, Actions: {actions}, Mode: {mode}")
            return

        self.console.print(
            f"[dim]│ Cycle: {cycle} │ Decisions: {decisions} │ "
            f"Actions: {actions} │ Mode: {mode} │[/dim]"
        )

    def show_error(self, error: str, context: str = "") -> None:
        """Display an error message."""
        if not HAS_RICH or not self.console:
            print(f"ERROR: {error}")
            if context:
                print(f"Context: {context}")
            return

        content = error
        if context:
            content += f"\n\n[dim]Context: {context}[/dim]"

        panel = Panel(
            Text.from_markup(content),
            title="[bold red]❌ ERROR[/bold red]",
            border_style="red",
            padding=(0, 1),
        )
        self.console.print(panel)

    def show_dream_cycle(self, status: str, insights: int = 0) -> None:
        """Display dream cycle status."""
        if not HAS_RICH or not self.console:
            print(f"💤 Dream Cycle: {status} (Insights: {insights})")
            return

        self.console.print(
            f"[bold blue]💤 DREAM CYCLE:[/bold blue] {status} "
            f"[dim](Insights: {insights})[/dim]"
        )


def create_display(config: "DisplayConfig") -> ThinkingDisplay:
    """Factory function to create a ThinkingDisplay instance."""
    return ThinkingDisplay(config=config)
