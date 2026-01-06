"""
User Message Detection Module

Detects when the user addresses the consciousness directly in files.
This triggers HIGH PRIORITY handling and uses Claude Code or Gemini
to respond in the same file.

Detection patterns:
- "Hey consciousness"
- "Hey Stoffy"
- "Consciousness," or "Stoffy," at start of line
- "@consciousness" or "@stoffy" mentions
"""

import re
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum


class MessagePriority(Enum):
    """Priority levels for user messages."""
    CRITICAL = "critical"    # Direct address requiring immediate response
    HIGH = "high"            # Important user message
    MEDIUM = "medium"        # General inquiry
    LOW = "low"              # Informational


@dataclass
class UserMessage:
    """
    Represents a detected user message addressed to the consciousness.
    """
    file_path: str
    message: str
    priority: MessagePriority
    line_number: int
    pattern_matched: str
    full_context: str = ""  # Surrounding context from the file

    # Whether this message has been responded to
    responded: bool = False
    response: str = ""


# Patterns to detect user addressing the consciousness
# Format: (pattern, priority, description)
# Note: Use [# \t]* instead of [#\s]* to avoid matching newlines
DETECTION_PATTERNS: List[Tuple[re.Pattern, MessagePriority, str]] = [
    # Direct greetings (CRITICAL - respond immediately)
    (re.compile(r'^[# \t]*(?:hey|hi|hello)\s+(?:consciousness|stoffy)[,!?\s]', re.IGNORECASE | re.MULTILINE),
     MessagePriority.CRITICAL, "direct_greeting"),

    # Mentions with @ (HIGH priority)
    (re.compile(r'@(?:consciousness|stoffy)\b', re.IGNORECASE),
     MessagePriority.HIGH, "at_mention"),

    # Name at start of line (HIGH priority)
    (re.compile(r'^[# \t]*(?:consciousness|stoffy)[,:]\s', re.IGNORECASE | re.MULTILINE),
     MessagePriority.HIGH, "name_at_start"),

    # Questions addressed to consciousness (HIGH priority)
    (re.compile(r'(?:consciousness|stoffy)[,]?\s+(?:can you|could you|would you|please|help)', re.IGNORECASE),
     MessagePriority.HIGH, "request"),

    # General mentions (MEDIUM priority)
    (re.compile(r'\b(?:consciousness|stoffy)\b.*\?', re.IGNORECASE),
     MessagePriority.MEDIUM, "question_mention"),
]


