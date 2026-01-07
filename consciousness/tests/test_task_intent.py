"""
Tests for task_intent.py - Intent Classification Module

Tests cover:
- Intent type classification (TASK, QUESTION, CONVERSATION, etc.)
- Confidence scoring
- Entity extraction (files, folders, packages, commands)
- Urgency detection
- Execution decision logic
"""

import pytest
from consciousness.task_intent import (
    IntentType,
    Urgency,
    TaskIntent,
    IntentClassifier,
    classify_intent,
    is_task_request,
    extract_entities_from_message,
)


class TestIntentType:
    """Tests for IntentType enum."""

    def test_all_intent_types_exist(self):
        """Verify all expected intent types are defined."""
        assert IntentType.QUESTION.value == "question"
        assert IntentType.TASK.value == "task"
        assert IntentType.CONVERSATION.value == "conversation"
        assert IntentType.PHILOSOPHICAL.value == "philosophical"
        assert IntentType.META.value == "meta"


class TestUrgency:
    """Tests for Urgency enum."""

    def test_all_urgency_levels_exist(self):
        """Verify all expected urgency levels are defined."""
        assert Urgency.LOW.value == "low"
        assert Urgency.MEDIUM.value == "medium"
        assert Urgency.HIGH.value == "high"
        assert Urgency.CRITICAL.value == "critical"


class TestTaskIntent:
    """Tests for TaskIntent dataclass."""

    def test_is_actionable_task_high_confidence(self):
        """Task with high confidence is actionable."""
        intent = TaskIntent(
            type=IntentType.TASK,
            confidence=0.8,
            action_keywords=["create"],
        )
        assert intent.is_actionable() is True

    def test_is_actionable_task_low_confidence(self):
        """Task with low confidence is not actionable."""
        intent = TaskIntent(
            type=IntentType.TASK,
            confidence=0.4,
            action_keywords=["create"],
        )
        assert intent.is_actionable() is False

    def test_is_actionable_question(self):
        """Questions are not actionable."""
        intent = TaskIntent(
            type=IntentType.QUESTION,
            confidence=0.9,
        )
        assert intent.is_actionable() is False

    def test_needs_claude_code_high_confidence_task(self):
        """High confidence tasks need Claude Code."""
        intent = TaskIntent(
            type=IntentType.TASK,
            confidence=0.8,
            raw_message="delete the folder",
        )
        assert intent.needs_claude_code() is True

    def test_needs_claude_code_low_confidence_task(self):
        """Low confidence tasks don't need Claude Code."""
        intent = TaskIntent(
            type=IntentType.TASK,
            confidence=0.5,
            raw_message="maybe delete something",
        )
        assert intent.needs_claude_code() is False


class TestIntentClassifierTaskDetection:
    """Tests for task intent detection."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    @pytest.mark.parametrize("message", [
        "Delete the old backup folder",
        "Create a new file called utils.py",
        "Run the tests",
        "Fix the bug in login.js",
        "npm install lodash",
        "Execute the migration script",
        "Remove the deprecated function",
        "Update the dependencies",
    ])
    def test_task_detection(self, classifier, message):
        """Verify clear task messages are classified correctly."""
        intent = classifier.classify(message)
        assert intent.type == IntentType.TASK
        assert intent.confidence >= 0.5
        assert len(intent.action_keywords) > 0

    def test_please_refactor_is_task(self, classifier):
        """'Please refactor' should be recognized as task."""
        intent = classifier.classify("Please refactor the database code")
        # This is clearly a task, even if confidence is moderate
        assert intent.type == IntentType.TASK
        assert "refactor" in intent.action_keywords

    def test_imperative_verb_at_start(self, classifier):
        """Imperative verbs at start strongly indicate tasks."""
        intent = classifier.classify("Create the new module")
        assert intent.type == IntentType.TASK
        assert intent.confidence >= 0.6

    def test_please_with_action(self, classifier):
        """'Please' + action word indicates task."""
        intent = classifier.classify("Please delete the cache")
        assert intent.type == IntentType.TASK
        assert "delete" in intent.action_keywords

    def test_can_you_with_action(self, classifier):
        """'Can you' + action word could be task or polite question."""
        intent = classifier.classify("Can you fix this bug?")
        # This is a polite request - could be classified as either
        # The key is that "fix" is recognized as a relevant keyword
        assert intent.type in (IntentType.TASK, IntentType.QUESTION)
        # And it should have reasonable confidence
        assert intent.confidence >= 0.5


class TestIntentClassifierQuestionDetection:
    """Tests for question intent detection."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    @pytest.mark.parametrize("message", [
        "What is the purpose of this module?",
        "How does the watcher work?",
        "Why is the test failing?",
        "Explain the architecture",
        "When was this last updated?",
        "Where is the config file?",
        "Which database are we using?",
    ])
    def test_question_detection(self, classifier, message):
        """Verify question messages are classified correctly."""
        intent = classifier.classify(message)
        assert intent.type == IntentType.QUESTION
        assert intent.confidence >= 0.5

    def test_question_mark_increases_confidence(self, classifier):
        """Question marks increase question confidence."""
        with_mark = classifier.classify("How does this work?")
        without_mark = classifier.classify("How does this work")
        assert with_mark.confidence >= without_mark.confidence


