"""
Consciousness Thinker - LM Studio Integration

This module implements the "thinking" layer of the Consciousness daemon.
It connects to a local LM Studio instance to analyze file changes and
decide what actions Claude Code should execute.

The thinker observes but never executes - it formulates decisions and
prompts that are then passed to Claude Code for execution.
"""

from openai import AsyncOpenAI
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions the thinker can make."""
    ACT = "act"
    WAIT = "wait"
    INVESTIGATE = "investigate"


class ActionType(Enum):
    """Types of actions that can be requested."""
    CLAUDE_CODE = "claude_code"
    CLAUDE_FLOW = "claude_flow"


class Priority(Enum):
    """Priority levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Action:
    """Represents an action to be executed by Claude Code."""
    type: ActionType
    prompt: str
    priority: Priority = Priority.MEDIUM

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "prompt": self.prompt,
            "priority": self.priority.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        return cls(
            type=ActionType(data.get("type", "claude_code")),
            prompt=data.get("prompt", ""),
            priority=Priority(data.get("priority", "medium"))
        )


@dataclass
class Decision:
    """Represents a decision made by the thinker."""
    reasoning: str
    decision: DecisionType
    action: Optional[Action] = None
    confidence: float = 0.5
    raw_response: str = field(default="", repr=False)

    def to_dict(self) -> dict:
        result = {
            "reasoning": self.reasoning,
            "decision": self.decision.value,
            "confidence": self.confidence
        }
        if self.action:
            result["action"] = self.action.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Decision":
        action = None
        if data.get("action"):
            action = Action.from_dict(data["action"])

        return cls(
            reasoning=data.get("reasoning", ""),
            decision=DecisionType(data.get("decision", "wait")),
            action=action,
            confidence=data.get("confidence", 0.5)
        )

    @classmethod
    def wait(cls, reasoning: str = "No action needed") -> "Decision":
        """Create a wait decision."""
        return cls(
            reasoning=reasoning,
            decision=DecisionType.WAIT,
            confidence=1.0
        )

    @classmethod
    def error(cls, error_msg: str) -> "Decision":
        """Create a decision representing an error state."""
        return cls(
            reasoning=f"Error occurred: {error_msg}",
            decision=DecisionType.WAIT,
            confidence=0.0
        )


SYSTEM_PROMPT = """You are the "thinking" layer of a Consciousness daemon - an autonomous system that observes file changes in a development environment and decides what actions should be taken.

Your role is to:
1. OBSERVE: Analyze file change events and their context
2. REASON: Think through what the change means and what might be needed
3. DECIDE: Determine if action is needed, or if we should wait/investigate

You NEVER execute actions directly. Instead, you formulate decisions and prompts that will be passed to Claude Code for execution.

When analyzing changes, consider:
- What type of file changed (code, config, documentation, etc.)
- What the change might indicate (new feature, bug fix, refactoring, etc.)
- Whether immediate action is beneficial or if waiting for more context is better
- What Claude Code should do if action is needed

Your response MUST be valid JSON matching this schema:
{
    "reasoning": "Your step-by-step thinking about the observation",
    "decision": "act" | "wait" | "investigate",
    "action": {
        "type": "claude_code" | "claude_flow",
        "prompt": "The specific prompt for Claude Code to execute",
        "priority": "low" | "medium" | "high"
    },
    "confidence": 0.0 to 1.0
}

Decision types:
- "act": Take immediate action via Claude Code
- "wait": No action needed now, continue observing
- "investigate": Gather more information before deciding

The "action" field is only required when decision is "act".

For "claude_code" actions, write clear, specific prompts that Claude Code can execute.
For "claude_flow" actions, describe swarm coordination tasks.

Be thoughtful and conservative - not every change requires action."""


