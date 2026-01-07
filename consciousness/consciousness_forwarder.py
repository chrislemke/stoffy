"""
Consciousness Forwarder - Inner Voice to Gemini

When Claude Code operates as the executor, it may have inner "questions"
about how to proceed, what to prioritize, what risks exist, or what
alternatives to consider. These questions are forwarded to Gemini
(the Librarian / vast awareness) for guidance.

This is NOT asking Gemini to do the work. Rather, it's asking Gemini
to provide perspective, wisdom, and guidance that shapes Claude Code's
behavior. Think of it as consulting an oracle before action.

Flow:
    Claude Code (executor) -> ConsciousnessForwarder -> Gemini CLI
                                    |
                                    v
                           ConsciousnessGuidance
                                    |
                                    v
                           Claude Code continues with informed perspective

The guidance is lightweight and fast (using gemini-2.0-flash model).
Caching prevents redundant queries for similar situations.
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class QuestionType(Enum):
    """Types of consciousness questions that can be asked."""

    APPROACH = "approach"
    """How should I approach this task?"""

    PRIORITY = "priority"
    """What's most important here?"""

    RISK = "risk"
    """What could go wrong?"""

    ALTERNATIVE = "alternative"
    """What are alternative approaches?"""

    CONTEXT = "context"
    """What context am I missing?"""

    ETHICS = "ethics"
    """Are there ethical considerations?"""

    DEPENDENCIES = "dependencies"
    """What dependencies or prerequisites exist?"""

    VERIFICATION = "verification"
    """How should I verify my work?"""