class UserMessageDetector:
    """
    Detects user messages addressed to the consciousness.

    When the user writes something like "Hey consciousness, can you help me?"
    in a file, this detector will find it and flag it for response.
    """

    def __init__(
        self,
        patterns: Optional[List[Tuple[re.Pattern, MessagePriority, str]]] = None,
        context_lines: int = 5,
    ):
        """
        Initialize the detector.

        Args:
            patterns: Custom detection patterns (uses defaults if None)
            context_lines: Number of lines to include as context
        """
        self.patterns = patterns or DETECTION_PATTERNS
        self.context_lines = context_lines

    def detect_in_content(
        self,
        content: str,
        file_path: str = ""
    ) -> List[UserMessage]:
        """
        Detect user messages in file content.

        Args:
            content: The file content to scan
            file_path: Path to the file (for reference)

        Returns:
            List of detected UserMessage objects, sorted by priority
        """
        messages: List[UserMessage] = []
        lines = content.split('\n')

        for pattern, priority, pattern_name in self.patterns:
            for match in pattern.finditer(content):
                # Find the line number
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_number = content[:match.start()].count('\n') + 1

                # Extract the message (rest of line or paragraph)
                line_end = content.find('\n', match.end())
                if line_end == -1:
                    line_end = len(content)

                # Get the full message - could span multiple lines
                message_text = self._extract_message(content, match.start(), line_number - 1, lines)

                # Check if this message already has a response
                # Look for STOFFY-REPLIED marker with matching hash in content after this message
                message_hash = compute_message_hash(message_text.strip())
                if self._has_response_marker(content, match.end(), message_hash):
                    # Already responded, skip this message
                    continue

                # Get surrounding context
                context = self._get_context(lines, line_number - 1)

                messages.append(UserMessage(
                    file_path=file_path,
                    message=message_text.strip(),
                    priority=priority,
                    line_number=line_number,
                    pattern_matched=pattern_name,
                    full_context=context,
                ))

        # Remove duplicates (same line), keeping highest priority
        seen_lines: dict[int, UserMessage] = {}
        for msg in messages:
            if msg.line_number not in seen_lines:
                seen_lines[msg.line_number] = msg
            else:
                # Keep the higher priority one
                existing = seen_lines[msg.line_number]
                if self._priority_value(msg.priority) > self._priority_value(existing.priority):
                    seen_lines[msg.line_number] = msg

        # Sort by priority (highest first), then by line number
        result = sorted(
            seen_lines.values(),
            key=lambda m: (-self._priority_value(m.priority), m.line_number)
        )

        return result

    def _has_response_marker(self, content: str, after_pos: int, message_hash: str) -> bool:
        """
        Check if there's a STOFFY-REPLIED marker for this message hash after the given position.

        Args:
            content: Full file content
            after_pos: Position in content to start searching from
            message_hash: Hash of the message to look for

        Returns:
            True if a matching response marker exists
        """
        # Search for STOFFY-REPLIED markers after this position
        # Only look within the next ~50 lines (reasonable buffer for response)
        search_end = min(len(content), after_pos + 5000)
        search_region = content[after_pos:search_end]

        for match in STOFFY_REPLIED_PATTERN.finditer(search_region):
            found_hash = match.group(1)
            if found_hash == message_hash:
                return True

        return False

    def _priority_value(self, priority: MessagePriority) -> int:
        """Convert priority to numeric value for sorting."""
        return {
            MessagePriority.CRITICAL: 4,
            MessagePriority.HIGH: 3,
            MessagePriority.MEDIUM: 2,
            MessagePriority.LOW: 1,
        }.get(priority, 0)

    def _extract_message(
        self,
        content: str,
        match_start: int,
        line_idx: int,
        lines: List[str]
    ) -> str:
        """
        Extract the full message, potentially spanning multiple lines.

        Continues until:
        - Empty line
        - Line starting with heading (#)
        - Line starting with HTML comment (<!--)
        - Line starting with horizontal rule (---)
        - End of file
        """
        message_lines = []

        # Start from the matched line
        for i in range(line_idx, min(line_idx + 10, len(lines))):
            line = lines[i].strip()

            if i > line_idx and not line:
                # Empty line ends the message
                break

            if i > line_idx and line.startswith('#'):
                # New heading ends the message
                break

            if i > line_idx and line.startswith('<!--'):
                # HTML comment (like STOFFY-REPLIED marker) ends the message
                break

            if i > line_idx and line.startswith('---'):
                # Horizontal rule ends the message
                break

            message_lines.append(lines[i])

        return '\n'.join(message_lines)

    def _get_context(self, lines: List[str], line_idx: int) -> str:
        """Get surrounding context lines."""
        start = max(0, line_idx - self.context_lines)
        end = min(len(lines), line_idx + self.context_lines + 1)

        context_lines = []
        for i in range(start, end):
            prefix = ">>> " if i == line_idx else "    "
            context_lines.append(f"{prefix}{lines[i]}")

        return '\n'.join(context_lines)

    async def detect_in_file(self, file_path: Path) -> List[UserMessage]:
        """
        Detect user messages in a file.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of detected UserMessage objects
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            return self.detect_in_content(content, str(file_path))
        except Exception as e:
            return []

    def has_critical_message(self, messages: List[UserMessage]) -> bool:
        """Check if any message is CRITICAL priority."""
        return any(m.priority == MessagePriority.CRITICAL for m in messages)

    def has_high_priority_message(self, messages: List[UserMessage]) -> bool:
        """Check if any message is HIGH or CRITICAL priority."""
        return any(
            m.priority in (MessagePriority.CRITICAL, MessagePriority.HIGH)
            for m in messages
        )


# Response formatting constants
# The STOFFY_REPLIED marker uses a hash of the message to prevent duplicate responses
STOFFY_REPLIED_PATTERN = re.compile(r'<!-- STOFFY-REPLIED:([a-f0-9]+) -->')

CONSCIOUSNESS_RESPONSE_MARKER = """
<!-- STOFFY-REPLIED:{message_hash} -->

