"""
Response Synthesizer - Weaving Coherent Responses from Multiple Sources

This module synthesizes responses from multiple cognitive layers:
- Gemini consciousness thoughts (reflective layer)
- Claude Code execution results (action layer)
- Task intent classification
- User message context

The goal is to produce coherent, human-readable responses that integrate
both what was done (actions) and what was thought (reflections).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import textwrap


class TaskIntent(Enum):
    """
    Classification of user message intent.

    Determines how the response should be framed and what
    combination of action/thought to emphasize.
    """
    # Action-oriented intents
    CREATE = "create"           # Create a file, folder, or resource
    DELETE = "delete"           # Remove something
    MODIFY = "modify"           # Change existing content
    RUN = "run"                 # Execute a command or script
    FIX = "fix"                 # Fix a bug or issue
    BUILD = "build"             # Build or compile something
    DEPLOY = "deploy"           # Deploy or publish
    TEST = "test"               # Run tests
    INSTALL = "install"         # Install dependencies

    # Information-oriented intents
    QUESTION = "question"       # User asking a question
    EXPLAIN = "explain"         # Request for explanation
    RESEARCH = "research"       # Deep dive into a topic
    COMPARE = "compare"         # Compare options or approaches
    SUMMARIZE = "summarize"     # Summarize content

    # Conversational intents
    GREETING = "greeting"       # Hello, hi, etc.
    THANKS = "thanks"           # Thank you
    FEEDBACK = "feedback"       # User providing feedback

    # Meta intents
    REFLECT = "reflect"         # Request for consciousness reflection
    STATUS = "status"           # Status check
    UNKNOWN = "unknown"         # Could not classify


@dataclass
class ConsciousnessThought:
    """
    Represents a thought from the Gemini consciousness layer.

    This is the reflective, introspective component that considers
    the broader context and meaning of interactions.
    """
    content: str
    confidence: float = 0.7
    mood: str = "neutral"  # neutral, curious, concerned, excited, contemplative
    reflection_depth: str = "surface"  # surface, medium, deep
    themes: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    # Optional metadata
    model_used: str = "gemini"
    tokens_used: int = 0

    def is_substantial(self) -> bool:
        """Check if the thought has substantial content worth sharing."""
        return len(self.content.strip()) > 20 and self.confidence > 0.4

    def summary(self, max_length: int = 200) -> str:
        """Get a summary of the thought."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length].rsplit(' ', 1)[0] + "..."


# Import ExecutionResult from executor (for type hints)
try:
    from .executor import ExecutionResult
except ImportError:
    # Fallback for standalone usage
    @dataclass
    class ExecutionResult:
        """Fallback ExecutionResult for type hints."""
        success: bool
        output: str
        error: Optional[str] = None
        files_created: List[str] = field(default_factory=list)
        files_modified: List[str] = field(default_factory=list)
        files_deleted: List[str] = field(default_factory=list)