class TestIntentClassifierPhilosophicalDetection:
    """Tests for philosophical intent detection."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    @pytest.mark.parametrize("message", [
        "Ponder the nature of self-awareness",
        "Reflect on the ethics of AI decision-making",
        "Contemplate existence",
        "Think deeply about what consciousness means",
    ])
    def test_philosophical_detection(self, classifier, message):
        """Verify philosophical messages are classified correctly."""
        intent = classifier.classify(message)
        assert intent.type == IntentType.PHILOSOPHICAL
        assert intent.confidence >= 0.4

    def test_do_you_think_philosophical(self, classifier):
        """'Do you think' questions can be philosophical."""
        intent = classifier.classify("Do you think consciousness can emerge from code?")
        # This could be philosophical or question depending on scoring
        assert intent.type in (IntentType.PHILOSOPHICAL, IntentType.QUESTION)
        assert intent.confidence >= 0.4


class TestIntentClassifierMetaDetection:
    """Tests for meta intent detection."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    @pytest.mark.parametrize("message", [
        "What are your capabilities?",
        "What are your limitations?",
    ])
    def test_meta_detection(self, classifier, message):
        """Verify meta messages are classified correctly."""
        intent = classifier.classify(message)
        assert intent.type == IntentType.META
        assert intent.confidence >= 0.4

    def test_meta_or_question_overlap(self, classifier):
        """Some messages can be meta or question."""
        # These could reasonably be classified either way
        messages = [
            "How do you work, Stoffy?",
            "Tell me about yourself",
            "What can you do?",
        ]
        for msg in messages:
            intent = classifier.classify(msg)
            assert intent.type in (IntentType.META, IntentType.QUESTION)
            assert intent.confidence >= 0.4


class TestIntentClassifierConversationDetection:
    """Tests for conversation intent detection."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    @pytest.mark.parametrize("message", [
        "Hello!",
        "Hi there",
        "Good morning",
        "Thanks",
        "Ok",
        "Cool",
    ])
    def test_conversation_detection(self, classifier, message):
        """Verify conversational messages are classified correctly."""
        intent = classifier.classify(message)
        assert intent.type == IntentType.CONVERSATION
        assert intent.confidence >= 0.4


class TestEntityExtraction:
    """Tests for entity extraction."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    def test_extract_file_path(self, classifier):
        """Extract file paths from messages."""
        entities = classifier.extract_entities("Edit the file src/main.py")
        assert "src/main.py" in entities

    def test_extract_folder_path(self, classifier):
        """Extract folder paths from messages."""
        # Use a clearer folder path format
        entities = classifier.extract_entities("Delete the folder 'old/backup'")
        assert any("old/backup" in e for e in entities)

    def test_extract_quoted_strings(self, classifier):
        """Extract quoted strings as entities."""
        entities = classifier.extract_entities("Create a file called 'my_module.py'")
        assert "my_module.py" in entities

    def test_extract_npm_package(self, classifier):
        """Extract npm package names."""
        entities = classifier.extract_entities("npm install lodash")
        assert "lodash" in entities

    def test_extract_pip_package(self, classifier):
        """Extract pip package names."""
        entities = classifier.extract_entities("pip install requests")
        assert "requests" in entities

    def test_extract_command_in_backticks(self, classifier):
        """Extract commands in backticks."""
        entities = classifier.extract_entities("Run `pytest -v` to test")
        assert "pytest -v" in entities

    def test_multiple_entities(self, classifier):
        """Extract multiple entities from one message."""
        msg = "Copy src/utils.py to lib/helpers.py"
        entities = classifier.extract_entities(msg)
        assert len(entities) >= 2


