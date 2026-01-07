"""Tests for the ConsciousnessForwarder module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from consciousness.consciousness_forwarder import (
    ConsciousnessForwarder,
    ConsciousnessGuidance,
    QuestionType,
    ForwarderConfig,
    GuidanceCache,
    QUESTION_TEMPLATES,
)


class TestQuestionType:
    """Tests for QuestionType enum."""

    def test_all_question_types_have_templates(self):
        """Every question type should have a template."""
        for qt in QuestionType:
            assert qt in QUESTION_TEMPLATES
            assert len(QUESTION_TEMPLATES[qt]) > 0

    def test_question_type_values(self):
        """Question types should have expected values."""
        assert QuestionType.APPROACH.value == "approach"
        assert QuestionType.RISK.value == "risk"
        assert QuestionType.ALTERNATIVE.value == "alternative"
        assert QuestionType.CONTEXT.value == "context"


class TestConsciousnessGuidance:
    """Tests for ConsciousnessGuidance dataclass."""

    def test_create_guidance(self):
        """Should create guidance with all fields."""
        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Use TDD methodology",
            confidence=0.85,
            alternatives=["Use BDD", "Use waterfall"],
            warnings=["Complex setup required"],
            key_points=["Write tests first", "Refactor continuously"],
        )

        assert guidance.question_type == QuestionType.APPROACH
        assert guidance.confidence == 0.85
        assert len(guidance.alternatives) == 2
        assert "Write tests first" in guidance.key_points

    def test_empty_guidance(self):
        """Should create empty guidance for unavailable consciousness."""
        guidance = ConsciousnessGuidance.empty(
            QuestionType.RISK,
            "Service unavailable"
        )

        assert guidance.confidence == 0.0
        assert "unavailable" in guidance.guidance.lower()
        assert not guidance.is_valid()

    def test_is_valid(self):
        """Should correctly identify valid guidance."""
        valid = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Valid guidance",
            confidence=0.8,
        )
        assert valid.is_valid()

        invalid = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="",
            confidence=0.8,
        )
        assert not invalid.is_valid()

        low_confidence = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Some guidance",
            confidence=0.0,
        )
        assert not low_confidence.is_valid()

    def test_to_dict_and_from_dict(self):
        """Should serialize and deserialize correctly."""
        original = ConsciousnessGuidance(
            question_type=QuestionType.PRIORITY,
            guidance="Focus on tests first",
            confidence=0.9,
            alternatives=["Focus on docs"],
            warnings=["Deadline approaching"],
            key_points=["Unit tests", "Integration tests"],
        )

        data = original.to_dict()
        restored = ConsciousnessGuidance.from_dict(data)

        assert restored.question_type == original.question_type
        assert restored.guidance == original.guidance
        assert restored.confidence == original.confidence
        assert restored.alternatives == original.alternatives

    def test_summarize(self):
        """Should create a summary of guidance."""
        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="This is a very long guidance text that should be truncated " * 10,
            confidence=0.8,
        )

        summary = guidance.summarize(max_length=50)
        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")


class TestGuidanceCache:
    """Tests for GuidanceCache."""

    def test_cache_put_and_get(self):
        """Should store and retrieve guidance."""
        cache = GuidanceCache(max_entries=10, ttl_seconds=3600)

        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Test guidance",
            confidence=0.8,
        )

        cache.put(QuestionType.APPROACH, "test context", guidance)
        retrieved = cache.get(QuestionType.APPROACH, "test context")

        assert retrieved is not None
        assert retrieved.guidance == "Test guidance"

    def test_cache_miss(self):
        """Should return None for cache miss."""
        cache = GuidanceCache()
        result = cache.get(QuestionType.RISK, "nonexistent")
        assert result is None

    def test_cache_expiration(self):
        """Should expire old entries."""
        cache = GuidanceCache(ttl_seconds=1)

        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Test",
            confidence=0.8,
        )

        cache.put(QuestionType.APPROACH, "context", guidance)

        # Manually expire by modifying internal state
        key = cache._make_key(QuestionType.APPROACH, "context")
        cache._cache[key] = (guidance, datetime.now() - timedelta(seconds=2))

        result = cache.get(QuestionType.APPROACH, "context")
        assert result is None

    def test_cache_lru_eviction(self):
        """Should evict oldest entries when full."""
        cache = GuidanceCache(max_entries=2)

        for i in range(3):
            guidance = ConsciousnessGuidance(
                question_type=QuestionType.APPROACH,
                guidance=f"Guidance {i}",
                confidence=0.8,
            )
            cache.put(QuestionType.APPROACH, f"context{i}", guidance)

        # First entry should be evicted
        assert cache.get(QuestionType.APPROACH, "context0") is None
        assert cache.get(QuestionType.APPROACH, "context1") is not None
        assert cache.get(QuestionType.APPROACH, "context2") is not None

    def test_cache_clear(self):
        """Should clear all entries."""
        cache = GuidanceCache()

        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Test",
            confidence=0.8,
        )

        cache.put(QuestionType.APPROACH, "context1", guidance)
        cache.put(QuestionType.RISK, "context2", guidance)

        cleared = cache.clear()
        assert cleared == 2
        assert cache.get(QuestionType.APPROACH, "context1") is None

    def test_cache_stats(self):
        """Should return cache statistics."""
        cache = GuidanceCache(max_entries=50, ttl_seconds=1800)

        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Test",
            confidence=0.8,
        )

        cache.put(QuestionType.APPROACH, "context", guidance)

        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["max_entries"] == 50
        assert stats["ttl_seconds"] == 1800


class TestForwarderConfig:
    """Tests for ForwarderConfig."""

    def test_default_config(self):
        """Should have sensible defaults."""
        config = ForwarderConfig()

        assert config.model == "gemini-2.0-flash"
        assert config.timeout_seconds == 30
        assert config.cache_enabled is True
        assert len(config.system_prompt) > 0

    def test_custom_config(self):
        """Should accept custom values."""
        config = ForwarderConfig(
            model="gemini-1.5-pro",
            timeout_seconds=60,
            cache_enabled=False,
        )

        assert config.model == "gemini-1.5-pro"
        assert config.timeout_seconds == 60
        assert config.cache_enabled is False


class TestConsciousnessForwarder:
    """Tests for ConsciousnessForwarder."""

    def test_init(self, tmp_path):
        """Should initialize correctly."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        assert forwarder.working_dir == tmp_path
        assert forwarder.temp_dir.exists()
        assert forwarder._query_count == 0
        assert forwarder._cache_hits == 0

    def test_is_available_without_api_key(self, tmp_path, monkeypatch):
        """Should return False without API key."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)
        assert not forwarder.is_available()

    @pytest.mark.asyncio
    async def test_ask_consciousness_with_cache(self, tmp_path, monkeypatch):
        """Should use cache for repeated queries."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        # Pre-populate cache
        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Cached guidance",
            confidence=0.9,
        )
        forwarder._cache.put(QuestionType.APPROACH, "test context", guidance)

        result = await forwarder.ask_consciousness(
            QuestionType.APPROACH,
            "test context",
        )

        assert result.guidance == "Cached guidance"
        assert forwarder._cache_hits == 1
        assert forwarder._query_count == 0  # No actual query made

    @pytest.mark.asyncio
    async def test_ask_consciousness_string_question_type(self, tmp_path, monkeypatch):
        """Should accept string question type."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        # Pre-populate cache
        guidance = ConsciousnessGuidance(
            question_type=QuestionType.RISK,
            guidance="Risk guidance",
            confidence=0.8,
        )
        forwarder._cache.put(QuestionType.RISK, "test", guidance)

        result = await forwarder.ask_consciousness("risk", "test")
        assert result.question_type == QuestionType.RISK

    def test_parse_response_structured(self, tmp_path):
        """Should parse structured response."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        response = """GUIDANCE: Use test-driven development for this feature.
