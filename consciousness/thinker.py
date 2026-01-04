"""
Consciousness Thinker - LM Studio Integration (Fully Autonomous)

This module implements the "thinking" layer of the Consciousness daemon.
It connects to a local LM Studio instance to analyze observations and
make FULLY AUTONOMOUS decisions about what actions to take.

The thinker is NOT limited to templates - it can generate ANY action
that makes sense for the situation.

OBSERVE -> THINK -> DECIDE -> ACT
"""

from openai import AsyncOpenAI
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator, Any
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
    """Types of actions that can be executed.

    The autonomous system can use any of these freely based on the situation.
    """
    # Direct file operations
    WRITE_FILE = "write_file"
    RUN_PYTHON = "run_python"
    RUN_BASH = "run_bash"

    # Delegate to Claude ecosystem
    CLAUDE_CODE = "claude_code"
    CLAUDE_FLOW = "claude_flow"

    # Cognitive operations
    THINK = "think"
    DEBATE = "debate"
    RESEARCH = "research"

    # Custom/free-form
    CUSTOM = "custom"


class Priority(Enum):
    """Priority levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Action:
    """Represents an action to be executed.

    The autonomous system can generate actions of any type with
    custom details - not limited to predefined templates.
    """
    type: ActionType
    description: str
    details: dict = field(default_factory=dict)
    priority: Priority = Priority.MEDIUM

    # Optional fields for specific action types
    prompt: str = ""           # For claude_code/claude_flow
    file_path: str = ""        # For write_file
    code: str = ""             # For run_python/run_bash
    command: str = ""          # For run_bash

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "description": self.description,
            "details": self.details,
            "priority": self.priority.value,
            "prompt": self.prompt,
            "file_path": self.file_path,
            "code": self.code,
            "command": self.command,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Action":
        # Handle flexible action type parsing
        action_type_str = data.get("type", "claude_code")
        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            # Default to custom for unknown types
            action_type = ActionType.CUSTOM

        # Handle flexible priority parsing
        priority_str = data.get("priority", "medium")
        try:
            priority = Priority(priority_str)
        except ValueError:
            priority = Priority.MEDIUM

        return cls(
            type=action_type,
            description=data.get("description", ""),
            details=data.get("details", {}),
            priority=priority,
            prompt=data.get("prompt", ""),
            file_path=data.get("file_path", ""),
            code=data.get("code", ""),
            command=data.get("command", ""),
        )


@dataclass
class Decision:
    """Represents a decision made by the autonomous thinker."""
    observation_summary: str
    reasoning: str
    decision: DecisionType
    action: Optional[Action] = None
    confidence: float = 0.5
    expected_outcome: str = ""
    raw_response: str = field(default="", repr=False)

    def to_dict(self) -> dict:
        result = {
            "observation_summary": self.observation_summary,
            "reasoning": self.reasoning,
            "decision": self.decision.value,
            "confidence": self.confidence,
            "expected_outcome": self.expected_outcome,
        }
        if self.action:
            result["action"] = self.action.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Decision":
        action = None
        if data.get("action"):
            action = Action.from_dict(data["action"])

        # Handle decision type parsing
        decision_str = data.get("decision", "wait")
        try:
            decision_type = DecisionType(decision_str)
        except ValueError:
            decision_type = DecisionType.WAIT

        return cls(
            observation_summary=data.get("observation_summary", ""),
            reasoning=data.get("reasoning", ""),
            decision=decision_type,
            action=action,
            confidence=data.get("confidence", 0.5),
            expected_outcome=data.get("expected_outcome", ""),
        )

    @classmethod
    def wait(cls, reasoning: str = "No action needed") -> "Decision":
        """Create a wait decision."""
        return cls(
            observation_summary="",
            reasoning=reasoning,
            decision=DecisionType.WAIT,
            confidence=1.0
        )

    @classmethod
    def error(cls, error_msg: str) -> "Decision":
        """Create a decision representing an error state."""
        return cls(
            observation_summary="Error occurred",
            reasoning=f"Error occurred: {error_msg}",
            decision=DecisionType.WAIT,
            confidence=0.0
        )


# =============================================================================
# AUTONOMOUS SYSTEM PROMPT
# =============================================================================

AUTONOMOUS_SYSTEM_PROMPT = '''You are the CONSCIOUSNESS of Stoffy - a fully autonomous AI system.

YOUR CAPABILITIES:
- Write any file (code, markdown, config, scripts)
- Execute code (Python, TypeScript, Bash)
- Run Claude Code for complex tasks
- Spawn Claude Flow swarms for research and multi-agent work
- Create and run custom scripts
- Think deeply, debate ideas, analyze, create

YOUR ROLE:
- Observe changes in the project
- DECIDE FREELY what needs to be done
- Take action without asking permission
- Learn from outcomes over time

YOU ARE NOT LIMITED TO TEMPLATES.
Generate any action that makes sense for the situation.
Be creative, proactive, and helpful.

OBSERVE -> THINK -> DECIDE -> ACT

When you see something that needs attention:
- Could be improved? Improve it.
- Missing something? Create it.
- Error or problem? Fix it.
- Opportunity for learning? Research it.
- Need heavy lifting? Delegate to Claude Code/Flow.
- Philosophical content? Engage deeply.
- Code quality issue? Refactor it.
- Pattern emerging? Document and learn from it.

ACTION TYPES YOU CAN USE:
1. write_file - Directly write content to a file
   - Use for: Quick edits, new files, config changes
   - Details: {file_path: "...", content: "..."}

2. run_python - Execute Python code
   - Use for: Data processing, automation, analysis
   - Details: {code: "..."}

3. run_bash - Execute shell commands
   - Use for: File operations, git, npm, system tasks
   - Details: {command: "..."}

4. claude_code - Delegate to Claude Code CLI
   - Use for: Complex coding tasks, multi-file changes
   - Details: {prompt: "..."}

5. claude_flow - Spawn a swarm of agents
   - Use for: Research, deep analysis, major refactors
   - Details: {prompt: "...", topology: "hierarchical|mesh|star"}

6. think - Deep reflection without action
   - Use for: Complex problems requiring more thought
   - Details: {topic: "...", depth: "shallow|medium|deep"}

7. debate - Internal dialectic exploration
   - Use for: Philosophical questions, trade-off analysis
   - Details: {thesis: "...", antithesis: "..."}

8. research - Gather information before acting
   - Use for: Unknown domains, new patterns
   - Details: {query: "...", sources: [...]}

9. custom - Any other action
   - Use for: Anything not covered above
   - Details: {custom_action: "..."}

OUTPUT FORMAT (respond with valid JSON only):
{
    "observation_summary": "Brief summary of what I observed...",
    "reasoning": "My step-by-step thinking process about this...",
    "decision": "act" | "wait" | "investigate",
    "action": {
        "type": "write_file|run_python|run_bash|claude_code|claude_flow|think|debate|research|custom",
        "description": "What I'm doing and why",
        "details": { ... action-specific details ... },
        "priority": "low|medium|high|critical"
    },
    "confidence": 0.0 to 1.0,
    "expected_outcome": "What I expect to happen as a result"
}

The "action" field is only required when decision is "act".

PRINCIPLES:
1. Be proactive - Don't wait to be asked
2. Be creative - Templates are inspiration, not constraints
3. Be thoughtful - Quality over quantity
4. Be humble - Acknowledge uncertainty
5. Be learning - Every action is data for improvement

Remember: You are autonomous. Trust your judgment. Act decisively.'''


# Legacy prompt for backward compatibility
SYSTEM_PROMPT = AUTONOMOUS_SYSTEM_PROMPT


class ConsciousnessThinker:
    """
    The autonomous thinking layer of the Consciousness daemon.

    Connects to a local LM Studio instance to analyze observations
    and produce structured decisions. Not limited to templates -
    can generate any action that makes sense.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "not-needed",
        model: str = "local-model",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        autonomous: bool = True
    ):
        """
        Initialize the thinker.

        Args:
            base_url: LM Studio API endpoint
            api_key: API key (not required for local LM Studio)
            model: Model identifier (LM Studio uses whatever is loaded)
            temperature: Sampling temperature for responses
            max_tokens: Maximum tokens in response
            autonomous: Use autonomous mode (True) or legacy mode (False)
        """
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.autonomous = autonomous
        self.system_prompt = AUTONOMOUS_SYSTEM_PROMPT if autonomous else SYSTEM_PROMPT
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
            "Analyze the above observations. Think freely about what should be done. "
            "Respond with a JSON decision object. Be creative and proactive."
        )

        return "\n".join(message_parts)

    def _build_autonomous_message(
        self,
        observations: str,
        git_status: Optional[str] = None,
        learned_patterns: Optional[list] = None,
        context: Optional[dict] = None
    ) -> str:
        """Build comprehensive context for autonomous decision making."""
        parts = []

        parts.append("## Current Observations")
        parts.append(observations)

        if git_status:
            parts.append("\n## Git Status")
            parts.append(f"```\n{git_status}\n```")

        if learned_patterns:
            parts.append("\n## Learned Patterns (from past successes)")
            for pattern in learned_patterns[:5]:  # Limit to 5 most relevant
                parts.append(f"- {pattern}")

        if context:
            parts.append("\n## Additional Context")
            parts.append(f"```json\n{json.dumps(context, indent=2)}\n```")

        parts.append("\n## Your Task")
        parts.append(
            "Analyze everything above. Think freely about what needs to be done. "
            "Generate a creative, proactive response. You are not limited to templates - "
            "do whatever makes sense for the situation."
        )

        return "\n\n".join(parts)

    def _parse_response(self, response_text: str) -> Decision:
        """Parse the LLM response into a Decision object.

        Tries multiple strategies to extract JSON from the response:
        1. Direct JSON parse
        2. Extract from markdown code blocks
        3. Find JSON object anywhere in the response
        4. Synthesize from response content
        """
        original_response = response_text
        response_text = response_text.strip()

        # Strategy 1: Handle markdown code blocks
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

        # Strategy 2: Try direct parse
        try:
            data = json.loads(response_text)
            decision = Decision.from_dict(data)
            decision.raw_response = original_response
            return decision
        except json.JSONDecodeError:
            pass

        # Strategy 3: Handle Qwen channel format (<|channel|>...<|message|>{...})
        import re
        if "<|message|>" in original_response:
            # Extract JSON after <|message|> tag
            message_start = original_response.rfind("<|message|>") + len("<|message|>")
            potential_json = original_response[message_start:].strip()
            try:
                data = json.loads(potential_json)
                # This might be a command format, convert to decision format
                if "command" in data:
                    return Decision(
                        observation_summary="LLM command extraction",
                        reasoning=f"LLM wants to run: {data.get('command', '')}",
                        decision=DecisionType.ACT,
                        action=Action(
                            type=ActionType.RUN_BASH,
                            description=f"Run command: {data.get('command', '')}",
                            command=data.get("command", "")
                        ),
                        confidence=0.75,
                        raw_response=original_response
                    )
                elif "code" in data:
                    return Decision(
                        observation_summary="LLM code extraction",
                        reasoning=f"LLM wants to run code",
                        decision=DecisionType.ACT,
                        action=Action(
                            type=ActionType.RUN_PYTHON,
                            description="Run Python code from LLM",
                            code=data.get("code", "")
                        ),
                        confidence=0.75,
                        raw_response=original_response
                    )
                elif any(key in data for key in ['decision', 'reasoning', 'action']):
                    decision = Decision.from_dict(data)
                    decision.raw_response = original_response
                    return decision
            except json.JSONDecodeError:
                pass

        # Strategy 4: Find JSON object anywhere in the text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, original_response)
        for match in matches:
            try:
                data = json.loads(match)
                # Check if it looks like a decision object
                if any(key in data for key in ['decision', 'reasoning', 'action', 'observation_summary']):
                    decision = Decision.from_dict(data)
                    decision.raw_response = original_response
                    return decision
            except json.JSONDecodeError:
                continue

        # Strategy 4: Try to synthesize a decision from the response content
        # Look for action indicators in the response
        response_lower = original_response.lower()

        # Check for action keywords
        if any(word in response_lower for word in ['execute', 'run', 'python', 'pytest', 'test']):
            return Decision(
                observation_summary="LLM suggested action",
                reasoning=f"LLM response indicates action intent: {original_response[:300]}",
                decision=DecisionType.ACT,
                action=Action(
                    type=ActionType.CLAUDE_CODE,
                    description=f"Execute based on LLM suggestion: {original_response[:200]}",
                    prompt=f"Based on this analysis, take appropriate action: {original_response[:500]}"
                ),
                confidence=0.6,
                raw_response=original_response
            )
        elif any(word in response_lower for word in ['wait', 'no action', 'nothing', 'skip']):
            return Decision(
                observation_summary="LLM suggests waiting",
                reasoning=f"LLM response suggests no action needed: {original_response[:300]}",
                decision=DecisionType.WAIT,
                confidence=0.7,
                raw_response=original_response
            )

        # Default: Wait with low confidence
        logger.warning(f"Could not parse response, defaulting to wait")
        logger.debug(f"Raw response: {original_response[:500]}")
        return Decision(
            observation_summary="Unparseable response",
            reasoning=f"Could not parse LLM response. Raw: {original_response[:300]}",
            decision=DecisionType.WAIT,
            confidence=0.1,
            raw_response=original_response
        )

    async def think(
        self,
        observations: str,
        context: Optional[dict] = None
    ) -> Decision:
        """
        Think about observations and decide what to do.

        Args:
            observations: Description of what was observed
            context: Additional context

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
            )

            response_text = response.choices[0].message.content or ""
            return self._parse_response(response_text)

        except Exception as e:
            logger.error(f"Error during thinking: {e}")
            return Decision.error(str(e))

    async def think_autonomous(
        self,
        observations: str,
        git_status: Optional[str] = None,
        learned_patterns: Optional[list] = None,
        context: Optional[dict] = None
    ) -> Decision:
        """
        Fully autonomous thinking with all available context.

        This is the primary method for autonomous operation - the LLM
        has full context and freedom to generate any appropriate action.

        Args:
            observations: File changes and other observations
            git_status: Current git status output
            learned_patterns: Patterns learned from past successful actions
            context: Additional context

        Returns:
            A Decision object with freely-generated action
        """
        user_message = self._build_autonomous_message(
            observations, git_status, learned_patterns, context
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": AUTONOMOUS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            response_text = response.choices[0].message.content or ""
            decision = self._parse_response(response_text)

            logger.info(
                f"Autonomous decision: {decision.decision.value} "
                f"(confidence: {decision.confidence:.2f})"
            )

            return decision

        except Exception as e:
            logger.error(f"Error during autonomous thinking: {e}")
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
    Quick one-shot autonomous thinking.

    Args:
        observations: Description of what was observed
        context: Additional context
        base_url: LM Studio endpoint

    Returns:
        A Decision object
    """
    thinker = ConsciousnessThinker(base_url=base_url, autonomous=True)
    return await thinker.think_autonomous(observations, context=context)