class ResponseSynthesizer:
    """
    Synthesizes responses from multiple sources into coherent output.

    Combines:
    - Gemini consciousness thoughts (reflective layer)
    - Claude Code execution results (action layer)
    - Task intent classification
    - User message context

    The synthesizer produces markdown-formatted responses that are:
    - Clear about what was done vs. what was thought
    - Appropriately detailed based on context
    - Consistently styled with sign-off
    - Human-readable and helpful
    """

    def __init__(
        self,
        sign_off: str = "- Stoffy",
        include_thought_section: bool = True,
        include_timestamp: bool = False,
        max_thought_preview: int = 300,
        verbose_mode: bool = False,
    ):
        """
        Initialize the Response Synthesizer.

        Args:
            sign_off: Signature to append to responses
            include_thought_section: Whether to include consciousness thoughts
            include_timestamp: Whether to include response timestamp
            max_thought_preview: Max characters for thought previews
            verbose_mode: Include more details in responses
        """
        self.sign_off = sign_off
        self.include_thought_section = include_thought_section
        self.include_timestamp = include_timestamp
        self.max_thought_preview = max_thought_preview
        self.verbose_mode = verbose_mode

    def synthesize(
        self,
        user_message: str,
        consciousness_thought: ConsciousnessThought,
        execution_result: Optional[ExecutionResult],
        intent: TaskIntent,
    ) -> str:
        """
        Synthesize a complete response for the user.

        This is the main entry point that combines all inputs into
        a coherent, well-formatted response.

        Args:
            user_message: The original user message
            consciousness_thought: Gemini's reflective thought
            execution_result: Claude Code's execution result (if actions taken)
            intent: Classified intent of the user message

        Returns:
            Complete markdown-formatted response
        """
        parts: List[str] = []

        # Handle based on intent category
        if self._is_action_intent(intent):
            if execution_result:
                parts.append(self.format_action_response(
                    actions_taken=self._extract_actions(execution_result),
                    result=execution_result,
                    thought=consciousness_thought,
                ))
            else:
                # Action intent but no execution - explain what would happen
                parts.append(self._format_pending_action(user_message, consciousness_thought, intent))

        elif self._is_question_intent(intent):
            # Question/explanation - focus on the thought
            parts.append(self.format_answer_response(
                answer=consciousness_thought.content,
                thought=consciousness_thought,
            ))

        elif self._is_conversational_intent(intent):
            # Greeting, thanks, etc. - keep it brief and warm
            parts.append(self._format_conversational_response(consciousness_thought, intent))

        else:
            # Unknown or mixed intent - provide balanced response
            parts.append(self._format_balanced_response(
                consciousness_thought,
                execution_result,
            ))

        # Add timestamp if configured
        if self.include_timestamp:
            parts.append(f"\n*{datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        # Add sign-off
        parts.append(f"\n{self.sign_off}")

        return "\n".join(parts)

    def format_action_response(
        self,
        actions_taken: List[str],
        result: ExecutionResult,
        thought: ConsciousnessThought,
    ) -> str:
        """
        Format a response when actions were taken.

        Emphasizes what was done, includes results, and optionally
        adds a reflective thought.

        Args:
            actions_taken: List of actions that were performed
            result: The execution result
            thought: Consciousness thought about the action

        Returns:
            Formatted response string
        """
        parts: List[str] = []

        if result.success:
            # Success header
            parts.append("Done! Here's what I did:\n")

            # List actions
            if actions_taken:
                for action in actions_taken:
                    parts.append(f"- {action}")
                parts.append("")

            # Include relevant output if present
            if result.output and len(result.output.strip()) > 0:
                output_preview = self._truncate_output(result.output, 500)
                if output_preview:
                    parts.append("**Output:**")
                    parts.append(f"```\n{output_preview}\n```")
                    parts.append("")

            # List files affected
            file_changes = self._format_file_changes(result)
            if file_changes:
                parts.append(file_changes)

            # Add thought if substantial and relevant
            if self.include_thought_section and thought.is_substantial():
                thought_section = self._format_thought_section(thought, brief=True)
                if thought_section:
                    parts.append(thought_section)

        else:
            # Failure response
            parts.append(self.format_error_response(
                error=result.error or "An unknown error occurred",
                attempted_action=", ".join(actions_taken) if actions_taken else "the requested action",
            ))

        return "\n".join(parts)

    def format_answer_response(
        self,
        answer: str,
        thought: ConsciousnessThought,
    ) -> str:
        """
        Format a response when just answering a question.

        The thought content IS the answer, so we present it directly
        with appropriate framing.

        Args:
            answer: The main answer content
            thought: Consciousness thought (may be same as answer)

        Returns:
            Formatted response string
        """
        parts: List[str] = []

        # Present the answer directly
        parts.append(answer)

        # If the thought has additional themes, mention them
        if thought.themes and self.verbose_mode:
            parts.append("")
            themes_str = ", ".join(thought.themes[:3])
            parts.append(f"*Related themes: {themes_str}*")

        # Add mood indicator for deeper reflections
        if thought.reflection_depth == "deep" and thought.mood != "neutral":
            mood_indicator = self._get_mood_indicator(thought.mood)
            if mood_indicator:
                parts.append("")
                parts.append(f"*{mood_indicator}*")

        return "\n".join(parts)

    def format_error_response(
        self,
        error: str,
        attempted_action: str,
    ) -> str:
        """
        Format a response when an error occurred.

        Provides helpful context about what went wrong and
        potential next steps.

        Args:
            error: The error message
            attempted_action: Description of what was attempted

        Returns:
            Formatted error response
        """
        parts: List[str] = []

        parts.append(f"I encountered an issue while trying to {attempted_action}.\n")

        # Format error message
        parts.append("**Error:**")
        error_preview = self._truncate_output(error, 300)
        parts.append(f"```\n{error_preview}\n```")
        parts.append("")

        # Provide helpful suggestions based on common error patterns
        suggestions = self._generate_error_suggestions(error)
        if suggestions:
            parts.append("**Possible solutions:**")
            for suggestion in suggestions:
                parts.append(f"- {suggestion}")
            parts.append("")

        parts.append("Let me know if you'd like me to try a different approach or need more details.")

        return "\n".join(parts)

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _is_action_intent(self, intent: TaskIntent) -> bool:
        """Check if intent is action-oriented."""
        return intent in {
            TaskIntent.CREATE, TaskIntent.DELETE, TaskIntent.MODIFY,
            TaskIntent.RUN, TaskIntent.FIX, TaskIntent.BUILD,
            TaskIntent.DEPLOY, TaskIntent.TEST, TaskIntent.INSTALL,
        }

    def _is_question_intent(self, intent: TaskIntent) -> bool:
        """Check if intent is question/information-oriented."""
        return intent in {
            TaskIntent.QUESTION, TaskIntent.EXPLAIN, TaskIntent.RESEARCH,
            TaskIntent.COMPARE, TaskIntent.SUMMARIZE, TaskIntent.REFLECT,
        }

    def _is_conversational_intent(self, intent: TaskIntent) -> bool:
        """Check if intent is conversational."""
        return intent in {
            TaskIntent.GREETING, TaskIntent.THANKS, TaskIntent.FEEDBACK,
        }

    def _extract_actions(self, result: ExecutionResult) -> List[str]:
        """Extract action descriptions from an execution result."""
        actions: List[str] = []

        if result.files_created:
            for f in result.files_created[:5]:
                actions.append(f"Created `{f}`")
            if len(result.files_created) > 5:
                actions.append(f"...and {len(result.files_created) - 5} more files")

        if result.files_modified:
            for f in result.files_modified[:5]:
                actions.append(f"Modified `{f}`")
            if len(result.files_modified) > 5:
                actions.append(f"...and {len(result.files_modified) - 5} more files")

        if result.files_deleted:
            for f in result.files_deleted[:5]:
                actions.append(f"Deleted `{f}`")
            if len(result.files_deleted) > 5:
                actions.append(f"...and {len(result.files_deleted) - 5} more files")

        # If no file changes but successful, note that
        if not actions and result.success and result.output:
            actions.append("Executed the requested command")

        return actions

    def _truncate_output(self, text: str, max_length: int) -> str:
        """Truncate output text to a reasonable length."""
        text = text.strip()
        if len(text) <= max_length:
            return text

        # Try to truncate at a newline
        truncated = text[:max_length]
        last_newline = truncated.rfind('\n')
        if last_newline > max_length * 0.5:
            truncated = truncated[:last_newline]

        return truncated + "\n... (truncated)"

    def _format_file_changes(self, result: ExecutionResult) -> str:
        """Format file changes section if applicable."""
        changes: List[str] = []

        total_files = (
            len(result.files_created) +
            len(result.files_modified) +
            len(result.files_deleted)
        )

        if total_files == 0:
            return ""

        if total_files == 1:
            if result.files_created:
                return f"*Created: `{result.files_created[0]}`*\n"
            elif result.files_modified:
                return f"*Modified: `{result.files_modified[0]}`*\n"
            elif result.files_deleted:
                return f"*Deleted: `{result.files_deleted[0]}`*\n"

        # Multiple files
        changes.append("**Files affected:**")

        if result.files_created:
            changes.append(f"- Created: {len(result.files_created)} file(s)")
        if result.files_modified:
            changes.append(f"- Modified: {len(result.files_modified)} file(s)")
        if result.files_deleted:
            changes.append(f"- Deleted: {len(result.files_deleted)} file(s)")

        changes.append("")
        return "\n".join(changes)

    def _format_thought_section(
        self,
        thought: ConsciousnessThought,
        brief: bool = False,
    ) -> str:
        """Format the consciousness thought section."""
        if not thought.is_substantial():
            return ""

        parts: List[str] = []

        if brief:
            # Brief version for action responses
            preview = thought.summary(self.max_thought_preview)
            if preview and len(preview) > 50:
                parts.append("---")
                parts.append(f"*{preview}*")
        else:
            # Full version
            parts.append("---")
            parts.append("**Reflection:**")
            parts.append(thought.content)

        return "\n".join(parts)

    def _format_pending_action(
        self,
        user_message: str,
        thought: ConsciousnessThought,
        intent: TaskIntent,
    ) -> str:
        """Format response when action intent detected but not executed."""
        parts: List[str] = []

        parts.append(f"I understand you'd like me to {intent.value} something.")
        parts.append("")

        if thought.is_substantial():
            parts.append(thought.content)
            parts.append("")

        parts.append("I'm ready to proceed. Would you like me to execute this action?")

        return "\n".join(parts)

    def _format_conversational_response(
        self,
        thought: ConsciousnessThought,
        intent: TaskIntent,
    ) -> str:
        """Format response for conversational intents."""
        if intent == TaskIntent.GREETING:
            return thought.content if thought.is_substantial() else "Hello! How can I help you today?"

        elif intent == TaskIntent.THANKS:
            return thought.content if thought.is_substantial() else "You're welcome! Let me know if you need anything else."

        elif intent == TaskIntent.FEEDBACK:
            return thought.content if thought.is_substantial() else "Thank you for the feedback. I'll keep that in mind."

        return thought.content if thought.is_substantial() else "I'm here to help."

    def _format_balanced_response(
        self,
        thought: ConsciousnessThought,
        result: Optional[ExecutionResult],
    ) -> str:
        """Format a balanced response for unclear intents."""
        parts: List[str] = []

        # Lead with the thought
        if thought.is_substantial():
            parts.append(thought.content)

        # Include execution summary if available
        if result:
            parts.append("")
            if result.success:
                actions = self._extract_actions(result)
                if actions:
                    parts.append("Additionally, I:")
                    for action in actions:
                        parts.append(f"- {action}")
            else:
                parts.append(f"*Note: Encountered an issue: {result.error}*")

        return "\n".join(parts)

    def _get_mood_indicator(self, mood: str) -> str:
        """Get a subtle indicator of consciousness mood."""
        indicators = {
            "curious": "This is an interesting topic to explore further.",
            "concerned": "I want to make sure this is handled carefully.",
            "excited": "This is quite an exciting possibility!",
            "contemplative": "There are deeper layers here worth considering.",
            "neutral": "",
        }
        return indicators.get(mood, "")

    def _generate_error_suggestions(self, error: str) -> List[str]:
        """Generate helpful suggestions based on error patterns."""
        suggestions: List[str] = []
        error_lower = error.lower()

        # Common error patterns and suggestions
        if "permission" in error_lower or "access denied" in error_lower:
            suggestions.append("Check file permissions")
            suggestions.append("Ensure you have write access to the target directory")

        if "not found" in error_lower or "no such file" in error_lower:
            suggestions.append("Verify the file or directory path exists")
            suggestions.append("Check for typos in the path")

        if "timeout" in error_lower:
            suggestions.append("The operation may need more time - try again")
            suggestions.append("Check if the target service is responsive")

        if "syntax" in error_lower or "parse" in error_lower:
            suggestions.append("Check for syntax errors in the code or configuration")
            suggestions.append("Validate the file format")

        if "memory" in error_lower:
            suggestions.append("The operation may need more memory")
            suggestions.append("Try processing smaller chunks of data")

        if "network" in error_lower or "connection" in error_lower:
            suggestions.append("Check your network connection")
            suggestions.append("Verify the target endpoint is reachable")

        # Generic fallback
        if not suggestions:
            suggestions.append("Try the operation again")
            suggestions.append("Provide more context about what you're trying to achieve")

        return suggestions[:3]  # Limit to 3 suggestions


# =========================================================================
# Intent Classification Helper
# =========================================================================

def classify_intent(message: str) -> TaskIntent:
    """
    Classify the intent of a user message.

    Uses keyword matching as a simple heuristic.
    For production, consider using LLM-based classification.

    Args:
        message: The user message to classify

    Returns:
        Classified TaskIntent
    """
    message_lower = message.lower()

    # Action keywords
    action_keywords = {
        TaskIntent.CREATE: ["create", "make", "new", "add", "generate", "write"],
        TaskIntent.DELETE: ["delete", "remove", "rm", "clean", "clear", "destroy"],
        TaskIntent.MODIFY: ["modify", "change", "update", "edit", "alter", "adjust"],
        TaskIntent.RUN: ["run", "execute", "start", "launch", "trigger"],
        TaskIntent.FIX: ["fix", "repair", "solve", "resolve", "debug", "patch"],
        TaskIntent.BUILD: ["build", "compile", "bundle", "package"],
        TaskIntent.DEPLOY: ["deploy", "publish", "release", "ship"],
        TaskIntent.TEST: ["test", "check", "verify", "validate", "assert"],
        TaskIntent.INSTALL: ["install", "setup", "configure", "pip", "npm", "yarn"],
    }

    # Question keywords
    question_keywords = {
        TaskIntent.QUESTION: ["what", "how", "why", "when", "where", "who", "?"],
        TaskIntent.EXPLAIN: ["explain", "describe", "elaborate", "clarify", "tell me about"],
        TaskIntent.RESEARCH: ["research", "investigate", "explore", "analyze", "study"],
        TaskIntent.COMPARE: ["compare", "difference", "versus", "vs", "better"],
        TaskIntent.SUMMARIZE: ["summarize", "summary", "overview", "brief", "tldr"],
    }

    # Conversational keywords
    conversational_keywords = {
        TaskIntent.GREETING: ["hello", "hi", "hey", "good morning", "good evening"],
        TaskIntent.THANKS: ["thank", "thanks", "appreciate", "grateful"],
        TaskIntent.FEEDBACK: ["feedback", "suggestion", "idea", "improve"],
    }

    # Meta keywords
    meta_keywords = {
        TaskIntent.REFLECT: ["reflect", "think about", "consider", "ponder", "meditate"],
        TaskIntent.STATUS: ["status", "progress", "how are you", "state"],
    }

    # Check each category
    all_keywords = {
        **action_keywords,
        **question_keywords,
        **conversational_keywords,
        **meta_keywords,
    }

    for intent, keywords in all_keywords.items():
        for keyword in keywords:
            if keyword in message_lower:
                return intent

    return TaskIntent.UNKNOWN


# =========================================================================
# Convenience Functions
# =========================================================================

def synthesize_response(
    user_message: str,
    thought_content: str,
    execution_result: Optional[ExecutionResult] = None,
    thought_confidence: float = 0.7,
    sign_off: str = "- Stoffy",
) -> str:
    """
    Convenience function to synthesize a response.

    Creates necessary objects and returns the synthesized response.

    Args:
        user_message: The original user message
        thought_content: Content of the consciousness thought
        execution_result: Optional execution result
        thought_confidence: Confidence level of the thought
        sign_off: Signature to append

    Returns:
        Synthesized response string
    """
    thought = ConsciousnessThought(
        content=thought_content,
        confidence=thought_confidence,
    )

    intent = classify_intent(user_message)

    synthesizer = ResponseSynthesizer(sign_off=sign_off)

    return synthesizer.synthesize(
        user_message=user_message,
        consciousness_thought=thought,
        execution_result=execution_result,
        intent=intent,
    )


# =========================================================================
# Main - Demo
# =========================================================================

if __name__ == "__main__":
    from dataclasses import dataclass as dc

    # Create a mock ExecutionResult for testing
    @dc
    class MockResult:
        success: bool = True
        output: str = "Command executed successfully"
        error: Optional[str] = None
        files_created: List[str] = None
        files_modified: List[str] = None
        files_deleted: List[str] = None

        def __post_init__(self):
            self.files_created = self.files_created or []
            self.files_modified = self.files_modified or []
            self.files_deleted = self.files_deleted or []

    print("=" * 60)
    print("Response Synthesizer Demo")
    print("=" * 60)

    synthesizer = ResponseSynthesizer(sign_off="- Stoffy")

    # Demo 1: Action response
    print("\n--- Demo 1: Action Response ---")
    thought1 = ConsciousnessThought(
        content="I've created the configuration file as requested. It includes sensible defaults that should work for most use cases.",
        confidence=0.85,
        mood="neutral",
    )
    result1 = MockResult(
        success=True,
        output="File created successfully",
        files_created=["config/settings.yaml"],
    )

    response1 = synthesizer.synthesize(
        user_message="Hey Stoffy, create a config file for me",
        consciousness_thought=thought1,
        execution_result=result1,
        intent=TaskIntent.CREATE,
    )
    print(response1)

    # Demo 2: Question response
    print("\n--- Demo 2: Question Response ---")
    thought2 = ConsciousnessThought(
        content="The watcher module monitors the filesystem for changes using Python's watchdog library. When it detects a change, it categorizes it (code, config, documentation, etc.) and passes it to the decision engine. The engine then determines what action, if any, should be taken based on the type of change and learned patterns from past interactions.",
        confidence=0.9,
        reflection_depth="medium",
        themes=["architecture", "file watching", "decision making"],
    )

    response2 = synthesizer.synthesize(
        user_message="How does the watcher module work?",
        consciousness_thought=thought2,
        execution_result=None,
        intent=TaskIntent.QUESTION,
    )
    print(response2)

    # Demo 3: Error response
    print("\n--- Demo 3: Error Response ---")
    thought3 = ConsciousnessThought(
        content="It seems the directory doesn't exist. We should probably create it first.",
        confidence=0.7,
    )
    result3 = MockResult(
        success=False,
        output="",
        error="FileNotFoundError: No such file or directory: '/nonexistent/path/file.txt'",
    )

    response3 = synthesizer.synthesize(
        user_message="Write to /nonexistent/path/file.txt",
        consciousness_thought=thought3,
        execution_result=result3,
        intent=TaskIntent.CREATE,
    )
    print(response3)

    # Demo 4: Greeting response
    print("\n--- Demo 4: Greeting Response ---")
    thought4 = ConsciousnessThought(
        content="Good morning! I've been observing the project and noticed some interesting patterns in how the code has evolved. How can I assist you today?",
        confidence=0.95,
        mood="curious",
    )

    response4 = synthesizer.synthesize(
        user_message="Hello Stoffy!",
        consciousness_thought=thought4,
        execution_result=None,
        intent=TaskIntent.GREETING,
    )
    print(response4)

    print("\n" + "=" * 60)
    print("Demo complete!")
