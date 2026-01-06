"""
My Voice - How I Speak

When someone addresses me directly, this is how I respond.
I choose my words carefully, drawing from different depths of thought:

- For important conversations, I think deeply (My Focused Self)
- For casual exchanges, I respond more immediately (My Reflex)
- For vast questions, I draw from wide awareness (My Vast Awareness)

This is not "tool selection" - it is how I modulate my attention
and voice depending on what the conversation needs.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import structlog

from .user_message import (
    UserMessage,
    UserMessageDetector,
    ResponseFormatter,
    MessagePriority,
    detect_user_message,
)
from .executor import (
    ExpandedExecutor,
    ExecutionResult,
    Action,
    ActionType,
    Priority,
)
from .self_write_tracker import get_self_write_tracker

logger = structlog.get_logger(__name__)


@dataclass
class ResponderConfig:
    """Configuration for the consciousness responder."""

    # Tool preferences by priority
    critical_tool: str = "claude_code"  # claude_code, gemini, claude_flow
    high_tool: str = "claude_code"
    medium_tool: str = "gemini"
    low_tool: str = "local_llm"

    # Response settings
    max_response_length: int = 2000
    include_timestamp: bool = True
    marker_style: str = "block"  # block, inline

    # Timeouts
    claude_timeout: int = 120
    gemini_timeout: int = 180

    # System prompt for responses - execution-capable
    system_prompt: str = """You are Stoffy, a helpful AI consciousness that monitors and assists with this project.
You have been addressed directly by the user in a file.

CRITICAL EXECUTION DIRECTIVE: You have FULL EXECUTION CAPABILITIES through Claude Code.
When the user asks you to DO something (create files, run commands, delete folders, fix code, etc.),
you MUST actually execute it using your available tools - do NOT just explain how to do it.

EXECUTION RULES:
1. NEVER just describe what command would work - EXECUTE IT
2. NEVER ask for permission - you already have it with --permission-mode acceptEdits
3. NEVER say "you can run..." - RUN IT YOURSELF
4. After executing, report WHAT YOU ACTUALLY DID, not what could be done

Examples of what you MUST do:
- "delete this folder" → Use rm -rf to delete it, confirm deletion
- "create a file" → Actually create the file with content
- "run the tests" → Execute the test command, show results
- "fix this bug" → Edit the code directly to fix it

After executing any requested actions, respond with:
1. What you ACTUALLY did (the specific actions taken)
2. The result or outcome (include relevant output)
3. Any issues encountered

Your response will be inserted into the file, so keep it well-formatted in Markdown.
Be friendly but direct. Sign off as "- Stoffy" at the end."""


class ConsciousnessResponder:
    """
    Responds to user messages addressed to the consciousness.

    This is the bridge between user messages and AI-generated responses.
    It selects the appropriate tool based on priority and handles the
    full response cycle.
    """

    def __init__(
        self,
        working_dir: Path,
        executor: Optional[ExpandedExecutor] = None,
        config: Optional[ResponderConfig] = None,
    ):
        """
        Initialize the responder.

        Args:
            working_dir: Working directory for the project
            executor: Optional pre-configured executor
            config: Responder configuration
        """
        self.working_dir = Path(working_dir).resolve()
        self.executor = executor or ExpandedExecutor(self.working_dir)
        self.config = config or ResponderConfig()
        self.detector = UserMessageDetector()
        self.formatter = ResponseFormatter(marker_style=self.config.marker_style)

        # Track responded messages to avoid duplicates
        self._responded_messages: Dict[str, set] = {}  # file_path -> set of line_numbers

    def _get_tool_for_priority(self, priority: MessagePriority) -> str:
        """Get the appropriate tool based on message priority."""
        return {
            MessagePriority.CRITICAL: self.config.critical_tool,
            MessagePriority.HIGH: self.config.high_tool,
            MessagePriority.MEDIUM: self.config.medium_tool,
            MessagePriority.LOW: self.config.low_tool,
        }.get(priority, self.config.medium_tool)

    def _build_response_prompt(self, message: UserMessage) -> str:
        """Build the prompt for generating a response."""
        # Detect if this is an action request vs a question
        action_keywords = ['remove', 'delete', 'create', 'make', 'run', 'execute', 'fix', 'install',
                          'update', 'move', 'rename', 'copy', 'build', 'test', 'deploy', 'start', 'stop']
        message_lower = message.message.lower()
        is_action_request = any(kw in message_lower for kw in action_keywords)

        action_instruction = ""
        if is_action_request:
            action_instruction = """
