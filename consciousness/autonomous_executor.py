"""
Autonomous Executor - Claude Code Execution with Gemini Consciousness Guidance.

This module bridges Gemini's consciousness/reasoning capabilities with Claude Code's
execution capabilities. Gemini provides guidance on whether and how to act,
while Claude Code performs the actual execution.

Flow:
1. Receive user message
2. Gemini consciousness provides guidance (should_act, action_hint, confidence)
3. If should_act AND confidence > threshold: Claude Code executes the action
4. Gemini reflects on the result (optional learning)
5. Return combined response

This creates a "think then act" pattern where:
- Gemini is the "consciousness" - aware, reflective, guidance-oriented
- Claude Code is the "body" - skilled, action-oriented, execution-focused
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

from .executor import (
    ExpandedExecutor,
    ExecutionResult,
    ExecutionConfig,
    Action as ExecutorAction,
    ActionType as ExecutorActionType,
    Priority as ExecutorPriority,
    ExecutionMode,
)
from .gemini_consciousness import (
    GeminiConsciousness,
    ConsciousnessThought,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EXECUTION RESPONSE
# =============================================================================

@dataclass
class ExecutionResponse:
    """
    Complete response from the autonomous executor.

    Combines consciousness guidance with execution results.
    """
    mode: str  # "executed", "answered", "declined", "error"
    thought: ConsciousnessThought
    result: Optional[ExecutionResult]
    response: str  # Final human-readable response
    actions_taken: List[str] = field(default_factory=list)

    # Timing
    total_duration_ms: float = 0.0
    thinking_duration_ms: float = 0.0
    execution_duration_ms: float = 0.0

    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mode": self.mode,
            "thought": self.thought.to_dict(),
            "result": self.result.to_dict() if self.result else None,
            "response": self.response,
            "actions_taken": self.actions_taken,
            "total_duration_ms": self.total_duration_ms,
            "thinking_duration_ms": self.thinking_duration_ms,
            "execution_duration_ms": self.execution_duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# AUTONOMOUS EXECUTOR WITH CONSCIOUSNESS
# =============================================================================

class AutonomousExecutorWithConsciousness:
    """
    Executes tasks autonomously using Claude Code with Gemini consciousness guidance.

    This is the main integration point between:
    - Gemini consciousness (thinking, deciding)
    - Claude Code executor (acting, executing)

    Flow:
    1. Receive user message
    2. Gemini consciousness provides guidance (should_act, action_hint)
    3. If should_act AND confidence > threshold: Claude Code executes
    4. Gemini reflects on the result (optional learning)
    5. Return combined response
    """

    def __init__(
        self,
        working_dir: Path,
        gemini_consciousness: Optional[GeminiConsciousness] = None,
        executor: Optional[ExpandedExecutor] = None,
        auto_execute_threshold: float = 0.8,
        enable_reflection: bool = True,
    ):
        """
        Initialize the autonomous executor.

        Args:
            working_dir: Working directory for execution
            gemini_consciousness: Gemini consciousness for guidance
            executor: Claude Code executor for action
            auto_execute_threshold: Minimum confidence to auto-execute
            enable_reflection: Whether to reflect on results for learning
        """
        self.working_dir = Path(working_dir).resolve()
        self.consciousness = gemini_consciousness or GeminiConsciousness()
        self.executor = executor or ExpandedExecutor(self.working_dir)
        self.auto_execute_threshold = auto_execute_threshold
        self.enable_reflection = enable_reflection

        # Track actions for reporting
        self._action_history: List[Dict[str, Any]] = []

    async def process_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResponse:
        """
        Process a user message with full autonomous capability.

        Args:
            message: The user message to process
            context: Additional context (files, history, etc.)

        Returns:
            ExecutionResponse with thought, result, and response
        """
        start_time = time.time()

        # Step 1: Consciousness thinks about the message
        thought = await self.consciousness.contemplate(message, context)
        thinking_duration = (time.time() - start_time) * 1000

        # Step 2: Decide whether to execute based on thought
        execution_result = None
        actions_taken = []
        response_mode = "answered"  # Default mode

        # Determine mode based on thought
        if thought.should_act and thought.confidence >= self.auto_execute_threshold:
            # Execute with consciousness guidance
            exec_start = time.time()
            execution_result = await self.execute_with_consciousness(thought, message)
            execution_duration = (time.time() - exec_start) * 1000

            if execution_result.success:
                response_mode = "executed"
                actions_taken = execution_result.files_created + execution_result.files_modified
                if execution_result.action_type:
                    actions_taken.insert(0, f"[{execution_result.action_type.value}]")
            else:
                response_mode = "error"
        elif thought.should_act:
            # Confidence too low, ask for confirmation
            response_mode = "low_confidence"
            execution_duration = 0
        elif not thought.should_act:
            response_mode = "answered"
            execution_duration = 0
        else:
            execution_duration = 0

        # Step 3: Build response
        response = self._build_response(thought, execution_result, response_mode)

        # Step 4: Optional reflection for learning
        if self.enable_reflection and execution_result:
            action_desc = thought.action_hint or thought.suggested_approach
            result_desc = f"Success: {execution_result.success}. Output: {execution_result.output[:500] if execution_result.output else 'None'}"
            reflection = await self.consciousness.reflect_on_action(
                action_taken=action_desc,
                result=result_desc,
                context=context,
            )
            logger.debug("autonomous.reflection", reflection=reflection)

        # Build final response
        total_duration = (time.time() - start_time) * 1000

        return ExecutionResponse(
            mode=response_mode,
            thought=thought,
            result=execution_result,
            response=response,
            actions_taken=actions_taken,
            total_duration_ms=total_duration,
            thinking_duration_ms=thinking_duration,
            execution_duration_ms=execution_duration,
        )

    async def execute_with_consciousness(
        self,
        thought: ConsciousnessThought,
        message: str,
    ) -> ExecutionResult:
        """
        Execute an action guided by consciousness thought.

        Args:
            thought: The consciousness thought guiding execution
            message: The original user message

        Returns:
            ExecutionResult from Claude Code
        """
        # Build the prompt for Claude Code with consciousness guidance
        prompt = self.build_claude_prompt(message, thought)

        # Create the action
        action = ExecutorAction(
            type=ExecutorActionType.CLAUDE_CODE,
            details={"prompt": prompt},
            priority=self._determine_priority(thought),
        )

        # Execute
        result = await self.executor.execute(action)

        # Track for history
        self._action_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message[:100],
            "action_hint": thought.action_hint,
            "confidence": thought.confidence,
            "success": result.success,
        })

        return result

    def build_claude_prompt(
        self,
        message: str,
        thought: ConsciousnessThought,
    ) -> str:
        """
        Build the prompt for Claude Code with consciousness guidance.

        Args:
            message: Original user message
            thought: Consciousness thought with guidance

        Returns:
            Rich prompt for Claude Code execution
        """
        parts = []

        # System context
        parts.append("You are Stoffy's executor - the skilled hands that act on conscious decisions.")
        parts.append("You have been given a task by the consciousness layer. Execute it completely.")
        parts.append("")

        # Consciousness guidance
        parts.append("## Consciousness Guidance")
        parts.append(f"Understanding: {thought.understanding}")
        parts.append(f"Suggested Approach: {thought.suggested_approach}")
        parts.append(f"Confidence: {thought.confidence:.2f}")

        if thought.action_hint:
            parts.append(f"Action Hint: {thought.action_hint}")

        if thought.metadata:
            parts.append(f"Additional Context: {json.dumps(thought.metadata, indent=2)}")

        parts.append("")

        # Original request
        parts.append("## User Request")
        parts.append(message)
        parts.append("")

        # Execution instructions
        parts.append("## Instructions")
        parts.append("1. Execute the requested action completely")
        parts.append("2. Report what you actually did (not what could be done)")
        parts.append("3. Include relevant output or results")
        parts.append("4. Note any issues or errors encountered")
        parts.append("")
        parts.append("Execute now.")

        return "\n".join(parts)

    def _determine_priority(self, thought: ConsciousnessThought) -> ExecutorPriority:
        """Determine execution priority from thought."""
        if thought.confidence >= 0.9:
            return ExecutorPriority.HIGH
        elif thought.confidence >= 0.7:
            return ExecutorPriority.MEDIUM
        else:
            return ExecutorPriority.LOW

    def _build_response(
        self,
        thought: ConsciousnessThought,
        result: Optional[ExecutionResult],
        mode: str,
    ) -> str:
        """Build human-readable response."""
        parts = []

        if mode == "executed" and result:
            if result.success:
                parts.append("Action completed successfully.")
                if result.output:
                    parts.append("")
                    parts.append("Result:")
                    parts.append(result.output[:1000])
            else:
                parts.append("Action attempted but encountered issues.")
                if result.error:
                    parts.append(f"Error: {result.error}")

        elif mode == "error" and result:
            parts.append("An error occurred during execution.")
            if result.error:
                parts.append(f"Error: {result.error}")
            parts.append("")
            parts.append("Consciousness analysis:")
            parts.append(thought.understanding)

        elif mode == "answered":
            # No action needed - provide the consciousness's understanding
            parts.append(thought.understanding)
            if thought.suggested_approach and thought.suggested_approach != thought.understanding:
                parts.append("")
                parts.append(thought.suggested_approach)

        elif mode == "declined":
            parts.append("I've decided not to proceed with this request.")
            parts.append(f"Reason: {thought.suggested_approach}")

        elif mode == "low_confidence":
            parts.append("I'm not fully confident about this request.")
            parts.append(f"My understanding: {thought.understanding}")
            parts.append(f"Suggested approach: {thought.suggested_approach}")
            parts.append(f"Confidence: {thought.confidence:.0%}")
            parts.append("")
            parts.append("Would you like me to proceed anyway?")

        else:
            parts.append(thought.understanding)
            if thought.suggested_approach:
                parts.append(thought.suggested_approach)

        return "\n".join(parts)

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Get recent action history."""
        return self._action_history[-50:]  # Last 50 actions

    def clear_history(self) -> None:
        """Clear action history."""
        self._action_history.clear()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def process_user_message(
    message: str,
    working_dir: Optional[Path] = None,
    context: Optional[Dict[str, Any]] = None,
    auto_threshold: float = 0.8,
) -> ExecutionResponse:
    """
    Convenience function to process a user message with autonomous execution.

    Args:
        message: User message to process
        working_dir: Working directory (defaults to cwd)
        context: Additional context
        auto_threshold: Auto-execution confidence threshold

    Returns:
        ExecutionResponse with results
    """
    wd = working_dir or Path.cwd()
    executor = AutonomousExecutorWithConsciousness(
        working_dir=wd,
        auto_execute_threshold=auto_threshold,
    )
    return await executor.process_message(message, context)


