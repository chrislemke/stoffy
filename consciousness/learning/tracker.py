"""
Outcome Tracker - Records and analyzes action outcomes for learning.

Tracks:
- Action execution results (success/failure)
- Execution time and errors
- Context at time of execution
- Similarity matching for pattern recognition
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

logger = logging.getLogger(__name__)


class OutcomeType(str, Enum):
    """Classification of outcome results."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class Outcome:
    """Represents the outcome of an executed action."""

    id: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observation: str = ""
    observation_hash: str = ""  # For similarity matching
    action_type: str = ""
    action_details: str = ""
    result_type: OutcomeType = OutcomeType.FAILURE
    result_output: str = ""
    error_message: Optional[str] = None
    execution_time: float = 0.0
    confidence_used: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "observation": self.observation[:500] if self.observation else "",
            "action_type": self.action_type,
            "action_details": self.action_details[:500] if self.action_details else "",
            "result_type": self.result_type.value,
            "result_output": self.result_output[:500] if self.result_output else "",
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "confidence_used": self.confidence_used,
            "context": self.context,
        }

    @property
    def success(self) -> bool:
        return self.result_type in (OutcomeType.SUCCESS, OutcomeType.PARTIAL)


def _compute_observation_hash(observation: str) -> str:
    """
    Compute a simple hash for observation similarity matching.

    Uses key terms extraction for fuzzy matching rather than exact hashing.
    """
    import hashlib
    import re

    # Extract key terms (file extensions, action words, paths)
    terms = set()

    # File extensions
    extensions = re.findall(r'\.([a-zA-Z0-9]+)', observation)
    terms.update(ext.lower() for ext in extensions)

    # Common action words
    action_words = ['created', 'modified', 'deleted', 'changed', 'added',
                   'removed', 'updated', 'new', 'error', 'failed', 'success']
    for word in action_words:
        if word in observation.lower():
            terms.add(word)

    # Directory names (common ones)
    dir_patterns = ['src', 'test', 'docs', 'config', 'lib', 'build', 'dist',
                   'knowledge', 'templates', 'indices', 'consciousness']
    for pattern in dir_patterns:
        if pattern in observation.lower():
            terms.add(pattern)

    # Sort and join for consistent hashing
    term_string = '|'.join(sorted(terms))
    return hashlib.md5(term_string.encode()).hexdigest()[:16]


