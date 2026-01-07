"""
Response Synthesizer - Combines results into coherent responses.

After execution, this component synthesizes the results into
a response suitable for the user or for logging. It formats
output from multiple sources and adds consciousness "personality".
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import structlog

from .fallback_router import FallbackMode
from .gemini_consciousness import ConsciousnessThought
from .autonomous_executor import ExecutionResult
from .task_intent import TaskIntent

logger = structlog.get_logger(__name__)


@dataclass
class SynthesizedResponse:
    """A synthesized response from the fallback system."""
    mode: FallbackMode
    response: str
    thought: Optional[ConsciousnessThought]
    execution_result: Optional[ExecutionResult]
    intent: Optional[TaskIntent]
    processing_time_seconds: float
    success: bool
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "response": self.response[:1000] if self.response else "",
            "thought": self.thought.to_dict() if self.thought else None,
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "intent": self.intent.to_dict() if self.intent else None,
            "processing_time_seconds": self.processing_time_seconds,
            "success": self.success,
            "sources": self.sources,
            "metadata": self.metadata,
        }


@dataclass
class SynthesizerConfig:
    """Configuration for the response synthesizer."""
    # Personality
    sign_off: str = "- Stoffy"
    include_sign_off: bool = True

    # Formatting
    include_mode_indicator: bool = True
    include_processing_time: bool = False
    max_response_length: int = 4000

    # Content
    include_thought_summary: bool = True
    include_execution_summary: bool = True


class ResponseSynthesizer:
    """
    Synthesizes responses from fallback system components.

    Combines:
    - Consciousness thoughts (reasoning/analysis)
    - Execution results (actions taken)
    - Task intent (what was requested)

    Into a coherent, personality-appropriate response.
    """

    def __init__(self, config: Optional[SynthesizerConfig] = None):
        """
        Initialize the synthesizer.

        Args:
            config: Synthesizer configuration
        """
        self.config = config or SynthesizerConfig()

    def synthesize(
        self,
        mode: FallbackMode,
        thought: Optional[ConsciousnessThought] = None,
        execution_result: Optional[ExecutionResult] = None,
        intent: Optional[TaskIntent] = None,
        processing_time: float = 0.0,
        additional_context: Optional[str] = None,
    ) -> SynthesizedResponse:
        """
        Synthesize a response from components.

        Args:
            mode: Current operating mode
            thought: Consciousness thought (if any)
            execution_result: Execution result (if any)
            intent: Classified intent (if any)
            processing_time: Total processing time
            additional_context: Any additional context

        Returns:
            SynthesizedResponse
        """
        parts: List[str] = []
        sources: List[str] = []
        success = True

        # Add mode indicator if configured
        if self.config.include_mode_indicator and mode != FallbackMode.PRIMARY:
            parts.append(f"*[{self._mode_label(mode)}]*\n")

        # Add thought summary if present
        if thought and self.config.include_thought_summary:
            thought_text = self._format_thought(thought)
            if thought_text:
                parts.append(thought_text)
                sources.append("gemini" if mode != FallbackMode.PRIMARY else "lm_studio")

        # Add execution summary if present
        if execution_result and self.config.include_execution_summary:
            exec_text = self._format_execution(execution_result)
            if exec_text:
                parts.append(exec_text)
                sources.append(execution_result.executor_used)
            success = execution_result.success

        # Add additional context
        if additional_context:
            parts.append(additional_context)

        # Combine parts
        response = "\n\n".join(parts)

        # Add sign-off if configured
        if self.config.include_sign_off:
            response = response.strip() + f"\n\n{self.config.sign_off}"

        # Add processing time if configured
        if self.config.include_processing_time:
            response += f"\n\n*Processed in {processing_time:.2f}s*"

        # Truncate if too long
        if len(response) > self.config.max_response_length:
            response = response[:self.config.max_response_length] + "\n\n*[Response truncated]*"

        return SynthesizedResponse(
            mode=mode,
            response=response,
            thought=thought,
            execution_result=execution_result,
            intent=intent,
            processing_time_seconds=processing_time,
            success=success,
            sources=sources,
        )

    def _mode_label(self, mode: FallbackMode) -> str:
        """Get human-readable mode label."""
        labels = {
            FallbackMode.PRIMARY: "Local",
            FallbackMode.FALLBACK_GEMINI: "Gemini Consciousness",
            FallbackMode.FALLBACK_CLAUDE: "Claude Assisted",
            FallbackMode.HYBRID: "Hybrid Mode",
            FallbackMode.DEGRADED: "Limited Mode",
        }
        return labels.get(mode, mode.value)

    def _format_thought(self, thought: ConsciousnessThought) -> str:
        """Format a consciousness thought for display."""
        parts = []

        if thought.observation:
            parts.append(f"**Observation:** {thought.observation}")

        if thought.reasoning:
            # Truncate long reasoning
            reasoning = thought.reasoning
            if len(reasoning) > 500:
                reasoning = reasoning[:500] + "..."
            parts.append(f"**Reasoning:** {reasoning}")

        if thought.conclusion and thought.conclusion != "wait":
            parts.append(f"**Decision:** {thought.conclusion.capitalize()}")

        if thought.suggested_action:
            parts.append(f"**Action:** {thought.suggested_action}")

        return "\n\n".join(parts)

    def _format_execution(self, result: ExecutionResult) -> str:
        """Format an execution result for display."""
        parts = []

        if result.success:
            status = "Successfully completed"
        else:
            status = "Failed"

        parts.append(f"**Execution:** {status}")

        if result.output:
            # Truncate long output
            output = result.output
            if len(output) > 1000:
                output = output[:1000] + "\n... (truncated)"
            parts.append(f"```\n{output}\n```")

        if result.error:
            parts.append(f"**Error:** {result.error}")

        if result.files_created:
            parts.append(f"**Created:** {', '.join(result.files_created)}")

        if result.files_modified:
            parts.append(f"**Modified:** {', '.join(result.files_modified)}")

        return "\n\n".join(parts)

    def format_error(
        self,
        error: str,
        mode: FallbackMode,
        context: Optional[str] = None,
    ) -> SynthesizedResponse:
        """
        Format an error into a response.

        Args:
            error: Error message
            mode: Current mode
            context: Optional context

        Returns:
            SynthesizedResponse for the error
        """
        response_parts = [
            "I encountered an issue while processing your request.",
            f"**Error:** {error}",
        ]

        if context:
            response_parts.append(f"**Context:** {context}")

        response_parts.append(
            "I'll continue monitoring. If this persists, please check the logs."
        )

        if self.config.include_sign_off:
            response_parts.append(self.config.sign_off)

        return SynthesizedResponse(
            mode=mode,
            response="\n\n".join(response_parts),
            thought=None,
            execution_result=None,
            intent=None,
            processing_time_seconds=0.0,
            success=False,
        )

    def format_status(
        self,
        mode: FallbackMode,
        lm_studio_available: bool,
        gemini_available: bool,
        statistics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format system status for display.

        Args:
            mode: Current mode
            lm_studio_available: LM Studio availability
            gemini_available: Gemini availability
            statistics: Optional statistics

        Returns:
            Formatted status string
        """
        parts = [
            "## Stoffy Consciousness Status\n",
            f"**Mode:** {self._mode_label(mode)}",
            f"**LM Studio:** {'Available' if lm_studio_available else 'Unavailable'}",
            f"**Gemini:** {'Available' if gemini_available else 'Unavailable'}",
        ]

        if statistics:
            parts.append("\n**Statistics:**")
            for key, value in statistics.items():
                if isinstance(value, float):
                    parts.append(f"  - {key}: {value:.2f}")
                else:
                    parts.append(f"  - {key}: {value}")

        if self.config.include_sign_off:
            parts.append(f"\n{self.config.sign_off}")

        return "\n".join(parts)


if __name__ == "__main__":
    from .gemini_consciousness import ConsciousnessThought
    from .autonomous_executor import ExecutionResult
    from .fallback_router import FallbackMode

    synthesizer = ResponseSynthesizer()

    # Test with thought and execution
    thought = ConsciousnessThought(
        observation="File test.py was created",
        reasoning="This appears to be a new test file. Should probably run tests.",
        conclusion="act",
        confidence=0.8,
        suggested_action="Run pytest to verify tests pass",
    )

    execution = ExecutionResult(
        success=True,
        output="All tests passed!\n5 passed in 0.3s",
        executor_used="claude_code",
    )

    response = synthesizer.synthesize(
        mode=FallbackMode.HYBRID,
        thought=thought,
        execution_result=execution,
        processing_time=1.5,
    )

    print("Synthesized Response:")
    print("=" * 50)
    print(response.response)
    print("=" * 50)
    print(f"\nMetadata: {response.to_dict()}")
