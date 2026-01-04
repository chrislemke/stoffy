"""
Outcome Tracker - Records and analyzes action outcomes for learning.

Tracks:
- Action execution results (success/failure)
- Execution time and errors
- Context at time of execution
- Similarity matching for pattern recognition
- Tiered intelligence execution (Local, Claude Code, Claude Flow, Gemini)
- Expected vs actual outcome matching for learning accuracy
- Dream Cycle processing status for pattern distillation
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class ExecutorTier(IntEnum):
    """Execution tier levels for tiered intelligence."""
    LOCAL = 1       # Local heuristics, no LLM
    CLAUDE_CODE = 2 # Claude Code for standard tasks
    CLAUDE_FLOW = 3 # Claude Flow for complex orchestration
    GEMINI = 4      # External Gemini for specialized tasks


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
    # Tiered intelligence tracking
    executor_tier: int = ExecutorTier.CLAUDE_CODE  # Default to Claude Code tier
    # Expected vs actual outcome tracking
    expected_outcome: str = ""
    outcome_match: bool = True  # Did actual match expected?
    # Dream Cycle processing
    processed_by_dreamer: bool = False
    dreamer_insights: str = ""

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
            "executor_tier": self.executor_tier,
            "expected_outcome": self.expected_outcome[:500] if self.expected_outcome else "",
            "outcome_match": self.outcome_match,
            "processed_by_dreamer": self.processed_by_dreamer,
            "dreamer_insights": self.dreamer_insights[:500] if self.dreamer_insights else "",
        }

    @property
    def success(self) -> bool:
        return self.result_type in (OutcomeType.SUCCESS, OutcomeType.PARTIAL)

    @property
    def tier_name(self) -> str:
        """Get human-readable tier name."""
        tier_names = {
            ExecutorTier.LOCAL: "Local",
            ExecutorTier.CLAUDE_CODE: "Claude Code",
            ExecutorTier.CLAUDE_FLOW: "Claude Flow",
            ExecutorTier.GEMINI: "Gemini",
        }
        return tier_names.get(self.executor_tier, f"Unknown (Tier {self.executor_tier})")


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

        # Step 1: Create tables with basic columns (backward compatible)
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

        # Step 2: Migrate schema to add new columns (for existing databases)
        await self._migrate_schema()

        # Step 3: Create indexes on new columns (after migration ensures columns exist)
        try:
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_outcomes_executor_tier ON outcomes(executor_tier)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_outcomes_processed_by_dreamer ON outcomes(processed_by_dreamer)"
            )
            await conn.commit()
        except Exception as e:
            logger.debug(f"Index creation note: {e}")

        logger.info("Outcome tracker database initialized")

    async def _migrate_schema(self) -> None:
        """Migrate schema to add new columns if needed for backward compatibility."""
        conn = await self._get_connection()

        # Check which columns exist
        cursor = await conn.execute("PRAGMA table_info(outcomes)")
        existing_columns = {row[1] for row in await cursor.fetchall()}

        migrations_needed = []

        # Define new columns with their defaults
        new_columns = [
            ("executor_tier", "INTEGER DEFAULT 2"),
            ("expected_outcome", "TEXT DEFAULT ''"),
            ("outcome_match", "INTEGER DEFAULT 1"),
            ("processed_by_dreamer", "INTEGER DEFAULT 0"),
            ("dreamer_insights", "TEXT DEFAULT ''"),
        ]

        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                migrations_needed.append(
                    f"ALTER TABLE outcomes ADD COLUMN {column_name} {column_def}"
                )

        if migrations_needed:
            for migration in migrations_needed:
                try:
                    await conn.execute(migration)
                    logger.info(f"Schema migration executed: {migration}")
                except Exception as e:
                    logger.warning(f"Migration skipped (may already exist): {e}")

            await conn.commit()
            logger.info(f"Applied {len(migrations_needed)} schema migrations")

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
        executor_tier: int = ExecutorTier.CLAUDE_CODE,
        expected_outcome: str = "",
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
            executor_tier: Tier that executed the action (1=Local, 2=Claude Code, 3=Claude Flow, 4=Gemini)
            expected_outcome: What was expected to happen

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

        # Determine if outcome matched expectation
        outcome_match = True
        if expected_outcome:
            # Simple heuristic: if expected and we failed, or unexpected error
            if not success and expected_outcome.lower() not in ("failure", "error"):
                outcome_match = False
            # Could be enhanced with semantic similarity in the future

        cursor = await conn.execute(
            """
            INSERT INTO outcomes (
                timestamp, observation, observation_hash, action_type,
                action_details, result_type, result_output, error_message,
                execution_time, confidence_used, context,
                executor_tier, expected_outcome, outcome_match,
                processed_by_dreamer, dreamer_insights
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                executor_tier,
                expected_outcome,
                1 if outcome_match else 0,
                0,  # processed_by_dreamer defaults to False
                "",  # dreamer_insights defaults to empty
            ),
        )
        await conn.commit()

        outcome_id = cursor.lastrowid or 0
        tier_name = ExecutorTier(executor_tier).name if executor_tier in [1, 2, 3, 4] else f"Tier-{executor_tier}"
        logger.debug(
            f"Recorded outcome: {action_type} -> {result_type.value} (id={outcome_id}, tier={tier_name})"
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
        return [self._row_to_outcome(row) for row in rows]

    def _row_to_outcome(self, row: aiosqlite.Row) -> Outcome:
        """Convert a database row to an Outcome object."""
        # Handle backward compatibility for rows without new columns
        executor_tier = row["executor_tier"] if "executor_tier" in row.keys() else ExecutorTier.CLAUDE_CODE
        expected_outcome = row["expected_outcome"] if "expected_outcome" in row.keys() else ""
        outcome_match = bool(row["outcome_match"]) if "outcome_match" in row.keys() else True
        processed_by_dreamer = bool(row["processed_by_dreamer"]) if "processed_by_dreamer" in row.keys() else False
        dreamer_insights = row["dreamer_insights"] if "dreamer_insights" in row.keys() else ""

        return Outcome(
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
            executor_tier=executor_tier,
            expected_outcome=expected_outcome,
            outcome_match=outcome_match,
            processed_by_dreamer=processed_by_dreamer,
            dreamer_insights=dreamer_insights,
        )

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
        return [self._row_to_outcome(row) for row in rows]

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

    # ============================================================
    # Dream Cycle Support Methods
    # ============================================================

    async def get_outcomes_for_dreaming(self, limit: int = 100) -> list[Outcome]:
        """
        Get unprocessed outcomes for the Dream Cycle.

        Returns outcomes that haven't been processed by the Dreamer yet,
        ordered by timestamp (oldest first) for sequential processing.

        Args:
            limit: Maximum number of outcomes to return

        Returns:
            List of unprocessed outcomes ready for dream analysis
        """
        conn = await self._get_connection()

        cursor = await conn.execute(
            """
            SELECT * FROM outcomes
            WHERE processed_by_dreamer = 0
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (limit,),
        )

        rows = await cursor.fetchall()
        logger.debug(f"Retrieved {len(rows)} outcomes for dreaming")
        return [self._row_to_outcome(row) for row in rows]

    async def mark_as_dreamed(
        self,
        outcome_ids: list[int],
        insights: str,
    ) -> None:
        """
        Mark outcomes as processed by Dreamer with insights.

        Args:
            outcome_ids: List of outcome IDs that were processed
            insights: Consolidated insights from the dream analysis
        """
        if not outcome_ids:
            return

        conn = await self._get_connection()

        # Use parameterized query with placeholders for each ID
        placeholders = ",".join("?" * len(outcome_ids))
        await conn.execute(
            f"""
            UPDATE outcomes
            SET processed_by_dreamer = 1,
                dreamer_insights = ?
            WHERE id IN ({placeholders})
            """,
            [insights] + outcome_ids,
        )
        await conn.commit()
        logger.info(f"Marked {len(outcome_ids)} outcomes as dreamed")

    async def get_undreamed_count(self) -> int:
        """Get count of outcomes not yet processed by Dreamer."""
        conn = await self._get_connection()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM outcomes WHERE processed_by_dreamer = 0"
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ============================================================
    # Tier Statistics Methods
    # ============================================================

    async def get_tier_statistics(
        self,
        time_window_hours: float = 168,  # 1 week default
    ) -> dict[int, dict[str, Any]]:
        """
        Get success rates and stats per execution tier.

        Args:
            time_window_hours: Time window for statistics

        Returns:
            Dictionary mapping tier number to statistics:
            {
                1: {"name": "Local", "total": 10, "successes": 8, "success_rate": 0.8, ...},
                2: {"name": "Claude Code", ...},
                ...
            }
        """
        conn = await self._get_connection()
        cutoff = time.time() - (time_window_hours * 3600)

        cursor = await conn.execute(
            """
            SELECT
                executor_tier,
                COUNT(*) as total,
                SUM(CASE WHEN result_type IN ('success', 'partial') THEN 1 ELSE 0 END) as successes,
                AVG(execution_time) as avg_execution_time,
                AVG(confidence_used) as avg_confidence,
                SUM(CASE WHEN outcome_match = 1 THEN 1 ELSE 0 END) as matches,
                COUNT(CASE WHEN expected_outcome != '' THEN 1 END) as with_expectations
            FROM outcomes
            WHERE timestamp >= ?
            GROUP BY executor_tier
            ORDER BY executor_tier
            """,
            (cutoff,),
        )

        tier_names = {
            ExecutorTier.LOCAL: "Local",
            ExecutorTier.CLAUDE_CODE: "Claude Code",
            ExecutorTier.CLAUDE_FLOW: "Claude Flow",
            ExecutorTier.GEMINI: "Gemini",
        }

        rows = await cursor.fetchall()
        result = {}

        for row in rows:
            tier = row["executor_tier"] or ExecutorTier.CLAUDE_CODE
            total = row["total"]
            successes = row["successes"] or 0
            matches = row["matches"] or 0
            with_expectations = row["with_expectations"] or 0

            result[tier] = {
                "name": tier_names.get(tier, f"Tier {tier}"),
                "total": total,
                "successes": successes,
                "success_rate": successes / total if total > 0 else 0,
                "avg_execution_time": row["avg_execution_time"] or 0,
                "avg_confidence": row["avg_confidence"] or 0,
                "prediction_accuracy": matches / with_expectations if with_expectations > 0 else None,
                "outcomes_with_expectations": with_expectations,
            }

        return result

    async def get_outcome_accuracy(
        self,
        time_window_hours: Optional[float] = None,
    ) -> float:
        """
        Calculate how often expected outcome matches actual.

        Only considers outcomes where an expected_outcome was provided.

        Args:
            time_window_hours: Optional time window to limit analysis

        Returns:
            Accuracy as a float between 0 and 1, or 0.0 if no data
        """
        conn = await self._get_connection()

        if time_window_hours:
            cutoff = time.time() - (time_window_hours * 3600)
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome_match = 1 THEN 1 ELSE 0 END) as matches
                FROM outcomes
                WHERE expected_outcome != '' AND timestamp >= ?
                """,
                (cutoff,),
            )
        else:
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome_match = 1 THEN 1 ELSE 0 END) as matches
                FROM outcomes
                WHERE expected_outcome != ''
                """
            )

        row = await cursor.fetchone()
        if not row or row["total"] == 0:
            return 0.0

        return (row["matches"] or 0) / row["total"]

    async def get_tier_recommendation(
        self,
        action_type: str,
        observation: str,
    ) -> tuple[int, str]:
        """
        Recommend which tier should handle a given action type.

        Based on historical success rates and execution times per tier.

        Args:
            action_type: Type of action to be performed
            observation: The observation triggering the action

        Returns:
            Tuple of (recommended_tier, reasoning)
        """
        tier_stats = await self.get_tier_statistics(time_window_hours=168)

        # Get action-specific stats per tier
        conn = await self._get_connection()
        cutoff = time.time() - (168 * 3600)  # 1 week

        cursor = await conn.execute(
            """
            SELECT
                executor_tier,
                COUNT(*) as total,
                SUM(CASE WHEN result_type IN ('success', 'partial') THEN 1 ELSE 0 END) as successes
            FROM outcomes
            WHERE action_type = ? AND timestamp >= ?
            GROUP BY executor_tier
            """,
            (action_type, cutoff),
        )

        action_tier_stats = {row["executor_tier"]: row for row in await cursor.fetchall()}

        # Default to Claude Code (tier 2)
        recommended = ExecutorTier.CLAUDE_CODE
        reasoning_parts = []

        # Check if Local (tier 1) has good success rate for this action type
        if ExecutorTier.LOCAL in action_tier_stats:
            local_stats = action_tier_stats[ExecutorTier.LOCAL]
            if local_stats["total"] >= 5:
                success_rate = (local_stats["successes"] or 0) / local_stats["total"]
                if success_rate >= 0.9:
                    recommended = ExecutorTier.LOCAL
                    reasoning_parts.append(
                        f"Local tier has {success_rate:.0%} success rate for {action_type}"
                    )

        # Check if Claude Flow is needed for complex operations
        if ExecutorTier.CLAUDE_FLOW in action_tier_stats:
            flow_stats = action_tier_stats[ExecutorTier.CLAUDE_FLOW]
            claude_code_stats = action_tier_stats.get(ExecutorTier.CLAUDE_CODE, {})

            if flow_stats.get("total", 0) >= 3 and claude_code_stats.get("total", 0) >= 3:
                flow_success = (flow_stats.get("successes", 0) or 0) / flow_stats["total"]
                cc_success = (claude_code_stats.get("successes", 0) or 0) / claude_code_stats["total"]

                if flow_success > cc_success + 0.2:  # Flow significantly better
                    recommended = ExecutorTier.CLAUDE_FLOW
                    reasoning_parts.append(
                        f"Claude Flow outperforms Claude Code ({flow_success:.0%} vs {cc_success:.0%})"
                    )

        if not reasoning_parts:
            reasoning_parts.append("Using default tier based on action complexity")

        tier_names = {
            ExecutorTier.LOCAL: "Local",
            ExecutorTier.CLAUDE_CODE: "Claude Code",
            ExecutorTier.CLAUDE_FLOW: "Claude Flow",
            ExecutorTier.GEMINI: "Gemini",
        }

        return recommended, f"Recommended: {tier_names[recommended]}. {' '.join(reasoning_parts)}"