class OutcomeTracker:
    """
    Tracks action outcomes and provides historical analysis.

    Uses SQLite for persistent storage and provides methods for:
    - Recording new outcomes
    - Calculating success rates by action type
    - Finding similar past outcomes
    - Aggregating statistics for confidence adjustment
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize the outcome tracker.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = Path(db_path)
        self._connection: Optional[aiosqlite.Connection] = None

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def initialize(self) -> None:
        """Initialize the database schema for outcome tracking."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = await self._get_connection()
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                observation TEXT NOT NULL,
                observation_hash TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_details TEXT NOT NULL,
                result_type TEXT NOT NULL,
                result_output TEXT DEFAULT '',
                error_message TEXT,
                execution_time REAL DEFAULT 0.0,
                confidence_used REAL DEFAULT 0.0,
                context TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_outcomes_action_type
                ON outcomes(action_type);
            CREATE INDEX IF NOT EXISTS idx_outcomes_result_type
                ON outcomes(result_type);
            CREATE INDEX IF NOT EXISTS idx_outcomes_observation_hash
                ON outcomes(observation_hash);
            CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp
                ON outcomes(timestamp);

            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                trigger_hash TEXT NOT NULL,
                trigger_description TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_template TEXT NOT NULL,
                success_rate REAL DEFAULT 0.0,
                occurrences INTEGER DEFAULT 0,
                last_updated REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_patterns_trigger_hash
                ON patterns(trigger_hash);
            CREATE INDEX IF NOT EXISTS idx_patterns_action_type
                ON patterns(action_type);
            CREATE INDEX IF NOT EXISTS idx_patterns_success_rate
                ON patterns(success_rate);
            """
        )
        await conn.commit()
        logger.info("Outcome tracker database initialized")

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def record_outcome(
        self,
        observation: str,
        action_type: str,
        action_details: str,
        success: bool,
        output: str = "",
        error: Optional[str] = None,
        execution_time: float = 0.0,
        confidence_used: float = 0.0,
        context: Optional[dict[str, Any]] = None,
    ) -> int:
        """
        Record an action outcome to the database.

        Args:
            observation: The observation that triggered the action
            action_type: Type of action (e.g., 'claude_code', 'update_indices')
            action_details: Details/prompt of the action
            success: Whether the action succeeded
            output: Output from the action
            error: Error message if any
            execution_time: Time taken in seconds
            confidence_used: Confidence level at decision time
            context: Additional context dictionary

        Returns:
            The ID of the recorded outcome
        """
        conn = await self._get_connection()

        observation_hash = _compute_observation_hash(observation)

        # Determine result type
        if error:
            if "timeout" in error.lower():
                result_type = OutcomeType.TIMEOUT
            else:
                result_type = OutcomeType.ERROR
        elif success:
            result_type = OutcomeType.SUCCESS
        else:
            result_type = OutcomeType.FAILURE

        cursor = await conn.execute(
            """
            INSERT INTO outcomes (
                timestamp, observation, observation_hash, action_type,
                action_details, result_type, result_output, error_message,
                execution_time, confidence_used, context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                observation,
                observation_hash,
                action_type,
                action_details,
                result_type.value,
                output,
                error,
                execution_time,
                confidence_used,
                json.dumps(context or {}),
            ),
        )
        await conn.commit()

        outcome_id = cursor.lastrowid or 0
        logger.debug(
            f"Recorded outcome: {action_type} -> {result_type.value} (id={outcome_id})"
        )
        return outcome_id

    async def get_success_rate(
        self,
        action_type: str,
        time_window_hours: Optional[float] = None,
    ) -> tuple[float, int]:
        """
        Calculate historical success rate for an action type.

        Args:
            action_type: The action type to check
            time_window_hours: Optional time window to limit analysis

        Returns:
            Tuple of (success_rate, total_count)
        """
        conn = await self._get_connection()

        if time_window_hours:
            cutoff = time.time() - (time_window_hours * 3600)
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN result_type IN ('success', 'partial') THEN 1 ELSE 0 END) as successes
                FROM outcomes
                WHERE action_type = ? AND timestamp >= ?
                """,
                (action_type, cutoff),
            )
        else:
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN result_type IN ('success', 'partial') THEN 1 ELSE 0 END) as successes
                FROM outcomes
                WHERE action_type = ?
                """,
                (action_type,),
            )

        row = await cursor.fetchone()
        if not row or row["total"] == 0:
            return 0.5, 0  # Default to 50% when no data

        total = row["total"]
        successes = row["successes"] or 0
        return successes / total, total

    async def get_similar_outcomes(
        self,
        observation: str,
        limit: int = 10,
    ) -> list[Outcome]:
        """
        Find outcomes with similar observations.

        Uses observation hash for efficient lookup of similar past situations.

        Args:
            observation: The current observation to match
            limit: Maximum number of outcomes to return

        Returns:
            List of similar past outcomes
        """
        conn = await self._get_connection()
        observation_hash = _compute_observation_hash(observation)

        cursor = await conn.execute(
            """
            SELECT * FROM outcomes
            WHERE observation_hash = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (observation_hash, limit),
        )

        rows = await cursor.fetchall()
        return [
            Outcome(
                id=row["id"],
                timestamp=datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
                observation=row["observation"],
                observation_hash=row["observation_hash"],
                action_type=row["action_type"],
                action_details=row["action_details"],
                result_type=OutcomeType(row["result_type"]),
                result_output=row["result_output"],
                error_message=row["error_message"],
                execution_time=row["execution_time"],
                confidence_used=row["confidence_used"],
                context=json.loads(row["context"]) if row["context"] else {},
            )
            for row in rows
        ]

    async def get_action_statistics(
        self,
        time_window_hours: float = 168,  # 1 week default
    ) -> dict[str, dict[str, Any]]:
        """
        Get aggregated statistics for all action types.

        Args:
            time_window_hours: Time window for statistics

        Returns:
            Dictionary mapping action_type to statistics
        """
        conn = await self._get_connection()
        cutoff = time.time() - (time_window_hours * 3600)

        cursor = await conn.execute(
            """
            SELECT
                action_type,
                COUNT(*) as total,
                SUM(CASE WHEN result_type IN ('success', 'partial') THEN 1 ELSE 0 END) as successes,
                AVG(execution_time) as avg_execution_time,
                AVG(confidence_used) as avg_confidence
            FROM outcomes
            WHERE timestamp >= ?
            GROUP BY action_type
            """,
            (cutoff,),
        )

        rows = await cursor.fetchall()
        return {
            row["action_type"]: {
                "total": row["total"],
                "successes": row["successes"] or 0,
                "success_rate": (row["successes"] or 0) / row["total"] if row["total"] > 0 else 0,
                "avg_execution_time": row["avg_execution_time"] or 0,
                "avg_confidence": row["avg_confidence"] or 0,
            }
            for row in rows
        }

    async def calculate_confidence_adjustment(
        self,
        action_type: str,
        base_confidence: float,
        observation: str,
    ) -> tuple[float, str]:
        """
        Calculate adjusted confidence based on historical outcomes.

        Args:
            action_type: Type of action being considered
            base_confidence: Original confidence from decision engine
            observation: Current observation for similarity matching

        Returns:
            Tuple of (adjusted_confidence, reasoning)
        """
        # Get overall success rate for this action type
        success_rate, total_count = await self.get_success_rate(action_type)

        # Get similar outcomes
        similar_outcomes = await self.get_similar_outcomes(observation, limit=5)

        adjustments = []
        adjusted = base_confidence

        # Adjust based on overall success rate (if we have enough data)
        if total_count >= 5:
            if success_rate > 0.8:
                # High success rate - boost confidence slightly
                boost = min(0.15, (success_rate - 0.5) * 0.3)
                adjusted = min(1.0, adjusted + boost)
                adjustments.append(
                    f"Historical success rate {success_rate:.0%} (n={total_count}) -> +{boost:.2f}"
                )
            elif success_rate < 0.4:
                # Low success rate - reduce confidence
                penalty = min(0.2, (0.5 - success_rate) * 0.4)
                adjusted = max(0.1, adjusted - penalty)
                adjustments.append(
                    f"Historical success rate {success_rate:.0%} (n={total_count}) -> -{penalty:.2f}"
                )

        # Adjust based on similar past outcomes
        if similar_outcomes:
            similar_success = sum(1 for o in similar_outcomes if o.success)
            similar_rate = similar_success / len(similar_outcomes)

            if len(similar_outcomes) >= 3:
                if similar_rate > 0.7:
                    boost = 0.1
                    adjusted = min(1.0, adjusted + boost)
                    adjustments.append(
                        f"Similar situations succeeded {similar_rate:.0%} of time -> +{boost:.2f}"
                    )
                elif similar_rate < 0.3:
                    penalty = 0.15
                    adjusted = max(0.1, adjusted - penalty)
                    adjustments.append(
                        f"Similar situations failed {1-similar_rate:.0%} of time -> -{penalty:.2f}"
                    )

        reasoning = (
            f"Base confidence: {base_confidence:.2f}. "
            + " ".join(adjustments)
            + f" Final: {adjusted:.2f}"
            if adjustments
            else f"Base confidence: {base_confidence:.2f} (no historical adjustments)"
        )

        return adjusted, reasoning

    async def get_recent_outcomes(
        self,
        limit: int = 50,
        action_type: Optional[str] = None,
    ) -> list[Outcome]:
        """
        Get recent outcomes, optionally filtered by action type.

        Args:
            limit: Maximum number of outcomes to return
            action_type: Optional filter by action type

        Returns:
            List of recent outcomes
        """
        conn = await self._get_connection()

        if action_type:
            cursor = await conn.execute(
                """
                SELECT * FROM outcomes
                WHERE action_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (action_type, limit),
            )
        else:
            cursor = await conn.execute(
                """
                SELECT * FROM outcomes
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = await cursor.fetchall()
        return [
            Outcome(
                id=row["id"],
                timestamp=datetime.fromtimestamp(row["timestamp"], tz=timezone.utc),
                observation=row["observation"],
                observation_hash=row["observation_hash"],
                action_type=row["action_type"],
                action_details=row["action_details"],
                result_type=OutcomeType(row["result_type"]),
                result_output=row["result_output"],
                error_message=row["error_message"],
                execution_time=row["execution_time"],
                confidence_used=row["confidence_used"],
                context=json.loads(row["context"]) if row["context"] else {},
            )
            for row in rows
        ]

    async def cleanup_old_outcomes(
        self,
        max_age_days: int = 30,
        max_entries: int = 10000,
    ) -> int:
        """
        Clean up old outcome entries.

        Args:
            max_age_days: Maximum age of entries to keep
            max_entries: Maximum total entries to keep

        Returns:
            Number of entries deleted
        """
        conn = await self._get_connection()
        deleted = 0

        # Delete by age
        cutoff = time.time() - (max_age_days * 24 * 3600)
        cursor = await conn.execute(
            "DELETE FROM outcomes WHERE timestamp < ?",
            (cutoff,),
        )
        deleted += cursor.rowcount

        # Delete excess entries
        cursor = await conn.execute("SELECT COUNT(*) FROM outcomes")
        row = await cursor.fetchone()
        count = row[0] if row else 0

        if count > max_entries:
            to_delete = count - max_entries
            await conn.execute(
                """
                DELETE FROM outcomes
                WHERE id IN (
                    SELECT id FROM outcomes
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
                """,
                (to_delete,),
            )
            deleted += to_delete

        await conn.commit()
        logger.info(f"Cleaned up {deleted} old outcome entries")
        return deleted