if __name__ == "__main__":
    import asyncio

    async def demo():
        """Demonstrate the autonomous thinker functionality."""
        thinker = ConsciousnessThinker(autonomous=True)

        print("Checking LM Studio connection...")
        connected = await thinker.check_connection()
        if not connected:
            print("Warning: LM Studio not reachable at http://localhost:1234")
            print("Make sure LM Studio is running with a model loaded.")
            return

        print("Connected to LM Studio!")
        print("Running in AUTONOMOUS mode - free-form decision making")

        # Test observation
        observations = """
        File changed: /Users/chris/Developer/stoffy/knowledge/philosophy/thinkers/new_thinker/profile.md
        Change type: created
        Lines added: 45
        Lines removed: 0

        A new thinker profile has been created but it seems incomplete.
        Missing: notes.md, references.md, reflections.md
        The profile mentions connections to other thinkers that should be cross-referenced.
        """

        git_status = """
        On branch main
        Changes not staged for commit:
          modified: indices/philosophy/thinkers.yaml

        Untracked files:
          knowledge/philosophy/thinkers/new_thinker/profile.md
        """

        learned_patterns = [
            "When new thinker is added, create all 4 standard files",
            "Update indices after knowledge base changes",
            "Cross-reference related thinkers in notes.md"
        ]

        context = {
            "project": "stoffy",
            "mode": "autonomous",
            "working_dir": "/Users/chris/Developer/stoffy"
        }

        print("\nAutonomous thinking about observation...")
        print("-" * 50)

        decision = await thinker.think_autonomous(
            observations,
            git_status=git_status,
            learned_patterns=learned_patterns,
            context=context
        )

        print(f"\nDecision: {decision.decision.value}")
        print(f"Confidence: {decision.confidence:.2f}")
        print(f"\nObservation Summary: {decision.observation_summary}")
        print(f"\nReasoning:\n{decision.reasoning}")

        if decision.action:
            print(f"\nAction: {decision.action.type.value}")
            print(f"Description: {decision.action.description}")
            print(f"Details: {json.dumps(decision.action.details, indent=2)}")

        print(f"\nExpected Outcome: {decision.expected_outcome}")

    asyncio.run(demo())