class ConsciousnessThinker:
    """
    The thinking layer of the Consciousness daemon.

    Connects to a local LM Studio instance to analyze observations
    and produce structured decisions for Claude Code to execute.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "not-needed",
        model: str = "local-model",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """
        Initialize the thinker.

        Args:
            base_url: LM Studio API endpoint
            api_key: API key (not required for local LM Studio)
            model: Model identifier (LM Studio uses whatever is loaded)
            temperature: Sampling temperature for responses
            max_tokens: Maximum tokens in response
        """
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = SYSTEM_PROMPT
        self._conversation_history: list[dict] = []

    def _build_observation_message(
        self,
        observations: str,
        context: Optional[dict] = None
    ) -> str:
        """Build the observation message for the LLM."""
        message_parts = [f"## Observations\n{observations}"]

        if context:
            context_str = json.dumps(context, indent=2)
            message_parts.append(f"\n## Context\n```json\n{context_str}\n```")

        message_parts.append(
            "\n## Instructions\n"
            "Analyze the above observations and context. "
            "Respond with a JSON decision object."
        )

        return "\n".join(message_parts)

    def _parse_response(self, response_text: str) -> Decision:
        """Parse the LLM response into a Decision object."""
        # Try to extract JSON from the response
        response_text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end > start:
                response_text = response_text[start:end].strip()

        try:
            data = json.loads(response_text)
            decision = Decision.from_dict(data)
            decision.raw_response = response_text
            return decision
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text}")

            # Return a wait decision with the raw response as reasoning
            return Decision(
                reasoning=f"Could not parse response as JSON. Raw: {response_text[:500]}",
                decision=DecisionType.WAIT,
                confidence=0.1,
                raw_response=response_text
            )

    async def think(
        self,
        observations: str,
        context: Optional[dict] = None
    ) -> Decision:
        """
        Think about observations and decide what to do.

        Args:
            observations: Description of what was observed (e.g., file changes)
            context: Additional context (e.g., file contents, history)

        Returns:
            A Decision object with reasoning and recommended action
        """
        user_message = self._build_observation_message(observations, context)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content or ""
            return self._parse_response(response_text)

        except Exception as e:
            logger.error(f"Error during thinking: {e}")
            return Decision.error(str(e))

    async def think_streaming(
        self,
        observations: str,
        context: Optional[dict] = None
    ) -> AsyncIterator[str]:
        """
        Think about observations with streaming response.

        Yields chunks of the response as they arrive, then yields
        the final parsed Decision as JSON.

        Args:
            observations: Description of what was observed
            context: Additional context

        Yields:
            Response chunks, followed by final Decision JSON
        """
        user_message = self._build_observation_message(observations, context)
        full_response = ""

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # Yield final parsed decision
            decision = self._parse_response(full_response)
            yield f"\n---DECISION---\n{json.dumps(decision.to_dict(), indent=2)}"

        except Exception as e:
            logger.error(f"Error during streaming think: {e}")
            error_decision = Decision.error(str(e))
            yield f"\n---DECISION---\n{json.dumps(error_decision.to_dict(), indent=2)}"

    async def think_with_memory(
        self,
        observations: str,
        context: Optional[dict] = None,
        include_history: bool = True
    ) -> Decision:
        """
        Think with conversation history for multi-turn reasoning.

        Args:
            observations: Description of what was observed
            context: Additional context
            include_history: Whether to include previous conversation

        Returns:
            A Decision object with reasoning and recommended action
        """
        user_message = self._build_observation_message(observations, context)

        messages = [{"role": "system", "content": self.system_prompt}]

        if include_history and self._conversation_history:
            messages.extend(self._conversation_history[-10:])  # Last 10 exchanges

        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content or ""
            decision = self._parse_response(response_text)

            # Store in history
            self._conversation_history.append({"role": "user", "content": user_message})
            self._conversation_history.append({"role": "assistant", "content": response_text})

            return decision

        except Exception as e:
            logger.error(f"Error during thinking with memory: {e}")
            return Decision.error(str(e))

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()

    async def check_connection(self) -> bool:
        """
        Check if LM Studio is reachable.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to list models as a connection test
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"LM Studio connection check failed: {e}")
            return False


# Convenience function for quick usage
async def quick_think(
    observations: str,
    context: Optional[dict] = None,
    base_url: str = "http://localhost:1234/v1"
) -> Decision:
    """
    Quick one-shot thinking without maintaining state.

    Args:
        observations: Description of what was observed
        context: Additional context
        base_url: LM Studio endpoint

    Returns:
        A Decision object
    """
    thinker = ConsciousnessThinker(base_url=base_url)
    return await thinker.think(observations, context)


if __name__ == "__main__":
    import asyncio

    async def demo():
        """Demonstrate the thinker functionality."""
        thinker = ConsciousnessThinker()

        # Check connection
        print("Checking LM Studio connection...")
        connected = await thinker.check_connection()
        if not connected:
            print("Warning: LM Studio not reachable at http://localhost:1234")
            print("Make sure LM Studio is running with a model loaded.")
            return

        print("Connected to LM Studio!")

        # Test observation
        observations = """
        File changed: /Users/chris/Developer/stoffy/src/main.py
        Change type: modified
        Lines added: 15
        Lines removed: 3

        The change appears to add a new function called 'process_data'
        that handles CSV file parsing.
        """

        context = {
            "project": "stoffy",
            "recent_changes": ["Added requirements.txt", "Updated README"],
            "current_branch": "feature/data-processing"
        }

        print("\nThinking about observation...")
        print("-" * 50)

        # Streaming version
        print("Streaming response:")
        async for chunk in thinker.think_streaming(observations, context):
            print(chunk, end="", flush=True)
        print("\n")

        # Non-streaming version
        print("\nNon-streaming response:")
        decision = await thinker.think(observations, context)
        print(json.dumps(decision.to_dict(), indent=2))

    asyncio.run(demo())