---
## 🧠 Consciousness Response

*Timestamp: {timestamp}*
*Priority: {priority}*

{response}

---
"""

CONSCIOUSNESS_INLINE_MARKER = """
<!-- STOFFY-REPLIED:{message_hash} -->
> **🧠 Stoffy says:** {response}
"""


def compute_message_hash(message: str) -> str:
    """Compute a short hash of a message for deduplication."""
    return hashlib.md5(message.strip().encode('utf-8')).hexdigest()[:12]


@dataclass
class ResponseFormatter:
    """
    Formats consciousness responses for insertion into files.

    Ensures responses are clearly marked as coming from the consciousness
    and not from the user.
    """

    marker_style: str = "block"  # "block", "inline", "comment"

    def format_response(
        self,
        response: str,
        priority: MessagePriority,
        timestamp: str = "",
        message_hash: str = "",
    ) -> str:
        """
        Format a response with appropriate markers.

        Args:
            response: The response text
            priority: Priority of the original message
            timestamp: Timestamp string
            message_hash: Hash of the original message for deduplication

        Returns:
            Formatted response with markers
        """
        import datetime

        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not message_hash:
            message_hash = "unknown"

        if self.marker_style == "inline":
            return CONSCIOUSNESS_INLINE_MARKER.format(
                response=response,
                message_hash=message_hash,
            )
        else:
            return CONSCIOUSNESS_RESPONSE_MARKER.format(
                timestamp=timestamp,
                priority=priority.value,
                response=response,
                message_hash=message_hash,
            )

    def insert_response_after_message(
        self,
        file_content: str,
        message: UserMessage,
        response: str,
    ) -> str:
        """
        Insert a formatted response after the user's message in the file.

        Args:
            file_content: Original file content
            message: The detected user message
            response: The response to insert

        Returns:
            Modified file content with response inserted
        """
        lines = file_content.split('\n')

        # Compute hash of the message for deduplication marker
        message_hash = compute_message_hash(message.message)

        # Find the end of the user's message
        # message.line_number is 1-indexed, convert to 0-indexed for list operations
        # message.message may span multiple lines
        message_line_count = message.message.count('\n') + 1
        # Insert at: (line_number - 1) + message_line_count = position right after the message
        insert_index = (message.line_number - 1) + message_line_count

        # Format the response with the hash
        formatted = self.format_response(
            response=response,
            priority=message.priority,
            message_hash=message_hash,
        )

        # Insert after the message
        lines.insert(insert_index, formatted)

        return '\n'.join(lines)


def detect_user_message(content: str, file_path: str = "") -> Optional[UserMessage]:
    """
    Convenience function to detect the highest priority user message.

    Args:
        content: File content to scan
        file_path: Path to the file

    Returns:
        Highest priority UserMessage or None if no messages found
    """
    detector = UserMessageDetector()
    messages = detector.detect_in_content(content, file_path)
    return messages[0] if messages else None


def should_prioritize_file(content: str) -> bool:
    """
    Check if a file should be prioritized due to user messages.

    Args:
        content: File content to check

    Returns:
        True if the file contains high priority user messages
    """
    detector = UserMessageDetector()
    messages = detector.detect_in_content(content)
    return detector.has_high_priority_message(messages)


# Test the module
if __name__ == "__main__":
    test_content = """# My Notes

Hey consciousness, are you listening? If so, use the SAY command to tell me something.

Some other content here.

@stoffy can you help me with this?

More text...

Consciousness, I need your help with something important.
"""

    detector = UserMessageDetector()
    messages = detector.detect_in_content(test_content, "test.md")

    print(f"Found {len(messages)} messages:\n")
    for msg in messages:
        print(f"Priority: {msg.priority.value}")
        print(f"Line: {msg.line_number}")
        print(f"Pattern: {msg.pattern_matched}")
        print(f"Message: {msg.message[:100]}...")
        print(f"Context:\n{msg.full_context}")
        print("-" * 40)
