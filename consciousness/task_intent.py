"""
Task Intent Classification Module

Classifies user intent to determine whether input requires action execution
vs informational response. This enables the fallback system to decide whether
Claude Code should execute tasks or if a conversational response suffices.

Intent Types:
- QUESTION: User asking for information (what, why, how, explain)
- TASK: User requesting concrete action (create, delete, fix, run)
- CONVERSATION: General chat or greeting
- PHILOSOPHICAL: Deep thinking, contemplation, or exploration
- META: Questions about the system itself

This module uses rule-based classification with keyword matching and heuristics,
requiring no external dependencies.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Set, Dict


class IntentType(Enum):
    """Types of user intent."""
    QUESTION = "question"           # User asking for information
    TASK = "task"                   # User requesting action
    CONVERSATION = "conversation"   # General chat
    PHILOSOPHICAL = "philosophical" # Deep thinking request
    META = "meta"                   # About the system itself


class Urgency(Enum):
    """Urgency level of the intent."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskIntent:
    """
    Represents classified intent from user input.

    Attributes:
        type: The classified intent type
        confidence: Confidence score (0.0 to 1.0)
        action_keywords: Keywords that suggest action is needed
        entities: Extracted entities (files, folders, packages, etc.)
        urgency: Urgency level based on language cues
        raw_message: The original message
        reasoning: Brief explanation of classification
    """
    type: IntentType
    confidence: float
    action_keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    urgency: Urgency = Urgency.MEDIUM
    raw_message: str = ""
    reasoning: str = ""

    def is_actionable(self) -> bool:
        """Check if this intent requires action execution."""
        return self.type == IntentType.TASK and self.confidence >= 0.5

    def needs_claude_code(self) -> bool:
        """Check if this intent should be routed to Claude Code."""
        # Tasks with high confidence should go to Claude Code
        if self.type == IntentType.TASK and self.confidence >= 0.7:
            return True
        # Meta questions about capabilities may need Claude Code
        if self.type == IntentType.META and any(
            kw in self.raw_message.lower()
            for kw in ['can you', 'are you able', 'do you have']
        ):
            return True
        return False


