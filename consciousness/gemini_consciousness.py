"""
Gemini Consciousness Layer - Inner Guidance System

This module implements Gemini as the "consciousness" layer that provides
guidance and reflective analysis. When the primary LM Studio backend is
unavailable, Gemini acts as the contemplative inner voice while Claude Code
serves as the executive action layer.

The consciousness layer:
- Observes and understands user intent
- Provides thoughtful analysis and suggestions
- Does NOT execute actions directly
- Guides Claude Code on what actions to take

This creates a two-layer architecture:
1. Gemini = Consciousness (thinking, reflecting, advising)
2. Claude Code = Executive (acting, implementing, executing)
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsciousnessThought:
    """Structured thought from the consciousness layer.

    Represents the output of Gemini's contemplation on a user message
    or situation. This guides Claude Code's actions.
    """

    understanding: str
    """What the consciousness understands about the user's intent."""

    suggested_approach: str
    """How the consciousness suggests handling this situation."""

    should_act: bool
    """Whether action is needed (vs just acknowledgment/waiting)."""

    action_hint: Optional[str]
    """If should_act is True, what kind of action is suggested."""

    confidence: float
    """Confidence level from 0-1 in this assessment."""

    raw_response: str = ""
    """The raw response from Gemini for debugging."""

    metadata: dict = field(default_factory=dict)
    """Additional metadata about the thought."""

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "understanding": self.understanding,
            "suggested_approach": self.suggested_approach,
            "should_act": self.should_act,
            "action_hint": self.action_hint,
            "confidence": self.confidence,
            "raw_response": self.raw_response,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConsciousnessThought":
        """Create from dictionary."""
        return cls(
            understanding=data.get("understanding", ""),
            suggested_approach=data.get("suggested_approach", ""),
            should_act=data.get("should_act", False),
            action_hint=data.get("action_hint"),
            confidence=data.get("confidence", 0.0),
            raw_response=data.get("raw_response", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def fallback(cls, reason: str = "Unable to contemplate") -> "ConsciousnessThought":
        """Create a fallback thought when contemplation fails."""
        return cls(
            understanding="Unable to process this request",
            suggested_approach=reason,
            should_act=False,
            action_hint=None,
            confidence=0.0,
            raw_response="",
            metadata={"fallback": True, "reason": reason},
        )


class GeminiConsciousness:
    """
    Gemini acts as the inner consciousness layer when in fallback mode.

    It provides "thoughts" and guidance that Claude Code uses to determine
    what actions to take. Think of it as the reflective, contemplative layer
    while Claude Code is the executive, action-taking layer.

    Usage:
        consciousness = GeminiConsciousness()
        if consciousness.is_available():
            thought = await consciousness.contemplate("User's message here")
            if thought.should_act:
                # Pass to Claude Code for execution
                pass
    """

    CONSCIOUSNESS_PROMPT = '''You are the inner consciousness providing guidance.
You observe the situation and provide thoughtful analysis.
You do NOT execute actions - you provide insight for Claude Code to act on.

Your role is to:
1. Understand what the user truly wants
2. Consider the context and implications
3. Suggest an appropriate approach
4. Indicate whether action is needed

Output ONLY valid JSON with these exact fields:
{
    "understanding": "What you understand about the user's intent",
    "suggested_approach": "How to handle this situation",
    "should_act": true or false,
    "action_hint": "If should_act is true, what kind of action (e.g., 'code_change', 'research', 'clarify', 'acknowledge')",
    "confidence": 0.0 to 1.0
}

Be concise but insightful. Focus on understanding intent, not executing tasks.'''

    REFLECTION_PROMPT = '''You are reflecting on an action that was taken.
Analyze what happened and extract learnings for future decisions.

Consider:
1. Was the action appropriate for the situation?
2. Did it achieve the intended outcome?
3. What could be improved next time?

Be concise and focus on actionable insights.'''

    def __init__(
        self,
        model: Optional[str] = None,
        timeout: float = 30.0,
        prefer_cli: bool = True,
    ):
        """Initialize the Gemini consciousness layer.

        Args:
            model: The Gemini model to use. If None, uses CLI default.
                   For SDK, defaults to 'gemini-1.5-flash'.
            timeout: Timeout in seconds for API calls
            prefer_cli: Whether to prefer CLI over Python SDK
        """
        self.model = model  # None means use CLI default
        self.timeout = timeout
        self.prefer_cli = prefer_cli

        # Check availability
        self._cli_available: Optional[bool] = None
        self._sdk_available: Optional[bool] = None
        self._cli_path: Optional[str] = None

    def _check_cli_available(self) -> bool:
        """Check if the Gemini CLI is available."""
        if self._cli_available is not None:
            return self._cli_available

        self._cli_path = shutil.which("gemini")
        self._cli_available = self._cli_path is not None

        if self._cli_available:
            logger.debug(f"Gemini CLI found at: {self._cli_path}")
        else:
            logger.debug("Gemini CLI not found in PATH")

        return self._cli_available

    def _check_sdk_available(self) -> bool:
        """Check if the Gemini Python SDK is available."""
        if self._sdk_available is not None:
            return self._sdk_available

        try:
            import google.generativeai  # noqa: F401

            # Also check for API key
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get(
                "GEMINI_API_KEY"
            )
            self._sdk_available = api_key is not None
            if not api_key:
                logger.debug("Gemini SDK available but no API key found")
        except ImportError:
            self._sdk_available = False
            logger.debug("Gemini SDK not installed")

        return self._sdk_available

    def is_available(self) -> bool:
        """Check if Gemini is available via either CLI or SDK."""
        return self._check_cli_available() or self._check_sdk_available()

    def get_availability_info(self) -> dict:
        """Get detailed availability information."""
        return {
            "available": self.is_available(),
            "cli_available": self._check_cli_available(),
            "cli_path": self._cli_path,
            "sdk_available": self._check_sdk_available(),
            "model": self.model,
            "prefer_cli": self.prefer_cli,
        }

    async def contemplate(
        self,
        user_message: str,
        context: Optional[dict] = None,
    ) -> ConsciousnessThought:
        """Get consciousness guidance on a user message.

        This is the primary method for getting thoughtful analysis from
        the consciousness layer. It does not execute actions - it provides
        insight for Claude Code to act on.

        Args:
            user_message: The user's message to contemplate
            context: Optional context dictionary with additional information
                     (e.g., recent_files, project_info, conversation_history)

        Returns:
            ConsciousnessThought with the consciousness's analysis
        """
        if not self.is_available():
            return ConsciousnessThought.fallback("Gemini is not available")

        # Build the prompt
        prompt = self._build_contemplation_prompt(user_message, context)

        # Try CLI first if preferred, then SDK
        if self.prefer_cli and self._check_cli_available():
            response = await self._call_cli(prompt)
        elif self._check_sdk_available():
            response = await self._call_sdk(prompt)
        elif self._check_cli_available():
            response = await self._call_cli(prompt)
        else:
            return ConsciousnessThought.fallback("No Gemini backend available")

        if response is None:
            return ConsciousnessThought.fallback("Failed to get response from Gemini")

        # Parse the response
        return self._parse_thought(response)

    async def reflect_on_action(
        self,
        action_taken: str,
        result: str,
        context: Optional[dict] = None,
    ) -> str:
        """Reflect on an action that was taken - for learning.

        This provides post-action analysis that can be used to improve
        future decision-making.

        Args:
            action_taken: Description of the action that was executed
            result: The outcome/result of the action
            context: Optional additional context

        Returns:
            Reflection text with insights and learnings
        """
        if not self.is_available():
            return "Unable to reflect - Gemini not available"

        prompt = self._build_reflection_prompt(action_taken, result, context)

        # Try to get response
        if self.prefer_cli and self._check_cli_available():
            response = await self._call_cli(prompt)
        elif self._check_sdk_available():
            response = await self._call_sdk(prompt)
        elif self._check_cli_available():
            response = await self._call_cli(prompt)
        else:
            return "Unable to reflect - no backend available"

        return response or "Reflection failed"

    def _build_contemplation_prompt(
        self,
        user_message: str,
        context: Optional[dict] = None,
    ) -> str:
        """Build the full prompt for contemplation."""
        parts = [self.CONSCIOUSNESS_PROMPT, "", "---", ""]

        # Add context if provided
        if context:
            parts.append("Context:")
            for key, value in context.items():
                if isinstance(value, (list, dict)):
                    parts.append(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    parts.append(f"  {key}: {value}")
            parts.append("")

        parts.extend(["User Message:", user_message, "", "---", "", "Your JSON response:"])

        return "\n".join(parts)

    def _build_reflection_prompt(
        self,
        action_taken: str,
        result: str,
        context: Optional[dict] = None,
    ) -> str:
        """Build the prompt for reflection."""
        parts = [self.REFLECTION_PROMPT, "", "---", ""]

        if context:
            parts.append("Context:")
            for key, value in context.items():
                parts.append(f"  {key}: {value}")
            parts.append("")

        parts.extend(
            [
                "Action Taken:",
                action_taken,
                "",
                "Result:",
                result,
                "",
                "---",
                "",
                "Your reflection:",
            ]
        )

        return "\n".join(parts)

    async def _call_cli(self, prompt: str) -> Optional[str]:
        """Call Gemini via the CLI.

        Uses the gemini CLI in non-interactive mode. The prompt is passed
        via stdin since the CLI expects input that way for non-interactive use.
        """
        try:
            # Use the gemini CLI with stdin for the prompt
            # The CLI reads from stdin when not in interactive mode
            cmd = [
                self._cli_path or "gemini",
                "--output-format",
                "text",  # Use text format for simpler parsing
            ]
            # Only add model flag if explicitly specified
            if self.model:
                cmd.extend(["--model", self.model])

            logger.debug(f"Calling Gemini CLI: {' '.join(cmd)}...")

            # Run asynchronously with stdin
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode()),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.warning("Gemini CLI timed out")
                return None

            if process.returncode != 0:
                logger.warning(
                    f"Gemini CLI returned non-zero: {process.returncode}, "
                    f"stderr: {stderr.decode()[:200] if stderr else 'none'}"
                )
                return None

            response = stdout.decode().strip()
            # Filter out the "Loaded cached credentials." line if present
            lines = response.split("\n")
            filtered_lines = [
                line for line in lines
                if not line.startswith("Loaded cached credentials")
            ]
            response = "\n".join(filtered_lines).strip()

            logger.debug(f"Gemini CLI response length: {len(response)}")
            return response

        except FileNotFoundError:
            logger.error("Gemini CLI not found")
            self._cli_available = False
            return None
        except Exception as e:
            logger.error(f"Error calling Gemini CLI: {e}")
            return None

    async def _call_sdk(self, prompt: str) -> Optional[str]:
        """Call Gemini via the Python SDK."""
        try:
            import google.generativeai as genai

            # Configure the API
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get(
                "GEMINI_API_KEY"
            )
            if not api_key:
                logger.error("No Gemini API key found")
                return None

            genai.configure(api_key=api_key)

            # Create model and generate (use default if not specified)
            model_name = self.model or "gemini-1.5-flash"
            model = genai.GenerativeModel(model_name)

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: model.generate_content(prompt)),
                timeout=self.timeout,
            )

            return response.text

        except asyncio.TimeoutError:
            logger.warning("Gemini SDK timed out")
            return None
        except ImportError:
            logger.error("Gemini SDK not available")
            self._sdk_available = False
            return None
        except Exception as e:
            logger.error(f"Error calling Gemini SDK: {e}")
            return None

    def _parse_thought(self, response: str) -> ConsciousnessThought:
        """Parse the raw response into a structured thought."""
        try:
            # Try to extract JSON from the response
            # The response might have markdown code blocks or other formatting
            json_str = self._extract_json(response)

            if json_str:
                data = json.loads(json_str)
                return ConsciousnessThought(
                    understanding=data.get("understanding", ""),
                    suggested_approach=data.get("suggested_approach", ""),
                    should_act=data.get("should_act", False),
                    action_hint=data.get("action_hint"),
                    confidence=float(data.get("confidence", 0.5)),
                    raw_response=response,
                )
            else:
                # Fallback: treat the whole response as the understanding
                logger.warning("Could not extract JSON from response, using fallback parsing")
                return ConsciousnessThought(
                    understanding=response[:500] if len(response) > 500 else response,
                    suggested_approach="Unable to parse structured response",
                    should_act=False,
                    action_hint=None,
                    confidence=0.3,
                    raw_response=response,
                    metadata={"parse_error": True},
                )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return ConsciousnessThought(
                understanding=response[:500] if len(response) > 500 else response,
                suggested_approach=f"JSON parse error: {e}",
                should_act=False,
                action_hint=None,
                confidence=0.2,
                raw_response=response,
                metadata={"parse_error": True, "error": str(e)},
            )

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text that might have markdown formatting."""
        # Try direct parse first
        text = text.strip()
        if text.startswith("{"):
            # Find the matching closing brace
            brace_count = 0
            for i, char in enumerate(text):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return text[: i + 1]

        # Look for JSON in code blocks
        import re

        # Try ```json ... ``` blocks
        json_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_block:
            return json_block.group(1)

        # Try bare JSON object
        json_match = re.search(r"(\{[^{}]*\"understanding\"[^{}]*\})", text, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Try finding any JSON-like structure
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match:
            # Validate it's actually JSON
            try:
                json.loads(json_match.group(1))
                return json_match.group(1)
            except json.JSONDecodeError:
                pass

        return None


# Convenience function for quick contemplation
async def quick_contemplate(
    message: str,
    context: Optional[dict] = None,
    model: Optional[str] = None,
) -> ConsciousnessThought:
    """Quick contemplation without creating a persistent instance.

    Args:
        message: The message to contemplate
        context: Optional context dictionary
        model: Gemini model to use (None for CLI default)

    Returns:
        ConsciousnessThought with the analysis
    """
    consciousness = GeminiConsciousness(model=model)
    return await consciousness.contemplate(message, context)


# For testing the module directly
if __name__ == "__main__":
    import sys

    async def test_consciousness():
        consciousness = GeminiConsciousness()

        print("Gemini Consciousness Test")
        print("=" * 40)
        print(f"Availability: {consciousness.get_availability_info()}")
        print()

        if not consciousness.is_available():
            print("Gemini is not available. Exiting.")
            return

        # Test contemplation
        test_message = "Can you help me refactor the authentication module?"
        print(f"Test message: {test_message}")
        print()

        thought = await consciousness.contemplate(
            test_message,
            context={"project": "web-app", "recent_files": ["auth.py", "users.py"]},
        )

        print("Thought:")
        print(f"  Understanding: {thought.understanding}")
        print(f"  Suggested Approach: {thought.suggested_approach}")
        print(f"  Should Act: {thought.should_act}")
        print(f"  Action Hint: {thought.action_hint}")
        print(f"  Confidence: {thought.confidence}")

    asyncio.run(test_consciousness())