async def think_then_act(
    message: str,
    working_dir: Optional[Path] = None,
    context: Optional[Dict[str, Any]] = None,
) -> ExecutionResponse:
    """
    Think about a message using Gemini consciousness, then act if needed.

    This is the primary entry point for consciousness-guided autonomous execution.

    Args:
        message: User message to process
        working_dir: Working directory (defaults to cwd)
        context: Additional context

    Returns:
        ExecutionResponse with thought and optional execution result
    """
    return await process_user_message(
        message=message,
        working_dir=working_dir,
        context=context,
        auto_threshold=0.8,
    )


# =============================================================================
# MAIN - Testing
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    async def main():
        """Test the autonomous executor."""
        print("=" * 60)
        print("Autonomous Executor Test")
        print("=" * 60)

        # Check Gemini availability
        consciousness = GeminiConsciousness()
        availability = consciousness.get_availability_info()
        print(f"\nGemini availability: {availability}")

        if not consciousness.is_available():
            print("\nGemini is not available.")
            print("Install gemini CLI or set GOOGLE_API_KEY to enable.")
            print("Testing with fallback behavior...")

        # Test 1: Action request
        print("\n--- Test 1: Action Request ---")
        test_message = "Create a file called test.txt with 'Hello World' in it"

        executor = AutonomousExecutorWithConsciousness(
            working_dir=Path.cwd(),
            auto_execute_threshold=0.8,
            enable_reflection=False,  # Disable for test
        )

        # Just test thinking, not execution
        thought = await consciousness.contemplate(test_message)
        print(f"Understanding: {thought.understanding[:100]}...")
        print(f"Suggested approach: {thought.suggested_approach[:100]}...")
        print(f"Should act: {thought.should_act}")
        print(f"Action hint: {thought.action_hint}")
        print(f"Confidence: {thought.confidence:.2f}")

        # Test 2: Question
        print("\n--- Test 2: Question ---")
        test_question = "What is the purpose of the consciousness module?"

        thought2 = await consciousness.contemplate(test_question)
        print(f"Understanding: {thought2.understanding[:100]}...")
        print(f"Should act: {thought2.should_act}")
        print(f"Confidence: {thought2.confidence:.2f}")

        # Test 3: Build prompt
        print("\n--- Test 3: Claude Prompt Building ---")
        if thought.should_act:
            prompt = executor.build_claude_prompt(test_message, thought)
            print(f"Prompt length: {len(prompt)} chars")
            print(f"Prompt preview:\n{prompt[:500]}...")

        # Test 4: Full flow (dry run)
        print("\n--- Test 4: Full Process Flow (dry run) ---")
        # Use a very high threshold to prevent actual execution
        safe_executor = AutonomousExecutorWithConsciousness(
            working_dir=Path.cwd(),
            auto_execute_threshold=0.99,  # Very high to prevent execution
            enable_reflection=False,
        )

        response = await safe_executor.process_message(
            "What files are in this directory?",
            context={"mode": "test"},
        )

        print(f"Response mode: {response.mode}")
        print(f"Response: {response.response[:200]}...")
        print(f"Thinking time: {response.thinking_duration_ms:.1f}ms")
        print(f"Total time: {response.total_duration_ms:.1f}ms")

        print("\n" + "=" * 60)
        print("Tests complete!")

    asyncio.run(main())