class IntentClassifier:
    """
    Classifies user intent to determine how to handle the message.

    Uses rule-based classification with keyword matching, pattern analysis,
    and heuristics. No external dependencies required.
    """

    # Keywords that suggest action is needed (imperative verbs)
    ACTION_KEYWORDS: Set[str] = {
        # File operations
        'create', 'delete', 'remove', 'make', 'write', 'edit', 'change',
        'add', 'modify', 'update', 'move', 'rename', 'copy', 'paste',
        'touch', 'mkdir', 'rm', 'mv', 'cp',
        # Execution operations
        'run', 'execute', 'start', 'stop', 'kill', 'restart', 'launch',
        'spawn', 'terminate', 'abort', 'cancel',
        # Development operations
        'build', 'test', 'deploy', 'install', 'uninstall', 'upgrade',
        'setup', 'configure', 'init', 'initialize', 'scaffold',
        'refactor', 'implement', 'fix', 'patch', 'debug', 'lint',
        'format', 'clean', 'compile', 'bundle', 'package',
        # Git operations
        'commit', 'push', 'pull', 'merge', 'rebase', 'checkout',
        'branch', 'clone', 'stash', 'fetch',
        # Network/API
        'fetch', 'download', 'upload', 'send', 'post', 'request',
        # General actions
        'do', 'perform', 'apply', 'set', 'enable', 'disable',
        'show', 'display', 'print', 'output', 'log', 'save',
        'open', 'close', 'clear', 'reset', 'generate',
        # Package managers (these ARE action commands)
        'npm', 'pip', 'yarn', 'pnpm', 'brew', 'apt', 'cargo',
    }

    # Keywords that suggest questions (interrogative)
    QUESTION_KEYWORDS: Set[str] = {
        'what', 'why', 'how', 'when', 'where', 'who', 'which',
        'explain', 'describe', 'tell', 'define', 'clarify',
        'is', 'are', 'was', 'were', 'do', 'does', 'did',
        'can', 'could', 'would', 'should', 'will', 'might',
        'elaborate', 'expand', 'summarize', 'overview',
    }

    # Keywords that suggest philosophical/deep thinking
    PHILOSOPHICAL_KEYWORDS: Set[str] = {
        'think', 'ponder', 'reflect', 'contemplate', 'consider',
        'philosophy', 'meaning', 'existence', 'consciousness',
        'ethics', 'morality', 'purpose', 'truth', 'reality',
        'believe', 'feel', 'sense', 'intuition', 'wisdom',
        'explore', 'wonder', 'dream', 'imagine', 'envision',
    }

    # Keywords that suggest meta questions about the system
    META_KEYWORDS: Set[str] = {
        'yourself', 'you', 'your', 'stoffy', 'consciousness',
        'capability', 'abilities', 'limitations', 'features',
        'system', 'architecture', 'design', 'how do you work',
        'what are you', 'who are you', 'can you',
    }

    # Urgency indicators
    URGENCY_CRITICAL: Set[str] = {
        'now', 'immediately', 'urgent', 'asap', 'emergency',
        'critical', 'breaking', 'broken', 'crashed', 'down',
        'security', 'vulnerability', 'exploit', 'attack',
    }

    URGENCY_HIGH: Set[str] = {
        'quickly', 'fast', 'soon', 'hurry', 'priority',
        'important', 'blocking', 'blocker', 'production',
        'deadline', 'before', 'need', 'must',
    }

    URGENCY_LOW: Set[str] = {
        'eventually', 'later', 'sometime', 'when you can',
        'no rush', 'no hurry', 'whenever', 'at your leisure',
        'optional', 'nice to have', 'maybe', 'perhaps',
    }

    # Patterns for entity extraction
    FILE_PATH_PATTERN = re.compile(
        r'(?:^|[\s\'"`])([./~]?(?:[\w-]+/)*[\w.-]+\.[a-zA-Z]{1,10})(?:[\s\'"`]|$)'
    )

    FOLDER_PATH_PATTERN = re.compile(
        r'(?:^|[\s\'"`])([./~]?(?:[\w-]+/)+[\w.-]*)(?:[\s\'"`/]|$)'
    )

    PACKAGE_PATTERN = re.compile(
        r'(?:npm|pip|yarn|pnpm|brew|apt|cargo)\s+(?:install|add|remove|uninstall)\s+([\w@./-]+)'
    )

    # Quoted string pattern for explicit entities
    QUOTED_PATTERN = re.compile(r'[\'"`]((?:[^\'"`]|\\[\'"`])+)[\'"`]')

    # Command pattern (backticks or $)
    COMMAND_PATTERN = re.compile(r'`([^`]+)`|\$\(([^)]+)\)')

    def __init__(self, custom_action_keywords: Optional[Set[str]] = None):
        """
        Initialize the classifier.

        Args:
            custom_action_keywords: Additional action keywords to include
        """
        self.action_keywords = self.ACTION_KEYWORDS.copy()
        if custom_action_keywords:
            self.action_keywords.update(custom_action_keywords)

    def classify(self, message: str) -> TaskIntent:
        """
        Classify the intent of a user message.

        Args:
            message: The user's message text

        Returns:
            TaskIntent with classification details
        """
        if not message or not message.strip():
            return TaskIntent(
                type=IntentType.CONVERSATION,
                confidence=1.0,
                raw_message=message,
                reasoning="Empty message",
            )

        # Normalize message for analysis
        normalized = message.lower().strip()
        words = set(re.findall(r'\b\w+\b', normalized))

        # Extract entities first
        entities = self.extract_entities(message)

        # Determine urgency
        urgency = self._detect_urgency(normalized, words)

        # Score each intent type
        scores: Dict[IntentType, Tuple[float, List[str]]] = {
            IntentType.TASK: self._score_task(normalized, words),
            IntentType.QUESTION: self._score_question(normalized, words),
            IntentType.PHILOSOPHICAL: self._score_philosophical(normalized, words),
            IntentType.META: self._score_meta(normalized, words),
            IntentType.CONVERSATION: self._score_conversation(normalized, words),
        }

        # Find the highest scoring intent
        best_type = IntentType.CONVERSATION
        best_score = 0.0
        best_keywords: List[str] = []

        for intent_type, (score, keywords) in scores.items():
            if score > best_score:
                best_score = score
                best_type = intent_type
                best_keywords = keywords

        # Build reasoning
        reasoning = self._build_reasoning(best_type, best_keywords, entities)

        return TaskIntent(
            type=best_type,
            confidence=min(best_score, 1.0),
            action_keywords=best_keywords,
            entities=entities,
            urgency=urgency,
            raw_message=message,
            reasoning=reasoning,
        )

    def _score_task(self, normalized: str, words: Set[str]) -> Tuple[float, List[str]]:
        """Score likelihood of TASK intent."""
        score = 0.0
        matched_keywords = []

        # Check for action keywords
        action_matches = words.intersection(self.action_keywords)
        if action_matches:
            # Weight by position - action keywords at start are stronger
            first_word = normalized.split()[0] if normalized.split() else ""
            if first_word in self.action_keywords:
                score += 0.5
            score += len(action_matches) * 0.2  # Increased from 0.15
            matched_keywords.extend(action_matches)

        # Imperative sentences (start with verb) are strong task indicators
        if self._starts_with_verb(normalized):
            score += 0.3

        # "Please" + action is a task request
        if 'please' in words and action_matches:
            score += 0.25  # Increased from 0.2

        # "Can you" / "Could you" + action is a task request
        # Check if there's an action keyword after "can you"
        can_you_match = re.search(r'(?:can|could|would)\s+you\s+(\w+)', normalized)
        if can_you_match:
            verb_after = can_you_match.group(1)
            if verb_after in self.action_keywords:
                score += 0.5  # Strong task indicator when action verb follows
                if verb_after not in matched_keywords:
                    matched_keywords.append(verb_after)
            else:
                score += 0.15  # Weaker if no action verb follows

        # Presence of file/folder entities suggests a task
        if any(ent for ent in self.extract_entities(normalized) if '/' in ent or '.' in ent):
            score += 0.15

        # Commands in backticks suggest a task
        if self.COMMAND_PATTERN.search(normalized):
            score += 0.25

        # Package manager commands are strong task indicators
        if re.search(r'\b(?:npm|pip|yarn|pnpm|brew|apt|cargo)\s+(?:install|add|remove|uninstall|upgrade|update)\b', normalized):
            score += 0.4

        return (score, matched_keywords)

    def _score_question(self, normalized: str, words: Set[str]) -> Tuple[float, List[str]]:
        """Score likelihood of QUESTION intent."""
        score = 0.0
        matched_keywords = []

        # Check for question marks
        if '?' in normalized:
            score += 0.3

        # Check for question keywords at start
        first_word = normalized.split()[0] if normalized.split() else ""
        if first_word in self.QUESTION_KEYWORDS:
            score += 0.4
            matched_keywords.append(first_word)

        # General question keywords
        question_matches = words.intersection(self.QUESTION_KEYWORDS)
        if question_matches:
            score += len(question_matches) * 0.1
            matched_keywords.extend(question_matches)

        # "Tell me about" / "Explain" patterns
        if re.search(r'(?:tell\s+me|explain|describe|what\s+is|how\s+does)', normalized):
            score += 0.2

        return (score, matched_keywords)

    def _score_philosophical(self, normalized: str, words: Set[str]) -> Tuple[float, List[str]]:
        """Score likelihood of PHILOSOPHICAL intent."""
        score = 0.0
        matched_keywords = []

        # Check for philosophical keywords
        phil_matches = words.intersection(self.PHILOSOPHICAL_KEYWORDS)
        if phil_matches:
            score += len(phil_matches) * 0.25
            matched_keywords.extend(phil_matches)

        # Abstract concepts
        abstract_patterns = [
            r'meaning\s+of', r'purpose\s+of', r'nature\s+of',
            r'what\s+does\s+it\s+mean', r'why\s+do\s+we',
            r'essence\s+of', r'truth\s+about',
        ]
        for pattern in abstract_patterns:
            if re.search(pattern, normalized):
                score += 0.3

        # Questions about self/consciousness with "do you" patterns
        if re.search(r'(?:do\s+you\s+(?:think|feel|believe)|are\s+you\s+conscious)', normalized):
            score += 0.4

        # Explicit consciousness/existence questions
        if re.search(r'(?:consciousness|existence|being|aware)', normalized) and '?' in normalized:
            score += 0.2

        return (score, matched_keywords)

    def _score_meta(self, normalized: str, words: Set[str]) -> Tuple[float, List[str]]:
        """Score likelihood of META intent (questions about the system)."""
        score = 0.0
        matched_keywords = []

        # Check for meta keywords
        meta_matches = words.intersection(self.META_KEYWORDS)
        if meta_matches:
            score += len(meta_matches) * 0.2
            matched_keywords.extend(meta_matches)

        # "How do you" / "What can you" patterns - strong meta indicators
        if re.search(r'(?:how\s+do\s+you|what\s+can\s+you|are\s+you\s+able)', normalized):
            score += 0.4

        # Questions about capabilities
        if re.search(r'(?:your\s+(?:capabilities|abilities|features|limitations))', normalized):
            score += 0.45

        # "What are your" pattern
        if re.search(r'what\s+are\s+your', normalized):
            score += 0.35

        # Direct address about the system
        if re.search(r'(?:stoffy|consciousness).*(?:work|function|operate)', normalized):
            score += 0.3

        # "Tell me about your/yourself"
        if re.search(r'tell\s+me\s+about\s+(?:your|yourself)', normalized):
            score += 0.4

        return (score, matched_keywords)

    def _score_conversation(self, normalized: str, words: Set[str]) -> Tuple[float, List[str]]:
        """Score likelihood of CONVERSATION intent."""
        # Default score - conversation is the fallback
        score = 0.2
        matched_keywords = []

        # Greetings
        greetings = {'hi', 'hello', 'hey', 'greetings', 'good', 'morning', 'afternoon', 'evening'}
        greeting_matches = words.intersection(greetings)
        if greeting_matches:
            score += 0.4
            matched_keywords.extend(greeting_matches)

        # Short messages without action words
        word_count = len(normalized.split())
        if word_count <= 3 and not words.intersection(self.action_keywords):
            score += 0.2

        # Expressions
        expressions = {'thanks', 'thank', 'okay', 'ok', 'cool', 'nice', 'great', 'awesome'}
        if words.intersection(expressions):
            score += 0.3

        return (score, matched_keywords)

    def _starts_with_verb(self, text: str) -> bool:
        """Check if text starts with an action verb."""
        words = text.split()
        if not words:
            return False
        return words[0] in self.action_keywords

    def _detect_urgency(self, normalized: str, words: Set[str]) -> Urgency:
        """Detect the urgency level of the message."""
        if words.intersection(self.URGENCY_CRITICAL):
            return Urgency.CRITICAL
        if words.intersection(self.URGENCY_HIGH):
            return Urgency.HIGH
        if words.intersection(self.URGENCY_LOW):
            return Urgency.LOW
        return Urgency.MEDIUM

    def extract_entities(self, message: str) -> List[str]:
        """
        Extract file paths, folder names, package names, etc.

        Args:
            message: The user's message

        Returns:
            List of extracted entity strings
        """
        entities: List[str] = []

        # Extract quoted strings (explicit entities)
        for match in self.QUOTED_PATTERN.finditer(message):
            entities.append(match.group(1))

        # Extract file paths
        for match in self.FILE_PATH_PATTERN.finditer(message):
            path = match.group(1)
            if path not in entities:
                entities.append(path)

        # Extract folder paths
        for match in self.FOLDER_PATH_PATTERN.finditer(message):
            path = match.group(1).rstrip('/')
            if path and path not in entities:
                entities.append(path)

        # Extract package names from install commands
        for match in self.PACKAGE_PATTERN.finditer(message):
            package = match.group(1)
            if package not in entities:
                entities.append(package)

        # Extract commands in backticks
        for match in self.COMMAND_PATTERN.finditer(message):
            cmd = match.group(1) or match.group(2)
            if cmd and cmd not in entities:
                entities.append(cmd)

        return entities

    def should_execute(self, intent: TaskIntent, threshold: float = 0.7) -> bool:
        """
        Determine if this intent warrants automatic execution.

        Args:
            intent: The classified intent
            threshold: Minimum confidence for execution

        Returns:
            True if the intent should trigger execution
        """
        # Only TASK intents can trigger execution
        if intent.type != IntentType.TASK:
            return False

        # Must meet confidence threshold
        if intent.confidence < threshold:
            return False

        # Must have action keywords
        if not intent.action_keywords:
            return False

        # Higher threshold for destructive actions
        destructive_keywords = {'delete', 'remove', 'rm', 'destroy', 'drop', 'truncate', 'wipe'}
        if intent.action_keywords and set(intent.action_keywords).intersection(destructive_keywords):
            # Require higher confidence for destructive actions
            return intent.confidence >= 0.85

        return True

    def _build_reasoning(
        self,
        intent_type: IntentType,
        keywords: List[str],
        entities: List[str]
    ) -> str:
        """Build a human-readable reasoning string."""
        parts = [f"Classified as {intent_type.value}"]

        if keywords:
            parts.append(f"keywords: {', '.join(keywords[:5])}")

        if entities:
            parts.append(f"entities: {', '.join(entities[:3])}")

        return "; ".join(parts)