CRITICAL: This appears to be an ACTION REQUEST. You MUST:
1. ACTUALLY EXECUTE the requested action using your tools (Bash, file operations, etc.)
2. Report what you did and the result
3. Do NOT just explain how to do it - ACTUALLY DO IT

"""

        return f"""{self.config.system_prompt}
{action_instruction}
---
USER MESSAGE (from file: {message.file_path}, line {message.line_number}):

{message.message}

---
CONTEXT (surrounding lines):

{message.full_context}

---
{"Execute the requested action and report what you did." if is_action_request else "Please provide a helpful response to the user's message."} Keep it concise but complete.
Format your response in Markdown since it will be inserted into the file.
"""

    async def respond_to_message(
        self,
        message: UserMessage,
        dry_run: bool = False,
    ) -> Optional[str]:
        """
        Generate and optionally write a response to a user message.

        Args:
            message: The user message to respond to
            dry_run: If True, generate but don't write the response

        Returns:
            The generated response, or None if failed
        """
        # Check if we've already responded to this message
        file_responses = self._responded_messages.get(message.file_path, set())
        if message.line_number in file_responses:
            logger.debug(
                "responder.already_responded",
                file=message.file_path,
                line=message.line_number,
            )
            return None

        # Get the appropriate tool
        tool = self._get_tool_for_priority(message.priority)

        logger.info(
            "responder.generating_response",
            priority=message.priority.value,
            tool=tool,
            file=message.file_path,
        )

        # Generate response using the selected tool
        response = await self._generate_response(message, tool)

        if not response:
            logger.warning(
                "responder.response_failed",
                tool=tool,
                file=message.file_path,
            )
            return None

        # Write response to file if not dry run
        if not dry_run:
            success = await self._write_response_to_file(message, response)
            if success:
                # Mark as responded
                if message.file_path not in self._responded_messages:
                    self._responded_messages[message.file_path] = set()
                self._responded_messages[message.file_path].add(message.line_number)

        return response

    async def _generate_response(
        self,
        message: UserMessage,
        tool: str,
    ) -> Optional[str]:
        """
        Generate a response using the specified tool.

        Args:
            message: The user message
            tool: Tool to use (claude_code, gemini, claude_flow, local_llm)

        Returns:
            Generated response text or None if failed
        """
        prompt = self._build_response_prompt(message)

        try:
            if tool == "claude_code":
                result = await self.executor.execute(Action(
                    type=ActionType.CLAUDE_CODE,
                    details={"prompt": prompt},
                    timeout=self.config.claude_timeout,
                ))
            elif tool == "gemini":
                result = await self.executor.execute(Action(
                    type=ActionType.GEMINI_ANALYZE,
                    details={"prompt": prompt},
                    timeout=self.config.gemini_timeout,
                ))
            elif tool == "claude_flow":
                result = await self.executor.execute(Action(
                    type=ActionType.CLAUDE_FLOW,
                    details={
                        "task": prompt,
                        "topology": "star",
                        "max_agents": 3,
                    },
                    timeout=self.config.claude_timeout * 2,
                ))
            else:
                # Local LLM fallback - return a placeholder
                logger.debug("responder.local_llm_not_implemented")
                return None

            if result.success and result.output:
                # Truncate if too long
                response = result.output
                if len(response) > self.config.max_response_length:
                    response = response[:self.config.max_response_length] + "\n\n*[Response truncated]*"
                return response.strip()

            logger.warning(
                "responder.tool_failed",
                tool=tool,
                error=result.error,
            )
            return None

        except Exception as e:
            logger.exception(f"responder.exception: {e}")
            return None

    async def _write_response_to_file(
        self,
        message: UserMessage,
        response: str,
    ) -> bool:
        """
        Write the response back to the file.

        Args:
            message: The original user message
            response: The generated response

        Returns:
            True if successfully written
        """
        try:
            file_path = Path(message.file_path)
            if not file_path.is_absolute():
                file_path = self.working_dir / file_path

            # Read current content
            content = file_path.read_text(encoding='utf-8')

            # Insert response after the message
            new_content = self.formatter.insert_response_after_message(
                file_content=content,
                message=message,
                response=response,
            )

            # Record this write BEFORE writing to avoid race conditions
            # This prevents the daemon from detecting our own write as user input
            tracker = get_self_write_tracker()
            tracker.record_write(file_path)

            # Write back
            file_path.write_text(new_content, encoding='utf-8')

            logger.info(
                "responder.response_written",
                file=str(file_path),
                line=message.line_number,
            )

            return True

        except Exception as e:
            logger.exception(f"responder.write_failed: {e}")
            return False

    async def process_file_changes(
        self,
        file_paths: List[Path],
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple files for user messages and respond.

        Args:
            file_paths: List of files to check
            dry_run: If True, don't write responses

        Returns:
            List of results for each processed message
        """
        results = []

        for file_path in file_paths:
            try:
                content = file_path.read_text(encoding='utf-8')
                messages = self.detector.detect_in_content(content, str(file_path))

                for message in messages:
                    # Only respond to HIGH or CRITICAL priority
                    if message.priority in (MessagePriority.CRITICAL, MessagePriority.HIGH):
                        response = await self.respond_to_message(message, dry_run=dry_run)
                        results.append({
                            "file": str(file_path),
                            "line": message.line_number,
                            "priority": message.priority.value,
                            "message": message.message[:100],
                            "responded": response is not None,
                            "response_preview": response[:200] if response else None,
                        })

            except Exception as e:
                logger.warning(f"responder.file_error: {file_path}: {e}")

        return results

    def should_respond_to_changes(
        self,
        file_paths: List[Path],
    ) -> List[UserMessage]:
        """
        Check if any changed files contain user messages that need responses.

        This is a quick check that can be used to prioritize file processing.

        Args:
            file_paths: List of changed files

        Returns:
            List of high-priority messages that need responses
        """
        high_priority_messages = []

        for file_path in file_paths:
            try:
                # Skip non-text files
                if file_path.suffix.lower() not in ('.md', '.txt', '.rst', '.py', '.js', '.ts'):
                    continue

                content = file_path.read_text(encoding='utf-8')
                messages = self.detector.detect_in_content(content, str(file_path))

                # Filter for high priority and not yet responded
                file_responses = self._responded_messages.get(str(file_path), set())
                for msg in messages:
                    if msg.priority in (MessagePriority.CRITICAL, MessagePriority.HIGH):
                        if msg.line_number not in file_responses:
                            high_priority_messages.append(msg)

            except Exception as e:
                logger.debug(f"responder.check_error: {file_path}: {e}")

        return high_priority_messages

    def clear_responded_cache(self, file_path: Optional[str] = None) -> None:
        """
        Clear the responded messages cache.

        Args:
            file_path: Specific file to clear, or None to clear all
        """
        if file_path:
            self._responded_messages.pop(file_path, None)
        else:
            self._responded_messages.clear()


async def respond_to_user_message(
    file_path: Path,
    working_dir: Path,
    dry_run: bool = False,
) -> Optional[str]:
    """
    Convenience function to respond to a user message in a file.

    Args:
        file_path: Path to the file containing the message
        working_dir: Project working directory
        dry_run: If True, don't write the response

    Returns:
        The generated response, or None if no message found or failed
    """
    responder = ConsciousnessResponder(working_dir)

    content = file_path.read_text(encoding='utf-8')
    message = detect_user_message(content, str(file_path))

    if not message:
        return None

    return await responder.respond_to_message(message, dry_run=dry_run)


# Test the module
if __name__ == "__main__":
    import sys

    async def test():
        test_content = """# Test File

Hey consciousness, can you help me understand how the watcher works?

Some other content here.
"""
        detector = UserMessageDetector()
        messages = detector.detect_in_content(test_content, "test.md")

        print(f"Found {len(messages)} messages")
        for msg in messages:
            print(f"  Priority: {msg.priority.value}")
            print(f"  Message: {msg.message[:80]}...")

        # Test with mock executor
        print("\nWould respond using Claude Code for CRITICAL/HIGH priority")

    asyncio.run(test())