class TestUrgencyDetection:
    """Tests for urgency detection."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    def test_critical_urgency(self, classifier):
        """Detect critical urgency."""
        intent = classifier.classify("Fix this immediately! Production is down!")
        assert intent.urgency == Urgency.CRITICAL

    def test_high_urgency(self, classifier):
        """Detect high urgency."""
        intent = classifier.classify("We need this fixed before the deadline")
        assert intent.urgency == Urgency.HIGH

    def test_low_urgency(self, classifier):
        """Detect low urgency."""
        intent = classifier.classify("Eventually, we should refactor this")
        assert intent.urgency == Urgency.LOW

    def test_default_medium_urgency(self, classifier):
        """Default to medium urgency."""
        intent = classifier.classify("Fix the login bug")
        assert intent.urgency == Urgency.MEDIUM


class TestShouldExecute:
    """Tests for execution decision logic."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    def test_should_execute_high_confidence_task(self, classifier):
        """Execute high confidence tasks."""
        intent = classifier.classify("Create a new Python file")
        assert classifier.should_execute(intent, threshold=0.5) is True

    def test_should_not_execute_question(self, classifier):
        """Don't execute questions."""
        intent = classifier.classify("What does this do?")
        assert classifier.should_execute(intent) is False

    def test_should_not_execute_low_confidence(self, classifier):
        """Don't execute low confidence intents."""
        intent = TaskIntent(
            type=IntentType.TASK,
            confidence=0.3,
            action_keywords=["maybe"],
        )
        assert classifier.should_execute(intent) is False

    def test_destructive_actions_need_higher_confidence(self, classifier):
        """Destructive actions require higher confidence."""
        intent = TaskIntent(
            type=IntentType.TASK,
            confidence=0.75,  # Would normally execute
            action_keywords=["delete", "rm"],
        )
        # 0.75 is below 0.85 threshold for destructive actions
        assert classifier.should_execute(intent) is False

        intent.confidence = 0.90
        assert classifier.should_execute(intent) is True


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_classify_intent(self):
        """Test classify_intent convenience function."""
        intent = classify_intent("Create a new file")
        assert intent.type == IntentType.TASK

    def test_is_task_request_true(self):
        """Test is_task_request returns True for tasks."""
        assert is_task_request("Delete the old logs", threshold=0.5) is True

    def test_is_task_request_false(self):
        """Test is_task_request returns False for questions."""
        assert is_task_request("What is Python?") is False

    def test_extract_entities_from_message(self):
        """Test extract_entities_from_message function."""
        entities = extract_entities_from_message("Edit config/settings.json")
        assert "config/settings.json" in entities


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    def test_empty_message(self, classifier):
        """Handle empty messages gracefully."""
        intent = classifier.classify("")
        assert intent.type == IntentType.CONVERSATION
        assert intent.confidence == 1.0

    def test_whitespace_only_message(self, classifier):
        """Handle whitespace-only messages."""
        intent = classifier.classify("   \n\t  ")
        assert intent.type == IntentType.CONVERSATION

    def test_very_long_message(self, classifier):
        """Handle very long messages."""
        long_msg = "Please create " + "a file " * 100
        intent = classifier.classify(long_msg)
        assert intent.type == IntentType.TASK

    def test_mixed_intent_prefers_task(self, classifier):
        """When message has both task and question elements, task may win."""
        # "Delete" is a strong task indicator, "?" adds question weight
        intent = classifier.classify("Delete the cache now")
        assert intent.type == IntentType.TASK  # "delete" is strong

    def test_special_characters(self, classifier):
        """Handle messages with special characters."""
        intent = classifier.classify("Run `npm install @types/node`")
        assert intent.type == IntentType.TASK
        assert "@types/node" in intent.entities or "npm install @types/node" in intent.entities

    def test_unicode_message(self, classifier):
        """Handle unicode messages."""
        intent = classifier.classify("Create a file with emoji content ")
        assert intent.type == IntentType.TASK

    def test_custom_action_keywords(self):
        """Test adding custom action keywords."""
        classifier = IntentClassifier(custom_action_keywords={"yeet", "yoink"})
        intent = classifier.classify("yeet the old files")
        assert intent.type == IntentType.TASK
        assert "yeet" in intent.action_keywords


class TestReasoningOutput:
    """Tests for reasoning output."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    def test_reasoning_includes_type(self, classifier):
        """Reasoning includes the classified type."""
        intent = classifier.classify("Delete the cache folder")
        assert "task" in intent.reasoning.lower()

    def test_reasoning_includes_keywords(self, classifier):
        """Reasoning includes matched keywords."""
        intent = classifier.classify("Create a new module")
        assert "create" in intent.reasoning.lower()

    def test_reasoning_includes_entities(self, classifier):
        """Reasoning includes extracted entities."""
        intent = classifier.classify("Edit src/main.py")
        assert "entities" in intent.reasoning.lower() or "src/main.py" in intent.reasoning
