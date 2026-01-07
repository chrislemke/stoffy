"""
Tests for ResponseSynthesizer

Validates the synthesis of coherent responses from multiple sources.
"""

import pytest
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field

from consciousness.response_synthesizer import (
    ResponseSynthesizer,
    ConsciousnessThought,
    TaskIntent,
    classify_intent,
    synthesize_response,
)


# =========================================================================
# Fixtures
# =========================================================================

@dataclass
class MockExecutionResult:
    """Mock ExecutionResult for testing."""
    success: bool = True
    output: str = ""
    error: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)


@pytest.fixture
def synthesizer():
    """Create a basic ResponseSynthesizer."""
    return ResponseSynthesizer(sign_off="- Stoffy")


@pytest.fixture
def thought_basic():
    """Create a basic thought."""
    return ConsciousnessThought(
        content="This is a thoughtful response about the topic.",
        confidence=0.8,
    )


@pytest.fixture
def thought_deep():
    """Create a deep reflection thought."""
    return ConsciousnessThought(
        content="After careful consideration, I believe the best approach is to refactor the module into smaller, more focused components. This will improve maintainability and testability.",
        confidence=0.9,
        reflection_depth="deep",
        mood="contemplative",
        themes=["architecture", "refactoring", "best practices"],
    )


@pytest.fixture
def result_success():
    """Create a successful execution result."""
    return MockExecutionResult(
        success=True,
        output="Operation completed successfully",
        files_created=["src/new_file.py"],
    )


@pytest.fixture
def result_failure():
    """Create a failed execution result."""
    return MockExecutionResult(
        success=False,
        error="Permission denied: /protected/path",
    )


# =========================================================================
# ConsciousnessThought Tests
# =========================================================================

class TestConsciousnessThought:
    """Tests for ConsciousnessThought dataclass."""

    def test_is_substantial_true(self):
        """Substantial thoughts should return True."""
        thought = ConsciousnessThought(
            content="This is a sufficiently long thought to be considered substantial.",
            confidence=0.7,
        )
        assert thought.is_substantial() is True

    def test_is_substantial_false_short(self):
        """Short thoughts should not be substantial."""
        thought = ConsciousnessThought(
            content="Too short",
            confidence=0.8,
        )
        assert thought.is_substantial() is False

    def test_is_substantial_false_low_confidence(self):
        """Low confidence thoughts should not be substantial."""
        thought = ConsciousnessThought(
            content="This is long enough but has low confidence score.",
            confidence=0.3,
        )
        assert thought.is_substantial() is False

    def test_summary_short_content(self):
        """Summary should return full content if short."""
        thought = ConsciousnessThought(content="Short content")
        assert thought.summary() == "Short content"

    def test_summary_truncates_long_content(self):
        """Summary should truncate long content."""
        long_content = "This is a very long piece of content that exceeds the maximum length allowed for summaries and should be truncated."
        thought = ConsciousnessThought(content=long_content)
        summary = thought.summary(max_length=50)

        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")


# =========================================================================
# TaskIntent Classification Tests
# =========================================================================

class TestClassifyIntent:
    """Tests for intent classification."""

    def test_classify_create_intent(self):
        """Should classify create intents."""
        assert classify_intent("create a new file") == TaskIntent.CREATE
        assert classify_intent("make a config") == TaskIntent.CREATE
        assert classify_intent("generate a report") == TaskIntent.CREATE

    def test_classify_delete_intent(self):
        """Should classify delete intents."""
        assert classify_intent("delete this file") == TaskIntent.DELETE
        assert classify_intent("remove the temp folder") == TaskIntent.DELETE

    def test_classify_run_intent(self):
        """Should classify run intents."""
        assert classify_intent("run the tests") == TaskIntent.RUN
        assert classify_intent("execute the script") == TaskIntent.RUN

    def test_classify_question_intent(self):
        """Should classify question intents."""
        assert classify_intent("what is this module?") == TaskIntent.QUESTION
        assert classify_intent("how does the watcher work?") == TaskIntent.QUESTION
        assert classify_intent("why did this fail?") == TaskIntent.QUESTION

    def test_classify_explain_intent(self):
        """Should classify explain intents."""
        assert classify_intent("explain the architecture") == TaskIntent.EXPLAIN
        assert classify_intent("describe the process") == TaskIntent.EXPLAIN

    def test_classify_greeting_intent(self):
        """Should classify greeting intents."""
        assert classify_intent("hello") == TaskIntent.GREETING
        assert classify_intent("hi there") == TaskIntent.GREETING
        assert classify_intent("hey Stoffy") == TaskIntent.GREETING

    def test_classify_thanks_intent(self):
        """Should classify thanks intents."""
        assert classify_intent("thank you") == TaskIntent.THANKS
        assert classify_intent("thanks for the help") == TaskIntent.THANKS

    def test_classify_unknown_intent(self):
        """Should return UNKNOWN for unclassifiable messages."""
        assert classify_intent("xyz abc 123") == TaskIntent.UNKNOWN


# =========================================================================
# ResponseSynthesizer Tests
# =========================================================================

