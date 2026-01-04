"""
Pattern Learner - Extracts and applies learned patterns from outcomes.

Identifies recurring patterns in:
- Observation -> Action -> Outcome sequences
- Successful vs failed approaches
- Time-based patterns (certain actions work better at certain times)
- Context-based patterns (certain file types need certain actions)
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from .tracker import OutcomeTracker, _compute_observation_hash

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of patterns that can be learned."""
    OBSERVATION_ACTION = "observation_action"  # When X observed, do Y
    ACTION_SEQUENCE = "action_sequence"  # After action X, action Y often follows
    FAILURE_RECOVERY = "failure_recovery"  # When X fails, Y often works
    TIME_BASED = "time_based"  # Action X works better at certain times
    CONTEXT_BASED = "context_based"  # Action X works for context Y


@dataclass
class Pattern:
    """Represents a learned pattern."""

    id: Optional[int] = None
    pattern_type: PatternType = PatternType.OBSERVATION_ACTION
    trigger_hash: str = ""
    trigger_description: str = ""
    action_type: str = ""
    action_template: str = ""
    success_rate: float = 0.0
    occurrences: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "trigger_hash": self.trigger_hash,
            "trigger_description": self.trigger_description,
            "action_type": self.action_type,
            "action_template": self.action_template,
            "success_rate": self.success_rate,
            "occurrences": self.occurrences,
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
        }

    @property
    def is_reliable(self) -> bool:
        """Check if this pattern has enough data to be reliable."""
        return self.occurrences >= 3 and self.success_rate >= 0.6


@dataclass
class Suggestion:
    """A suggestion based on learned patterns."""

    action_type: str
    action_template: str
    confidence: float
    reasoning: str
    pattern: Optional[Pattern] = None
    source: str = "pattern"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "action_template": self.action_template,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "pattern_id": self.pattern.id if self.pattern else None,
            "source": self.source,
        }


