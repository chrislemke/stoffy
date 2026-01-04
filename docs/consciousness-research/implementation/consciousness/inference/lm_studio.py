"""
LM Studio Reasoner - Local LLM Integration for Consciousness Thinking

Implements the INFER phase of the OIDA loop using LM Studio's OpenAI-compatible API.
Supports streaming for responsive thinking and structured JSON output.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from openai import AsyncOpenAI

from ..config import CONSCIOUSNESS_SYSTEM_PROMPT, LMStudioConfig
from ..observers import Observation


class DecisionType(Enum):
    """Types of decisions the consciousness can make."""
    ACT = "act"           # Take action now
    WAIT = "wait"         # Wait for more information
    INVESTIGATE = "investigate"  # Gather more information actively


class ActionType(Enum):
    """Types of actions for delegation."""
    CLAUDE_TASK = "claude_task"         # Single Claude API task
    CLAUDE_FLOW_SWARM = "claude_flow_swarm"  # Multi-agent swarm
    INTERNAL = "internal"               # Internal operation


@dataclass
class SelfAssessment:
    """Metacognitive self-assessment from reasoning."""
    uncertainty_sources: list[str] = field(default_factory=list)
    alternative_interpretations: list[str] = field(default_factory=list)
    metacognitive_flags: list[str] = field(default_factory=list)


@dataclass
class Action:
    """An action to delegate."""
    type: ActionType
    description: str
    prompt: str
    priority: str = "medium"  # low, medium, high, critical


@dataclass
class Decision:
    """A decision made by the consciousness."""
    reasoning: str
    decision: DecisionType
    action: Optional[Action]
    confidence: float
    self_assessment: SelfAssessment
    raw_response: str = ""

    @classmethod
    def parse(cls, response: str) -> "Decision":
        """Parse a JSON response into a Decision."""
        try:
            data = json.loads(response)

            # Parse action if present
            action = None
            if data.get("action"):
                action_data = data["action"]
                action = Action(
                    type=ActionType(action_data.get("type", "internal")),
                    description=action_data.get("description", ""),
                    prompt=action_data.get("prompt", ""),
                    priority=action_data.get("priority", "medium"),
                )

            # Parse self-assessment
            self_data = data.get("self_assessment", {})
            self_assessment = SelfAssessment(
                uncertainty_sources=self_data.get("uncertainty_sources", []),
                alternative_interpretations=self_data.get("alternative_interpretations", []),
                metacognitive_flags=self_data.get("metacognitive_flags", []),
            )

            return cls(
                reasoning=data.get("reasoning", ""),
                decision=DecisionType(data.get("decision", "wait")),
                action=action,
                confidence=float(data.get("confidence", 0.5)),
                self_assessment=self_assessment,
                raw_response=response,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Return a safe "wait" decision if parsing fails
            return cls(
                reasoning=f"Failed to parse response: {e}",
                decision=DecisionType.WAIT,
                action=None,
                confidence=0.0,
                self_assessment=SelfAssessment(
                    metacognitive_flags=[f"Parse error: {e}"]
                ),
                raw_response=response,
            )


class LMStudioReasoner:
    """
    LM Studio client for consciousness reasoning.

    Connects to LM Studio's OpenAI-compatible API for local inference.
    Implements the INFER phase of OIDA loop with streaming support.
    """

    def __init__(self, config: LMStudioConfig):
        self.config = config
        self.client = AsyncOpenAI(
            base_url=config.base_url,
            api_key="not-needed",  # LM Studio doesn't require API key
        )
        self._conversation_history: list[dict[str, str]] = []

    def _format_observations(self, observations: list[Observation]) -> str:
        """Format observations for the LLM prompt."""
        if not observations:
            return "No new observations since last thinking cycle."

        lines = ["## Current Observations\n"]
        for obs in observations:
            lines.append(f"- **{obs.event_type.value}** (priority: {obs.priority:.2f})")
            lines.append(f"  Source: {obs.source}")
            lines.append(f"  Time: {obs.timestamp.isoformat()}")

            # Format payload
            for key, value in obs.payload.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        return "\n".join(lines)

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format additional context for the prompt."""
        lines = ["## Current Context\n"]

        if "active_tasks" in context:
            lines.append(f"Active tasks: {len(context['active_tasks'])}")
            for task in context["active_tasks"][:5]:  # Show top 5
                lines.append(f"  - {task}")

        if "goals" in context:
            lines.append("\nCurrent goals:")
            for goal in context["goals"]:
                lines.append(f"  - {goal}")

        if "recent_decisions" in context:
            lines.append(f"\nRecent decisions: {len(context['recent_decisions'])}")

        return "\n".join(lines)

    async def think(
        self,
        observations: list[Observation],
        context: Optional[dict[str, Any]] = None,
    ) -> Decision:
        """
        Main thinking function - called continuously in the OIDA loop.

        Takes current observations and context, returns a decision.
        Uses streaming for responsive output.
        """
        context = context or {}

        # Build the user message
        user_content = self._format_observations(observations)
        if context:
            user_content += "\n\n" + self._format_context(context)

        user_content += "\n\n## Your Task\nAnalyze these observations and decide what to do. Output valid JSON."

        messages = [
            {"role": "system", "content": CONSCIOUSNESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # Add recent conversation history for continuity
        if self._conversation_history:
            messages = messages[:1] + self._conversation_history[-4:] + messages[1:]

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
            )

            # Collect streamed response
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content

            # Update conversation history
            self._conversation_history.append({"role": "user", "content": user_content})
            self._conversation_history.append({"role": "assistant", "content": full_response})

            # Keep history manageable (last 10 exchanges)
            if len(self._conversation_history) > 20:
                self._conversation_history = self._conversation_history[-20:]

            return Decision.parse(full_response)

        except Exception as e:
            # Return a safe decision on error
            return Decision(
                reasoning=f"LM Studio connection error: {e}",
                decision=DecisionType.WAIT,
                action=None,
                confidence=0.0,
                self_assessment=SelfAssessment(
                    metacognitive_flags=[f"Connection error: {e}"]
                ),
            )

    async def reflect(self, recent_decisions: list[Decision]) -> dict[str, Any]:
        """
        Metacognitive reflection on recent decisions.

        Implements the strange loop: the system observes its own decisions.
        """
        if not recent_decisions:
            return {"reflection": "No decisions to reflect on."}

        reflection_prompt = """## Metacognitive Reflection

Review your recent decisions and assess:
1. Were your confidence levels calibrated correctly?
2. Did your predictions about outcomes match reality?
3. Are there patterns in your uncertainty sources?
4. Should you adjust your decision thresholds?

Recent decisions:
"""
        for d in recent_decisions[-5:]:
            reflection_prompt += f"\n- Decision: {d.decision.value}, Confidence: {d.confidence:.2f}"
            reflection_prompt += f"\n  Reasoning: {d.reasoning[:200]}..."

        reflection_prompt += "\n\nOutput JSON with your reflection."

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are reflecting on your own decision-making process."},
                    {"role": "user", "content": reflection_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=1024,
            )

            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
