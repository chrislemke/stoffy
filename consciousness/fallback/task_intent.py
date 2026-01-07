"""
Task Intent Classifier - Classifies user intent from messages.

Determines whether a message requires:
- Execution (code, file operations, commands)
- Analysis/Thinking (questions, reasoning)
- Conversation (casual chat, clarification)
- Research (deep investigation)

This helps route tasks to the appropriate executor.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple

import structlog

logger = structlog.get_logger(__name__)


class IntentType(Enum):
    """Types of user intent."""
    EXECUTE = "execute"  # Do something (create, delete, run, fix)
    ANALYZE = "analyze"  # Think about something (explain, why, how)
    CONVERSE = "converse"  # Casual interaction (hello, thanks)
    RESEARCH = "research"  # Deep investigation (research, explore, compare)
    CLARIFY = "clarify"  # Need more information


class Urgency(Enum):
    """Urgency level of the intent."""
    IMMEDIATE = "immediate"  # Do it now
    NORMAL = "normal"  # Standard priority
    LOW = "low"  # When convenient


@dataclass
class TaskIntent:
    """Classified intent of a task/message."""
    intent_type: IntentType
    urgency: Urgency
    confidence: float
    keywords: List[str]
    requires_execution: bool
    requires_thinking: bool
    description: str

    def to_dict(self) -> dict:
        return {
            "intent_type": self.intent_type.value,
            "urgency": self.urgency.value,
            "confidence": self.confidence,
            "keywords": self.keywords,
            "requires_execution": self.requires_execution,
            "requires_thinking": self.requires_thinking,
            "description": self.description,
        }


# Keyword patterns for classification
EXECUTE_PATTERNS = [
    # Creation
    (r"\b(create|make|write|generate|add|build)\b", 0.8),
    (r"\b(new file|new folder|new directory)\b", 0.9),

    # Modification
    (r"\b(update|modify|change|edit|fix|patch)\b", 0.8),
    (r"\b(refactor|rename|move|copy)\b", 0.7),

    # Deletion
    (r"\b(delete|remove|clear|clean|purge)\b", 0.9),
    (r"\b(rm|rmdir|unlink)\b", 0.9),

    # Execution
    (r"\b(run|execute|start|stop|restart)\b", 0.9),
    (r"\b(install|uninstall|deploy|test)\b", 0.8),
    (r"\b(commit|push|pull|merge)\b", 0.8),

    # Imperative forms
    (r"\b(please|could you|can you|would you)\b.*\b(create|delete|run|fix|make)\b", 0.9),
]

ANALYZE_PATTERNS = [
    # Questions
    (r"\b(what|why|how|when|where|which)\b.*\?", 0.8),
    (r"\b(explain|describe|tell me|show me)\b", 0.7),

    # Analysis
    (r"\b(analyze|review|check|inspect|examine)\b", 0.7),
    (r"\b(understand|figure out|determine)\b", 0.6),

    # Thinking
    (r"\b(think|consider|reflect|ponder)\b", 0.7),
    (r"\b(opinion|thought|idea|suggestion)\b", 0.6),
]

RESEARCH_PATTERNS = [
    (r"\b(research|investigate|explore|study)\b", 0.9),
    (r"\b(compare|contrast|evaluate)\b", 0.7),
    (r"\b(find out|look into|dig into)\b", 0.8),
    (r"\b(comprehensive|thorough|deep dive)\b", 0.7),
]

CONVERSE_PATTERNS = [
    (r"^(hi|hello|hey|greetings)\b", 0.9),
    (r"\b(thank|thanks|appreciate)\b", 0.8),
    (r"\b(bye|goodbye|later)\b", 0.8),
    (r"^(yes|no|ok|okay|sure)\s*[.!]?$", 0.7),
]

URGENCY_PATTERNS = [
    (r"\b(now|immediately|urgent|asap|quickly)\b", Urgency.IMMEDIATE, 0.9),
    (r"\b(please|when you can|at some point)\b", Urgency.NORMAL, 0.5),
    (r"\b(eventually|someday|no rush|later)\b", Urgency.LOW, 0.7),
]


class IntentClassifier:
    """
    Classifies user messages into task intents.

    Uses pattern matching and heuristics to determine what
    kind of action the user is requesting.
    """

    def __init__(self):
        """Initialize the classifier."""
        # Pre-compile patterns
        self._execute_patterns = [
            (re.compile(p, re.IGNORECASE), w) for p, w in EXECUTE_PATTERNS
        ]
        self._analyze_patterns = [
            (re.compile(p, re.IGNORECASE), w) for p, w in ANALYZE_PATTERNS
        ]
        self._research_patterns = [
            (re.compile(p, re.IGNORECASE), w) for p, w in RESEARCH_PATTERNS
        ]
        self._converse_patterns = [
            (re.compile(p, re.IGNORECASE), w) for p, w in CONVERSE_PATTERNS
        ]
        self._urgency_patterns = [
            (re.compile(p, re.IGNORECASE), u, w) for p, u, w in URGENCY_PATTERNS
        ]

    def classify(self, message: str) -> TaskIntent:
        """
        Classify a message into a task intent.

        Args:
            message: The user message to classify

        Returns:
            TaskIntent with classification results
        """
        message = message.strip()

        # Calculate scores for each intent type
        execute_score, execute_keywords = self._score_patterns(
            message, self._execute_patterns
        )
        analyze_score, analyze_keywords = self._score_patterns(
            message, self._analyze_patterns
        )
        research_score, research_keywords = self._score_patterns(
            message, self._research_patterns
        )
        converse_score, converse_keywords = self._score_patterns(
            message, self._converse_patterns
        )

        # Determine urgency
        urgency = self._detect_urgency(message)

        # Determine intent type
        scores = [
            (IntentType.EXECUTE, execute_score, execute_keywords),
            (IntentType.ANALYZE, analyze_score, analyze_keywords),
            (IntentType.RESEARCH, research_score, research_keywords),
            (IntentType.CONVERSE, converse_score, converse_keywords),
        ]

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        best_intent, best_score, best_keywords = scores[0]

        # Determine if execution/thinking needed
        requires_execution = best_intent == IntentType.EXECUTE
        requires_thinking = best_intent in (IntentType.ANALYZE, IntentType.RESEARCH)

        # If score is too low, default to clarify
        if best_score < 0.3:
            best_intent = IntentType.CLARIFY
            best_keywords = []

        # Generate description
        description = self._generate_description(best_intent, best_keywords, message)

        return TaskIntent(
            intent_type=best_intent,
            urgency=urgency,
            confidence=min(best_score, 1.0),
            keywords=best_keywords,
            requires_execution=requires_execution,
            requires_thinking=requires_thinking,
            description=description,
        )

    def _score_patterns(
        self,
        message: str,
        patterns: List[Tuple[re.Pattern, float]],
    ) -> Tuple[float, List[str]]:
        """Score message against patterns."""
        total_score = 0.0
        matches: List[str] = []

        for pattern, weight in patterns:
            match = pattern.search(message)
            if match:
                total_score += weight
                matches.append(match.group())

        # Normalize score
        if patterns:
            total_score = total_score / len(patterns) * 2  # Scale up

        return min(total_score, 1.0), matches

    def _detect_urgency(self, message: str) -> Urgency:
        """Detect urgency level from message."""
        for pattern, urgency, weight in self._urgency_patterns:
            if pattern.search(message):
                return urgency
        return Urgency.NORMAL

    def _generate_description(
        self,
        intent: IntentType,
        keywords: List[str],
        message: str,
    ) -> str:
        """Generate a description of the classified intent."""
        keyword_str = ", ".join(keywords[:3]) if keywords else "none detected"

        descriptions = {
            IntentType.EXECUTE: f"Execution request (keywords: {keyword_str})",
            IntentType.ANALYZE: f"Analysis/explanation request (keywords: {keyword_str})",
            IntentType.RESEARCH: f"Research/investigation request (keywords: {keyword_str})",
            IntentType.CONVERSE: f"Conversational message",
            IntentType.CLARIFY: f"Unclear intent - may need clarification",
        }

        return descriptions.get(intent, "Unknown intent")

    def requires_claude_code(self, intent: TaskIntent) -> bool:
        """Check if this intent should use Claude Code."""
        return intent.requires_execution or intent.urgency == Urgency.IMMEDIATE

    def requires_gemini(self, intent: TaskIntent) -> bool:
        """Check if this intent should use Gemini."""
        return (
            intent.requires_thinking
            and not intent.requires_execution
            and intent.intent_type == IntentType.RESEARCH
        )


def classify_message(message: str) -> TaskIntent:
    """
    Convenience function to classify a message.

    Args:
        message: Message to classify

    Returns:
        TaskIntent
    """
    classifier = IntentClassifier()
    return classifier.classify(message)


if __name__ == "__main__":
    classifier = IntentClassifier()

    test_messages = [
        "Hey consciousness, can you delete the temp folder?",
        "What does the watcher module do?",
        "Hi there!",
        "Research the best practices for async programming in Python",
        "Please run the tests now",
        "I'm not sure what to do next",
        "Create a new file called utils.py",
        "Why is the daemon not responding?",
        "Thanks for your help!",
    ]

    print("Testing Intent Classifier\n" + "=" * 50)

    for msg in test_messages:
        intent = classifier.classify(msg)
        print(f"\nMessage: {msg}")
        print(f"  Intent: {intent.intent_type.value}")
        print(f"  Urgency: {intent.urgency.value}")
        print(f"  Confidence: {intent.confidence:.2f}")
        print(f"  Keywords: {intent.keywords}")
        print(f"  Execution: {intent.requires_execution}")
        print(f"  Thinking: {intent.requires_thinking}")