class TestResponseSynthesizer:
    """Tests for ResponseSynthesizer."""

    def test_synthesize_action_response_success(
        self, synthesizer, thought_basic, result_success
    ):
        """Should synthesize a successful action response."""
        response = synthesizer.synthesize(
            user_message="create a new file",
            consciousness_thought=thought_basic,
            execution_result=result_success,
            intent=TaskIntent.CREATE,
        )

        assert "Done!" in response
        assert "src/new_file.py" in response
        assert "- Stoffy" in response

    def test_synthesize_action_response_failure(
        self, synthesizer, thought_basic, result_failure
    ):
        """Should synthesize an error response for failed actions."""
        response = synthesizer.synthesize(
            user_message="write to protected path",
            consciousness_thought=thought_basic,
            execution_result=result_failure,
            intent=TaskIntent.CREATE,
        )

        assert "issue" in response.lower() or "error" in response.lower()
        assert "Permission denied" in response
        assert "- Stoffy" in response

    def test_synthesize_question_response(self, synthesizer, thought_deep):
        """Should synthesize a question response."""
        response = synthesizer.synthesize(
            user_message="what is the best approach?",
            consciousness_thought=thought_deep,
            execution_result=None,
            intent=TaskIntent.QUESTION,
        )

        assert "refactor" in response
        assert "- Stoffy" in response

    def test_synthesize_greeting_response(self, synthesizer, thought_basic):
        """Should synthesize a greeting response."""
        greeting_thought = ConsciousnessThought(
            content="Hello! Great to hear from you. How can I help today?",
            confidence=0.9,
        )

        response = synthesizer.synthesize(
            user_message="hello",
            consciousness_thought=greeting_thought,
            execution_result=None,
            intent=TaskIntent.GREETING,
        )

        assert "Hello" in response or "hello" in response
        assert "- Stoffy" in response

    def test_sign_off_customization(self):
        """Should use custom sign-off."""
        synthesizer = ResponseSynthesizer(sign_off="- Custom Signature")
        thought = ConsciousnessThought(content="A thought", confidence=0.5)

        response = synthesizer.synthesize(
            user_message="question?",
            consciousness_thought=thought,
            execution_result=None,
            intent=TaskIntent.QUESTION,
        )

        assert "- Custom Signature" in response

    def test_timestamp_inclusion(self):
        """Should include timestamp when configured."""
        synthesizer = ResponseSynthesizer(
            sign_off="- Test",
            include_timestamp=True,
        )
        thought = ConsciousnessThought(content="A thought", confidence=0.5)

        response = synthesizer.synthesize(
            user_message="test",
            consciousness_thought=thought,
            execution_result=None,
            intent=TaskIntent.UNKNOWN,
        )

        # Should contain a date-like pattern
        assert any(c.isdigit() for c in response)

    def test_format_error_response_with_suggestions(self, synthesizer):
        """Error responses should include helpful suggestions."""
        response = synthesizer.format_error_response(
            error="Permission denied: cannot write to file",
            attempted_action="create the configuration file",
        )

        assert "Permission" in response or "permission" in response
        assert "Possible solutions" in response

    def test_format_file_changes_single_file(self, synthesizer):
        """Should format single file change nicely."""
        result = MockExecutionResult(
            success=True,
            files_created=["config.yaml"],
        )

        # Access private method for testing
        formatted = synthesizer._format_file_changes(result)

        assert "config.yaml" in formatted
        assert "Created" in formatted

    def test_format_file_changes_multiple_files(self, synthesizer):
        """Should summarize multiple file changes."""
        result = MockExecutionResult(
            success=True,
            files_created=["file1.py", "file2.py"],
            files_modified=["existing.py"],
        )

        formatted = synthesizer._format_file_changes(result)

        assert "Files affected" in formatted
        assert "Created: 2" in formatted
        assert "Modified: 1" in formatted


# =========================================================================
# Convenience Function Tests
# =========================================================================

class TestSynthesizeResponseFunction:
    """Tests for the convenience function."""

    def test_synthesize_response_basic(self):
        """Should synthesize a basic response."""
        response = synthesize_response(
            user_message="what is this?",
            thought_content="This is an explanation of the topic.",
            sign_off="- Test",
        )

        assert "explanation" in response
        assert "- Test" in response

    def test_synthesize_response_with_result(self):
        """Should handle execution result."""
        result = MockExecutionResult(
            success=True,
            output="Done",
            files_created=["new.py"],
        )

        response = synthesize_response(
            user_message="create a file",
            thought_content="File created as requested.",
            execution_result=result,
        )

        assert "new.py" in response or "Done" in response


# =========================================================================
# Edge Cases
# =========================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_thought_content(self, synthesizer):
        """Should handle empty thought content."""
        thought = ConsciousnessThought(content="", confidence=0.5)

        response = synthesizer.synthesize(
            user_message="hello",
            consciousness_thought=thought,
            execution_result=None,
            intent=TaskIntent.GREETING,
        )

        # Should fall back to default greeting
        assert "- Stoffy" in response

    def test_very_long_output_truncation(self, synthesizer, thought_basic):
        """Should truncate very long outputs."""
        long_output = "x" * 10000

        result = MockExecutionResult(
            success=True,
            output=long_output,
        )

        response = synthesizer.synthesize(
            user_message="run command",
            consciousness_thought=thought_basic,
            execution_result=result,
            intent=TaskIntent.RUN,
        )

        assert "(truncated)" in response
        assert len(response) < 10000

    def test_special_characters_in_output(self, synthesizer, thought_basic):
        """Should handle special characters in output."""
        result = MockExecutionResult(
            success=True,
            output="Result: `code` and *markdown* and <html>",
        )

        response = synthesizer.synthesize(
            user_message="run",
            consciousness_thought=thought_basic,
            execution_result=result,
            intent=TaskIntent.RUN,
        )

        # Should not crash
        assert "- Stoffy" in response

    def test_none_execution_result_with_action_intent(self, synthesizer, thought_basic):
        """Should handle action intent without execution result."""
        response = synthesizer.synthesize(
            user_message="delete the folder",
            consciousness_thought=thought_basic,
            execution_result=None,
            intent=TaskIntent.DELETE,
        )

        assert "Would you like me to" in response or "delete" in response.lower()
        assert "- Stoffy" in response