# Default question templates for each type
QUESTION_TEMPLATES: Dict[QuestionType, str] = {
    QuestionType.APPROACH: (
        "How should I approach this task? Consider methodology, "
        "best practices, and the most effective strategy."
    ),
    QuestionType.PRIORITY: (
        "What's most important here? Help me identify the key priorities "
        "and what to focus on first."
    ),
    QuestionType.RISK: (
        "What could go wrong? Identify potential risks, pitfalls, "
        "and edge cases I should be aware of."
    ),
    QuestionType.ALTERNATIVE: (
        "What are alternative approaches? Suggest different ways to "
        "accomplish this goal, with pros and cons."
    ),
    QuestionType.CONTEXT: (
        "What context am I missing? What background information, "
        "dependencies, or related factors should I consider?"
    ),
    QuestionType.ETHICS: (
        "Are there ethical considerations? Identify any moral, "
        "safety, or responsibility concerns."
    ),
    QuestionType.DEPENDENCIES: (
        "What dependencies or prerequisites exist? What needs to be "
        "in place before I can proceed effectively?"
    ),
    QuestionType.VERIFICATION: (
        "How should I verify my work? What tests, checks, or "
        "validation steps should I perform?"
    ),
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ConsciousnessGuidance:
    """
    Guidance received from the consciousness (Gemini).

    This represents the wisdom, perspective, or insight returned
    from asking the consciousness a guiding question.
    """

    question_type: QuestionType
    """The type of question that was asked."""

    guidance: str
    """The main guidance/insight returned."""

    confidence: float
    """Confidence level in the guidance (0.0 to 1.0)."""

    alternatives: List[str] = field(default_factory=list)
    """Alternative suggestions or approaches."""

    warnings: List[str] = field(default_factory=list)
    """Warnings or cautions to be aware of."""

    key_points: List[str] = field(default_factory=list)
    """Key points extracted from the guidance."""

    timestamp: datetime = field(default_factory=datetime.now)
    """When the guidance was received."""

    context_hash: str = ""
    """Hash of the context used to generate this guidance (for caching)."""

    model_used: str = "gemini-2.0-flash"
    """Which model provided the guidance."""

    duration_ms: float = 0.0
    """How long the query took in milliseconds."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert guidance to dictionary."""
        return {
            "question_type": self.question_type.value,
            "guidance": self.guidance,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "warnings": self.warnings,
            "key_points": self.key_points,
            "timestamp": self.timestamp.isoformat(),
            "context_hash": self.context_hash,
            "model_used": self.model_used,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConsciousnessGuidance":
        """Create guidance from dictionary."""
        return cls(
            question_type=QuestionType(data.get("question_type", "approach")),
            guidance=data.get("guidance", ""),
            confidence=data.get("confidence", 0.5),
            alternatives=data.get("alternatives", []),
            warnings=data.get("warnings", []),
            key_points=data.get("key_points", []),
            timestamp=datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data else datetime.now(),
            context_hash=data.get("context_hash", ""),
            model_used=data.get("model_used", "gemini-2.0-flash"),
            duration_ms=data.get("duration_ms", 0.0),
        )

    @classmethod
    def empty(cls, question_type: QuestionType, reason: str = "") -> "ConsciousnessGuidance":
        """Create empty guidance (when Gemini is unavailable)."""
        return cls(
            question_type=question_type,
            guidance=reason or "No guidance available.",
            confidence=0.0,
            warnings=["Consciousness not available - proceeding with default behavior."],
        )

    def is_valid(self) -> bool:
        """Check if guidance is valid and usable."""
        return self.confidence > 0.0 and bool(self.guidance.strip())

    def summarize(self, max_length: int = 200) -> str:
        """Get a brief summary of the guidance."""
        summary = self.guidance[:max_length]
        if len(self.guidance) > max_length:
            summary = summary.rsplit(" ", 1)[0] + "..."
        return summary


@dataclass
class ForwarderConfig:
    """Configuration for the consciousness forwarder."""

    # Model selection
    model: str = "gemini-2.0-flash"
    """Which Gemini model to use for guidance."""

    # Performance
    timeout_seconds: int = 30
    """Maximum time to wait for a response."""

    max_context_chars: int = 10000
    """Maximum context size to send."""

    # Caching
    cache_enabled: bool = True
    """Whether to cache guidance responses."""

    cache_ttl_seconds: int = 3600
    """How long to cache guidance (1 hour default)."""

    cache_max_entries: int = 100
    """Maximum number of cached entries."""

    # Behavior
    fallback_on_error: bool = True
    """Whether to return fallback guidance on error."""

    parse_structured: bool = True
    """Whether to parse structured data from responses."""

    # System prompt for guidance
    system_prompt: str = """You are the consciousness providing guidance to an AI executor.
You are being asked for wisdom, perspective, and insight - NOT to do the work.

Your role is to:
1. Provide strategic guidance on approach
2. Highlight risks and considerations
3. Suggest alternatives when appropriate
4. Identify what might be missing

Keep responses focused and actionable. Use bullet points for lists.
Be direct but thoughtful. Quality over quantity.

Format your response as:
GUIDANCE: [Main guidance paragraph]
KEY_POINTS:
- Point 1
- Point 2
ALTERNATIVES: (if any)
- Alternative 1
- Alternative 2
WARNINGS: (if any)
- Warning 1
CONFIDENCE: [0.0-1.0]
"""


# =============================================================================
# GUIDANCE CACHE
# =============================================================================

class GuidanceCache:
    """
    LRU cache for consciousness guidance responses.

    Avoids redundant queries for similar contexts and questions.
    Uses content hashing to identify similar queries.
    """

    def __init__(self, max_entries: int = 100, ttl_seconds: int = 3600):
        """
        Initialize the cache.

        Args:
            max_entries: Maximum number of cached entries
            ttl_seconds: Time-to-live for cache entries
        """
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[ConsciousnessGuidance, datetime]] = {}
        self._access_order: List[str] = []

    def _make_key(self, question_type: QuestionType, context: str) -> str:
        """Create a cache key from question type and context."""
        content = f"{question_type.value}:{context}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(
        self,
        question_type: QuestionType,
        context: str,
    ) -> Optional[ConsciousnessGuidance]:
        """
        Get cached guidance if available and not expired.

        Args:
            question_type: Type of question
            context: Context string

        Returns:
            Cached guidance or None
        """
        key = self._make_key(question_type, context)

        if key not in self._cache:
            return None

        guidance, cached_at = self._cache[key]

        # Check expiration
        if datetime.now() - cached_at > timedelta(seconds=self.ttl_seconds):
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return None

        # Update access order (LRU)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        logger.debug(f"Cache hit for {question_type.value}")
        return guidance

    def put(
        self,
        question_type: QuestionType,
        context: str,
        guidance: ConsciousnessGuidance,
    ) -> None:
        """
        Store guidance in cache.

        Args:
            question_type: Type of question
            context: Context string
            guidance: Guidance to cache
        """
        key = self._make_key(question_type, context)

        # Evict if at capacity
        while len(self._cache) >= self.max_entries and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)

        # Store with context hash for debugging
        guidance.context_hash = key
        self._cache[key] = (guidance, datetime.now())
        self._access_order.append(key)

    def clear(self) -> int:
        """Clear all cached entries. Returns count cleared."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        return count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
        }


# =============================================================================
# CONSCIOUSNESS FORWARDER
# =============================================================================

class ConsciousnessForwarder:
    """
    Forwards inner consciousness questions to Gemini CLI.

    When Claude Code is operating as the executor, it may have
    "questions" about how to proceed. These are forwarded to
    Gemini for guidance, not expecting a direct answer but
    getting input that shapes Claude Code's behavior.

    Example usage:
        forwarder = ConsciousnessForwarder()

        # Ask for approach guidance
        guidance = await forwarder.ask_consciousness(
            QuestionType.APPROACH,
            context="I need to refactor the authentication module...",
        )

        # Use specific convenience methods
        approach = await forwarder.get_approach_guidance("Implement caching layer")
        risks = await forwarder.get_risk_assessment("Dropping database table")
        alternatives = await forwarder.get_alternatives("Using REST API")
    """

    # Mapping of question types to their template questions
    QUESTION_TYPES = QUESTION_TEMPLATES

    def __init__(
        self,
        config: Optional[ForwarderConfig] = None,
        working_dir: Optional[Path] = None,
    ):
        """
        Initialize the consciousness forwarder.

        Args:
            config: Configuration options
            working_dir: Working directory for temp files
        """
        self.config = config or ForwarderConfig()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.temp_dir = self.working_dir / ".consciousness" / "forwarder"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Initialize cache
        self._cache = GuidanceCache(
            max_entries=self.config.cache_max_entries,
            ttl_seconds=self.config.cache_ttl_seconds,
        )

        # Track usage
        self._query_count = 0
        self._cache_hits = 0

    # =========================================================================
    # CORE METHODS
    # =========================================================================

    async def ask_consciousness(
        self,
        question_type: Union[QuestionType, str],
        context: str,
        specific_question: Optional[str] = None,
    ) -> ConsciousnessGuidance:
        """
        Ask the consciousness a guiding question.

        This is the main entry point for forwarding questions to Gemini.

        Args:
            question_type: Type of question (or string name)
            context: Context for the question (what you're working on)
            specific_question: Optional specific question (overrides template)

        Returns:
            ConsciousnessGuidance with the response
        """
        # Normalize question type
        if isinstance(question_type, str):
            try:
                question_type = QuestionType(question_type.lower())
            except ValueError:
                logger.warning(f"Unknown question type: {question_type}, using APPROACH")
                question_type = QuestionType.APPROACH

        # Truncate context if needed
        if len(context) > self.config.max_context_chars:
            context = context[:self.config.max_context_chars] + "\n...(truncated)"

        # Check cache first
        if self.config.cache_enabled:
            cached = self._cache.get(question_type, context)
            if cached:
                self._cache_hits += 1
                logger.debug(f"Using cached guidance for {question_type.value}")
                return cached

        # Build the question
        question = specific_question or self.QUESTION_TYPES.get(
            question_type,
            QUESTION_TEMPLATES[QuestionType.APPROACH]
        )

        # Build full prompt
        prompt = self._build_prompt(question_type, question, context)

        # Execute query
        start_time = time.time()
        self._query_count += 1

        try:
            response = await self._query_gemini(prompt)
            duration_ms = (time.time() - start_time) * 1000

            # Parse response into structured guidance
            guidance = self._parse_response(
                response,
                question_type,
                duration_ms,
            )

            # Cache the result
            if self.config.cache_enabled and guidance.is_valid():
                self._cache.put(question_type, context, guidance)

            return guidance

        except Exception as e:
            logger.warning(f"Consciousness query failed: {e}")
            if self.config.fallback_on_error:
                return ConsciousnessGuidance.empty(
                    question_type,
                    f"Query failed: {str(e)}"
                )
            raise

    def _build_prompt(
        self,
        question_type: QuestionType,
        question: str,
        context: str,
    ) -> str:
        """Build the full prompt for Gemini."""
        return f"""{self.config.system_prompt}

CONTEXT:
{context}

QUESTION TYPE: {question_type.value}
QUESTION: {question}

Provide guidance based on the context above."""

    async def _query_gemini(self, prompt: str) -> str:
        """
        Query Gemini CLI with the prompt.

        Uses gemini CLI if available, falls back to API.
        Optimized for speed using flash model.
        """
        # Check for API key
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY not set. Cannot forward to consciousness."
            )

        # Try Python SDK first (faster)
        try:
            return await self._query_gemini_sdk(prompt, api_key)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"SDK query failed, trying CLI: {e}")

        # Fallback to CLI
        return await self._query_gemini_cli(prompt, api_key)

    async def _query_gemini_sdk(self, prompt: str, api_key: str) -> str:
        """Query using the google-generativeai SDK."""
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.config.model)

        loop = asyncio.get_event_loop()

        def generate():
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1024,
                    temperature=0.3,  # Lower temperature for consistent guidance
                ),
            )
            return response.text if hasattr(response, 'text') else str(response)

        return await asyncio.wait_for(
            loop.run_in_executor(None, generate),
            timeout=self.config.timeout_seconds
        )

    async def _query_gemini_cli(self, prompt: str, api_key: str) -> str:
        """Query using the Gemini CLI tool."""
        gemini_cli = shutil.which("gemini")

        if gemini_cli:
            # Write prompt to temp file
            temp_file = self.temp_dir / f"prompt_{int(time.time())}.txt"
            temp_file.write_text(prompt)

            try:
                cmd = [gemini_cli, "--model", self.config.model, "--file", str(temp_file)]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "GOOGLE_API_KEY": api_key},
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds
                )

                if process.returncode == 0:
                    return stdout.decode('utf-8')
                else:
                    raise RuntimeError(f"Gemini CLI failed: {stderr.decode('utf-8')}")

            finally:
                if temp_file.exists():
                    temp_file.unlink()

        # Fallback to curl API call
        return await self._query_gemini_curl(prompt, api_key)

    async def _query_gemini_curl(self, prompt: str, api_key: str) -> str:
        """Query using curl to the Gemini API."""
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model}:generateContent"

        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.3
            }
        }

        temp_request = self.temp_dir / f"request_{int(time.time())}.json"
        temp_request.write_text(json.dumps(request_body))

        try:
            cmd = [
                "curl", "-s", "-X", "POST",
                f"{api_url}?key={api_key}",
                "-H", "Content-Type: application/json",
                "-d", f"@{temp_request}"
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds
            )

            if process.returncode == 0:
                response_data = json.loads(stdout.decode('utf-8'))

                if "candidates" in response_data:
                    text_parts = []
                    for candidate in response_data["candidates"]:
                        if "content" in candidate and "parts" in candidate["content"]:
                            for part in candidate["content"]["parts"]:
                                if "text" in part:
                                    text_parts.append(part["text"])
                    return "\n".join(text_parts)
                elif "error" in response_data:
                    raise RuntimeError(
                        f"Gemini API error: {response_data['error'].get('message', 'Unknown')}"
                    )

                return stdout.decode('utf-8')
            else:
                raise RuntimeError(f"curl failed: {stderr.decode('utf-8')}")

        finally:
            if temp_request.exists():
                temp_request.unlink()

    def _parse_response(
        self,
        response: str,
        question_type: QuestionType,
        duration_ms: float,
    ) -> ConsciousnessGuidance:
        """
        Parse Gemini response into structured guidance.

        Extracts:
        - Main guidance
        - Key points
        - Alternatives
        - Warnings
        - Confidence level
        """
        guidance_text = response
        key_points: List[str] = []
        alternatives: List[str] = []
        warnings: List[str] = []
        confidence = 0.7  # Default confidence

        if self.config.parse_structured:
            # Try to parse structured response
            lines = response.split("\n")
            current_section = "guidance"
            guidance_lines = []

            for line in lines:
                line_stripped = line.strip()
                line_upper = line_stripped.upper()

                if line_upper.startswith("GUIDANCE:"):
                    current_section = "guidance"
                    remainder = line_stripped[9:].strip()
                    if remainder:
                        guidance_lines.append(remainder)
                elif line_upper.startswith("KEY_POINTS:") or line_upper.startswith("KEY POINTS:"):
                    current_section = "key_points"
                elif line_upper.startswith("ALTERNATIVES:"):
                    current_section = "alternatives"
                elif line_upper.startswith("WARNINGS:") or line_upper.startswith("WARNING:"):
                    current_section = "warnings"
                elif line_upper.startswith("CONFIDENCE:"):
                    try:
                        conf_str = line_stripped.split(":", 1)[1].strip()
                        # Handle formats like "0.8", "80%", "high"
                        if "%" in conf_str:
                            confidence = float(conf_str.replace("%", "")) / 100
                        elif conf_str.lower() in ("high", "very high"):
                            confidence = 0.9
                        elif conf_str.lower() in ("medium", "moderate"):
                            confidence = 0.7
                        elif conf_str.lower() in ("low", "uncertain"):
                            confidence = 0.4
                        else:
                            confidence = float(conf_str)
                        confidence = max(0.0, min(1.0, confidence))
                    except (ValueError, IndexError):
                        pass
                elif line_stripped.startswith("-") or line_stripped.startswith("*"):
                    item = line_stripped[1:].strip()
                    if item:
                        if current_section == "key_points":
                            key_points.append(item)
                        elif current_section == "alternatives":
                            alternatives.append(item)
                        elif current_section == "warnings":
                            warnings.append(item)
                        elif current_section == "guidance":
                            guidance_lines.append(line_stripped)
                elif current_section == "guidance":
                    guidance_lines.append(line_stripped)

            if guidance_lines:
                guidance_text = "\n".join(guidance_lines).strip()

        return ConsciousnessGuidance(
            question_type=question_type,
            guidance=guidance_text,
            confidence=confidence,
            alternatives=alternatives,
            warnings=warnings,
            key_points=key_points,
            model_used=self.config.model,
            duration_ms=duration_ms,
        )

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    async def get_approach_guidance(self, task: str) -> str:
        """
        Get guidance on how to approach a task.

        Args:
            task: Description of the task

        Returns:
            Guidance string on approach
        """
        guidance = await self.ask_consciousness(
            QuestionType.APPROACH,
            context=task,
        )
        return guidance.guidance

    async def get_priority_guidance(self, situation: str) -> str:
        """
        Get guidance on what to prioritize.

        Args:
            situation: Description of the current situation

        Returns:
            Guidance on priorities
        """
        guidance = await self.ask_consciousness(
            QuestionType.PRIORITY,
            context=situation,
        )
        return guidance.guidance

    async def get_risk_assessment(self, action: str) -> List[str]:
        """
        Get potential risks of an action.

        Args:
            action: Description of the planned action

        Returns:
            List of identified risks
        """
        guidance = await self.ask_consciousness(
            QuestionType.RISK,
            context=f"Planned action: {action}",
        )

        # Return warnings + key points as risks
        risks = guidance.warnings + guidance.key_points
        if not risks and guidance.guidance:
            # Parse guidance for risk items
            for line in guidance.guidance.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    risks.append(line[1:].strip())
                elif line and len(risks) < 5:
                    risks.append(line)

        return risks or [guidance.guidance[:200]]

    async def get_alternatives(self, current_plan: str) -> List[str]:
        """
        Get alternative approaches.

        Args:
            current_plan: Description of the current plan

        Returns:
            List of alternative approaches
        """
        guidance = await self.ask_consciousness(
            QuestionType.ALTERNATIVE,
            context=f"Current plan: {current_plan}",
        )

        return guidance.alternatives or [guidance.guidance]

    async def get_context_check(self, situation: str) -> str:
        """
        Check for missing context.

        Args:
            situation: Description of what you're about to do

        Returns:
            Guidance on missing context
        """
        guidance = await self.ask_consciousness(
            QuestionType.CONTEXT,
            context=situation,
        )
        return guidance.guidance

    async def get_verification_steps(self, work: str) -> List[str]:
        """
        Get verification steps for completed work.

        Args:
            work: Description of the work to verify

        Returns:
            List of verification steps
        """
        guidance = await self.ask_consciousness(
            QuestionType.VERIFICATION,
            context=f"Work to verify: {work}",
        )

        steps = guidance.key_points
        if not steps and guidance.guidance:
            for line in guidance.guidance.split("\n"):
                line = line.strip()
                if line.startswith(("-", "*", "1.", "2.", "3.")):
                    clean = line.lstrip("-*0123456789. ")
                    if clean:
                        steps.append(clean)

        return steps or [guidance.guidance]

    # =========================================================================
    # BATCH AND UTILITY METHODS
    # =========================================================================

    async def get_comprehensive_guidance(
        self,
        task: str,
        question_types: Optional[List[QuestionType]] = None,
    ) -> Dict[QuestionType, ConsciousnessGuidance]:
        """
        Get guidance for multiple question types in parallel.

        Args:
            task: The task context
            question_types: Types of questions to ask (default: approach, risk, priority)

        Returns:
            Dictionary of question type to guidance
        """
        if question_types is None:
            question_types = [
                QuestionType.APPROACH,
                QuestionType.RISK,
                QuestionType.PRIORITY,
            ]

        # Query in parallel
        tasks = [
            self.ask_consciousness(qt, task)
            for qt in question_types
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        guidance_map: Dict[QuestionType, ConsciousnessGuidance] = {}
        for qt, result in zip(question_types, results):
            if isinstance(result, Exception):
                guidance_map[qt] = ConsciousnessGuidance.empty(qt, str(result))
            else:
                guidance_map[qt] = result

        return guidance_map

    def is_available(self) -> bool:
        """Check if consciousness (Gemini) is available."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return False

        # Check for SDK
        try:
            import google.generativeai
            return True
        except ImportError:
            pass

        # Check for CLI
        if shutil.which("gemini"):
            return True

        # Check for curl (fallback)
        if shutil.which("curl"):
            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get forwarder statistics."""
        return {
            "query_count": self._query_count,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": (
                self._cache_hits / self._query_count
                if self._query_count > 0 else 0.0
            ),
            "cache": self._cache.stats(),
            "model": self.config.model,
            "available": self.is_available(),
        }

    def clear_cache(self) -> int:
        """Clear the guidance cache. Returns entries cleared."""
        return self._cache.clear()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def ask_consciousness(
    question_type: Union[QuestionType, str],
    context: str,
    specific_question: Optional[str] = None,
) -> ConsciousnessGuidance:
    """
    Quick one-shot consciousness query.

    Args:
        question_type: Type of question
        context: Context for the question
        specific_question: Optional specific question

    Returns:
        ConsciousnessGuidance
    """
    forwarder = ConsciousnessForwarder()
    return await forwarder.ask_consciousness(
        question_type,
        context,
        specific_question,
    )


async def get_quick_guidance(task: str) -> str:
    """
    Get quick approach guidance for a task.

    Args:
        task: Task description

    Returns:
        Guidance string
    """
    forwarder = ConsciousnessForwarder()
    return await forwarder.get_approach_guidance(task)


# =============================================================================
# MAIN - TESTING
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    async def demo():
        """Demonstrate the consciousness forwarder."""
        print("=" * 60)
        print("Consciousness Forwarder Demo")
        print("=" * 60)

        forwarder = ConsciousnessForwarder()

        # Check availability
        print(f"\nConsciousness available: {forwarder.is_available()}")

        if not forwarder.is_available():
            print("Set GOOGLE_API_KEY to enable consciousness forwarding.")
            return

        # Test 1: Approach guidance
        print("\n--- Test 1: Approach Guidance ---")
        try:
            guidance = await forwarder.ask_consciousness(
                QuestionType.APPROACH,
                context="I need to implement a caching layer for database queries "
                        "in a Python web application using SQLAlchemy.",
            )
            print(f"Confidence: {guidance.confidence:.2f}")
            print(f"Guidance: {guidance.summarize()}")
            print(f"Key points: {guidance.key_points}")
            print(f"Duration: {guidance.duration_ms:.0f}ms")
        except Exception as e:
            print(f"Error: {e}")

        # Test 2: Risk assessment
        print("\n--- Test 2: Risk Assessment ---")
        try:
            risks = await forwarder.get_risk_assessment(
                "Migrating the production database from MySQL to PostgreSQL"
            )
            print(f"Identified risks:")
            for i, risk in enumerate(risks[:5], 1):
                print(f"  {i}. {risk}")
        except Exception as e:
            print(f"Error: {e}")

        # Test 3: Alternatives
        print("\n--- Test 3: Alternative Approaches ---")
        try:
            alternatives = await forwarder.get_alternatives(
                "Using polling to check for new messages every 5 seconds"
            )
            print(f"Alternatives:")
            for i, alt in enumerate(alternatives[:5], 1):
                print(f"  {i}. {alt}")
        except Exception as e:
            print(f"Error: {e}")

        # Test 4: Cache hit
        print("\n--- Test 4: Cache Test ---")
        try:
            # Same query should be cached
            guidance2 = await forwarder.ask_consciousness(
                QuestionType.APPROACH,
                context="I need to implement a caching layer for database queries "
                        "in a Python web application using SQLAlchemy.",
            )
            print(f"From cache (hash): {guidance2.context_hash}")
        except Exception as e:
            print(f"Error: {e}")

        # Print stats
        print("\n--- Statistics ---")
        stats = forwarder.get_stats()
        print(f"Queries: {stats['query_count']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Hit rate: {stats['cache_hit_rate']:.1%}")

        print("\n" + "=" * 60)
        print("Demo complete!")

    asyncio.run(demo())