class PatternLearner:
    """
    Learns patterns from outcome history and provides suggestions.

    Analyzes the outcome database to identify:
    - What actions tend to succeed for certain observations
    - What action sequences work well together
    - How to recover from failures
    """

    def __init__(
        self,
        db_path: str | Path,
        outcome_tracker: Optional[OutcomeTracker] = None,
    ):
        """
        Initialize the pattern learner.

        Args:
            db_path: Path to the SQLite database
            outcome_tracker: Optional shared OutcomeTracker instance
        """
        self.db_path = Path(db_path)
        self.outcome_tracker = outcome_tracker or OutcomeTracker(db_path)
        self._connection: Optional[aiosqlite.Connection] = None

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def extract_patterns(
        self,
        min_occurrences: int = 3,
        min_success_rate: float = 0.5,
    ) -> list[Pattern]:
        """
        Extract patterns from the outcome history.

        Analyzes outcomes to find recurring patterns that can inform
        future decisions.

        Args:
            min_occurrences: Minimum occurrences to consider a pattern
            min_success_rate: Minimum success rate to consider useful

        Returns:
            List of extracted patterns
        """
        conn = await self._get_connection()
        patterns = []

        # Extract observation -> action patterns
        cursor = await conn.execute(
            """
            SELECT
                observation_hash,
                action_type,
                COUNT(*) as occurrences,
                SUM(CASE WHEN result_type IN ('success', 'partial') THEN 1 ELSE 0 END) as successes,
                MAX(observation) as sample_observation,
                MAX(action_details) as sample_action
            FROM outcomes
            GROUP BY observation_hash, action_type
            HAVING occurrences >= ?
            """,
            (min_occurrences,),
        )

        rows = await cursor.fetchall()
        for row in rows:
            success_rate = (row["successes"] or 0) / row["occurrences"]
            if success_rate >= min_success_rate:
                patterns.append(
                    Pattern(
                        pattern_type=PatternType.OBSERVATION_ACTION,
                        trigger_hash=row["observation_hash"],
                        trigger_description=row["sample_observation"][:200] if row["sample_observation"] else "",
                        action_type=row["action_type"],
                        action_template=row["sample_action"][:500] if row["sample_action"] else "",
                        success_rate=success_rate,
                        occurrences=row["occurrences"],
                        last_updated=datetime.now(timezone.utc),
                    )
                )

        logger.info(f"Extracted {len(patterns)} patterns from outcome history")
        return patterns

    async def update_patterns(self) -> int:
        """
        Update stored patterns based on recent outcomes.

        Recalculates pattern statistics and stores/updates them in the database.

        Returns:
            Number of patterns updated
        """
        conn = await self._get_connection()

        # Extract current patterns
        patterns = await self.extract_patterns()

        updated = 0
        for pattern in patterns:
            # Check if pattern exists
            cursor = await conn.execute(
                """
                SELECT id FROM patterns
                WHERE trigger_hash = ? AND action_type = ?
                """,
                (pattern.trigger_hash, pattern.action_type),
            )
            existing = await cursor.fetchone()

            if existing:
                # Update existing pattern
                await conn.execute(
                    """
                    UPDATE patterns SET
                        success_rate = ?,
                        occurrences = ?,
                        last_updated = ?,
                        action_template = ?
                    WHERE id = ?
                    """,
                    (
                        pattern.success_rate,
                        pattern.occurrences,
                        time.time(),
                        pattern.action_template,
                        existing["id"],
                    ),
                )
            else:
                # Insert new pattern
                await conn.execute(
                    """
                    INSERT INTO patterns (
                        pattern_type, trigger_hash, trigger_description,
                        action_type, action_template, success_rate,
                        occurrences, last_updated, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pattern.pattern_type.value,
                        pattern.trigger_hash,
                        pattern.trigger_description,
                        pattern.action_type,
                        pattern.action_template,
                        pattern.success_rate,
                        pattern.occurrences,
                        time.time(),
                        json.dumps(pattern.metadata),
                    ),
                )
            updated += 1

        await conn.commit()
        logger.info(f"Updated {updated} patterns in database")
        return updated

    async def suggest_from_patterns(
        self,
        observation: str,
        max_suggestions: int = 3,
    ) -> list[Suggestion]:
        """
        Suggest actions based on learned patterns.

        Args:
            observation: Current observation to match
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggestions sorted by confidence
        """
        conn = await self._get_connection()
        observation_hash = _compute_observation_hash(observation)

        # Find matching patterns
        cursor = await conn.execute(
            """
            SELECT * FROM patterns
            WHERE trigger_hash = ?
            ORDER BY success_rate DESC, occurrences DESC
            LIMIT ?
            """,
            (observation_hash, max_suggestions * 2),  # Get extra for filtering
        )

        rows = await cursor.fetchall()
        suggestions = []

        for row in rows:
            pattern = Pattern(
                id=row["id"],
                pattern_type=PatternType(row["pattern_type"]),
                trigger_hash=row["trigger_hash"],
                trigger_description=row["trigger_description"],
                action_type=row["action_type"],
                action_template=row["action_template"],
                success_rate=row["success_rate"],
                occurrences=row["occurrences"],
                last_updated=datetime.fromtimestamp(row["last_updated"], tz=timezone.utc),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

            if pattern.is_reliable:
                # Calculate confidence based on pattern reliability
                confidence = min(0.95, pattern.success_rate * (1 - 1 / (pattern.occurrences + 1)))

                suggestions.append(
                    Suggestion(
                        action_type=pattern.action_type,
                        action_template=pattern.action_template,
                        confidence=confidence,
                        reasoning=(
                            f"Pattern matched: {pattern.action_type} succeeded "
                            f"{pattern.success_rate:.0%} of the time "
                            f"in {pattern.occurrences} similar situations"
                        ),
                        pattern=pattern,
                    )
                )

        # Sort by confidence and limit
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:max_suggestions]

    async def get_failure_patterns(
        self,
        action_type: str,
    ) -> list[dict[str, Any]]:
        """
        Get common failure patterns for an action type.

        Useful for understanding why certain actions fail.

        Args:
            action_type: Action type to analyze

        Returns:
            List of failure pattern summaries
        """
        conn = await self._get_connection()

        cursor = await conn.execute(
            """
            SELECT
                error_message,
                COUNT(*) as count,
                AVG(execution_time) as avg_time
            FROM outcomes
            WHERE action_type = ?
              AND result_type IN ('failure', 'error', 'timeout')
              AND error_message IS NOT NULL
            GROUP BY error_message
            ORDER BY count DESC
            LIMIT 10
            """,
            (action_type,),
        )

        rows = await cursor.fetchall()
        return [
            {
                "error": row["error_message"],
                "count": row["count"],
                "avg_execution_time": row["avg_time"],
            }
            for row in rows
        ]

    async def get_pattern_by_id(self, pattern_id: int) -> Optional[Pattern]:
        """Get a specific pattern by ID."""
        conn = await self._get_connection()

        cursor = await conn.execute(
            "SELECT * FROM patterns WHERE id = ?",
            (pattern_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return Pattern(
            id=row["id"],
            pattern_type=PatternType(row["pattern_type"]),
            trigger_hash=row["trigger_hash"],
            trigger_description=row["trigger_description"],
            action_type=row["action_type"],
            action_template=row["action_template"],
            success_rate=row["success_rate"],
            occurrences=row["occurrences"],
            last_updated=datetime.fromtimestamp(row["last_updated"], tz=timezone.utc),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    async def get_all_patterns(
        self,
        min_success_rate: float = 0.0,
        limit: int = 100,
    ) -> list[Pattern]:
        """
        Get all stored patterns.

        Args:
            min_success_rate: Filter by minimum success rate
            limit: Maximum patterns to return

        Returns:
            List of patterns
        """
        conn = await self._get_connection()

        cursor = await conn.execute(
            """
            SELECT * FROM patterns
            WHERE success_rate >= ?
            ORDER BY success_rate DESC, occurrences DESC
            LIMIT ?
            """,
            (min_success_rate, limit),
        )

        rows = await cursor.fetchall()
        return [
            Pattern(
                id=row["id"],
                pattern_type=PatternType(row["pattern_type"]),
                trigger_hash=row["trigger_hash"],
                trigger_description=row["trigger_description"],
                action_type=row["action_type"],
                action_template=row["action_template"],
                success_rate=row["success_rate"],
                occurrences=row["occurrences"],
                last_updated=datetime.fromtimestamp(row["last_updated"], tz=timezone.utc),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            for row in rows
        ]

    async def get_statistics(self) -> dict[str, Any]:
        """Get overall pattern learning statistics."""
        conn = await self._get_connection()

        cursor = await conn.execute("SELECT COUNT(*) FROM patterns")
        row = await cursor.fetchone()
        total_patterns = row[0] if row else 0

        cursor = await conn.execute(
            "SELECT COUNT(*) FROM patterns WHERE success_rate >= 0.6 AND occurrences >= 3"
        )
        row = await cursor.fetchone()
        reliable_patterns = row[0] if row else 0

        cursor = await conn.execute("SELECT AVG(success_rate) FROM patterns")
        row = await cursor.fetchone()
        avg_success_rate = row[0] if row else 0

        cursor = await conn.execute(
            """
            SELECT action_type, COUNT(*) as count
            FROM patterns
            GROUP BY action_type
            ORDER BY count DESC
            """
        )
        rows = await cursor.fetchall()
        by_action_type = {row["action_type"]: row["count"] for row in rows}

        return {
            "total_patterns": total_patterns,
            "reliable_patterns": reliable_patterns,
            "average_success_rate": avg_success_rate,
            "patterns_by_action_type": by_action_type,
        }

    async def cleanup_stale_patterns(
        self,
        max_age_days: int = 90,
        min_occurrences: int = 2,
    ) -> int:
        """
        Remove stale or unreliable patterns.

        Args:
            max_age_days: Remove patterns not updated in this many days
            min_occurrences: Remove patterns with fewer occurrences

        Returns:
            Number of patterns removed
        """
        conn = await self._get_connection()

        cutoff = time.time() - (max_age_days * 24 * 3600)

        cursor = await conn.execute(
            """
            DELETE FROM patterns
            WHERE last_updated < ? OR occurrences < ?
            """,
            (cutoff, min_occurrences),
        )

        deleted = cursor.rowcount
        await conn.commit()

        logger.info(f"Cleaned up {deleted} stale patterns")
        return deleted