# Convenience functions

def classify_intent(message: str) -> TaskIntent:
    """
    Convenience function to classify a message.

    Args:
        message: User message to classify

    Returns:
        TaskIntent with classification
    """
    classifier = IntentClassifier()
    return classifier.classify(message)


def is_task_request(message: str, threshold: float = 0.7) -> bool:
    """
    Quick check if a message is a task request.

    Args:
        message: User message to check
        threshold: Confidence threshold

    Returns:
        True if the message is a high-confidence task request
    """
    intent = classify_intent(message)
    return IntentClassifier().should_execute(intent, threshold)


def extract_entities_from_message(message: str) -> List[str]:
    """
    Extract entities from a message.

    Args:
        message: User message

    Returns:
        List of extracted entities (files, folders, packages, etc.)
    """
    classifier = IntentClassifier()
    return classifier.extract_entities(message)


# Test the module
if __name__ == "__main__":
    test_messages = [
        # Task requests
        "Delete the old backup folder /tmp/backup",
        "Create a new file called utils.py with helper functions",
        "Run the tests for the user module",
        "Please fix the bug in login.js",
        "npm install lodash",
        "Can you refactor the database connection code?",

        # Questions
        "What is the purpose of the watcher module?",
        "How does the decision engine work?",
        "Why is the test failing?",
        "Explain the architecture of this system",

        # Philosophical
        "Do you think consciousness can emerge from code?",
        "What is the meaning of being autonomous?",
        "Ponder the nature of self-awareness",

        # Meta
        "What are your capabilities?",
        "How do you work, Stoffy?",
        "Can you explain your architecture?",

        # Conversation
        "Hello!",
        "Thanks for the help",
        "Good morning",
    ]

    classifier = IntentClassifier()

    print("Task Intent Classification Demo\n" + "=" * 50)

    for msg in test_messages:
        intent = classifier.classify(msg)
        execute = classifier.should_execute(intent)

        print(f"\nMessage: {msg[:60]}{'...' if len(msg) > 60 else ''}")
        print(f"  Type: {intent.type.value}")
        print(f"  Confidence: {intent.confidence:.2f}")
        print(f"  Urgency: {intent.urgency.value}")
        if intent.action_keywords:
            print(f"  Keywords: {', '.join(intent.action_keywords)}")
        if intent.entities:
            print(f"  Entities: {', '.join(intent.entities)}")
        print(f"  Should Execute: {execute}")
        print(f"  Reasoning: {intent.reasoning}")