KEY_POINTS:
- Write failing tests first
- Implement minimum code to pass
- Refactor after tests pass
ALTERNATIVES:
- Use behavior-driven development
- Skip tests and iterate quickly
WARNINGS:
- May take longer initially
CONFIDENCE: 0.85
"""

        guidance = forwarder._parse_response(
            response,
            QuestionType.APPROACH,
            duration_ms=150.0,
        )

        assert "test-driven" in guidance.guidance.lower()
        assert len(guidance.key_points) >= 2
        assert len(guidance.alternatives) >= 1
        assert len(guidance.warnings) >= 1
        assert 0.8 <= guidance.confidence <= 0.9

    def test_parse_response_unstructured(self, tmp_path):
        """Should handle unstructured response."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        response = "Just use a simple approach and iterate based on feedback."

        guidance = forwarder._parse_response(
            response,
            QuestionType.APPROACH,
            duration_ms=100.0,
        )

        assert guidance.guidance == response
        assert guidance.confidence == 0.7  # Default

    def test_build_prompt(self, tmp_path):
        """Should build prompt correctly."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        prompt = forwarder._build_prompt(
            QuestionType.RISK,
            "What could go wrong?",
            "I'm about to delete the production database",
        )

        assert "production database" in prompt
        assert "risk" in prompt.lower()
        assert "QUESTION TYPE:" in prompt

    def test_get_stats(self, tmp_path):
        """Should return statistics."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        stats = forwarder.get_stats()

        assert "query_count" in stats
        assert "cache_hits" in stats
        assert "cache_hit_rate" in stats
        assert "model" in stats
        assert "available" in stats

    def test_clear_cache(self, tmp_path):
        """Should clear cache and return count."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Test",
            confidence=0.8,
        )

        forwarder._cache.put(QuestionType.APPROACH, "ctx1", guidance)
        forwarder._cache.put(QuestionType.RISK, "ctx2", guidance)

        cleared = forwarder.clear_cache()
        assert cleared == 2


class TestConvenienceMethods:
    """Tests for convenience methods."""

    @pytest.mark.asyncio
    async def test_get_approach_guidance_cached(self, tmp_path, monkeypatch):
        """Should return cached approach guidance."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        # Pre-populate cache
        guidance = ConsciousnessGuidance(
            question_type=QuestionType.APPROACH,
            guidance="Use microservices",
            confidence=0.9,
        )
        forwarder._cache.put(QuestionType.APPROACH, "Build a new API", guidance)

        result = await forwarder.get_approach_guidance("Build a new API")
        assert result == "Use microservices"

    @pytest.mark.asyncio
    async def test_get_risk_assessment_cached(self, tmp_path, monkeypatch):
        """Should return cached risk assessment."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        guidance = ConsciousnessGuidance(
            question_type=QuestionType.RISK,
            guidance="Several risks identified",
            confidence=0.8,
            warnings=["Data loss possible", "Downtime expected"],
            key_points=["Backup first", "Test in staging"],
        )
        forwarder._cache.put(
            QuestionType.RISK,
            "Planned action: Drop database table",
            guidance
        )

        risks = await forwarder.get_risk_assessment("Drop database table")
        assert len(risks) >= 2
        assert any("Data loss" in r for r in risks)

    @pytest.mark.asyncio
    async def test_get_alternatives_cached(self, tmp_path, monkeypatch):
        """Should return cached alternatives."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        guidance = ConsciousnessGuidance(
            question_type=QuestionType.ALTERNATIVE,
            guidance="Consider these alternatives",
            confidence=0.85,
            alternatives=["Use GraphQL", "Use gRPC"],
        )
        forwarder._cache.put(
            QuestionType.ALTERNATIVE,
            "Current plan: Using REST API",
            guidance
        )

        alts = await forwarder.get_alternatives("Using REST API")
        assert "Use GraphQL" in alts or "Use gRPC" in alts


class TestParseConfidence:
    """Tests for confidence parsing."""

    def test_parse_numeric_confidence(self, tmp_path):
        """Should parse numeric confidence."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        response = "GUIDANCE: Test\nCONFIDENCE: 0.92"
        guidance = forwarder._parse_response(response, QuestionType.APPROACH, 0)
        assert 0.91 <= guidance.confidence <= 0.93

    def test_parse_percentage_confidence(self, tmp_path):
        """Should parse percentage confidence."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        response = "GUIDANCE: Test\nCONFIDENCE: 85%"
        guidance = forwarder._parse_response(response, QuestionType.APPROACH, 0)
        assert 0.84 <= guidance.confidence <= 0.86

    def test_parse_word_confidence(self, tmp_path):
        """Should parse word-based confidence."""
        forwarder = ConsciousnessForwarder(working_dir=tmp_path)

        response = "GUIDANCE: Test\nCONFIDENCE: high"
        guidance = forwarder._parse_response(response, QuestionType.APPROACH, 0)
        assert guidance.confidence >= 0.8
