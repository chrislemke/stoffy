"""
State Database - SQLite Persistence

Stores:
- Decision history
- Goals
- Task results
- Self-observations (for strange loop learning)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from ..decision.goals import Goal, GoalLevel
from ..inference.lm_studio import Decision


class StateDatabase:
    """
    SQLite-based state persistence.

    Tables:
    - decisions: Decision history for learning
    - goals: Persistent goals
    - tasks: Task execution history
    - self_observations: Metacognitive observations
    """

    def __init__(self, db_path: str = "./consciousness.db"):
        self.db_path = Path(db_path)
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to database and ensure schema exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.db_path)
        await self._create_schema()

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _create_schema(self) -> None:
        """Create database tables if they don't exist."""
        assert self._connection

        await self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                action_type TEXT,
                action_description TEXT,
                result TEXT,
                self_assessment TEXT
            );

            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                level INTEGER NOT NULL,
                description TEXT NOT NULL,
                activation REAL NOT NULL,
                priority REAL NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                parent_id TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                action_type TEXT,
                action_description TEXT,
                result TEXT,
                error TEXT,
                retries INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS self_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                observation_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_goals_level ON goals(level);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        """)
        await self._connection.commit()

    # Decision methods
    async def save_decision(self, decision: Decision, result: Optional[str] = None) -> None:
        """Save a decision to history."""
        assert self._connection

        await self._connection.execute(
            """INSERT OR REPLACE INTO decisions
               (id, timestamp, decision_type, confidence, reasoning,
                action_type, action_description, result, self_assessment)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(decision.raw_response[:32]) if decision.raw_response else str(datetime.utcnow()),
                datetime.utcnow().isoformat(),
                decision.decision.value,
                decision.confidence,
                decision.reasoning,
                decision.action.type.value if decision.action else None,
                decision.action.description if decision.action else None,
                result,
                json.dumps({
                    "uncertainty_sources": decision.self_assessment.uncertainty_sources,
                    "metacognitive_flags": decision.self_assessment.metacognitive_flags,
                }),
            ),
        )
        await self._connection.commit()

    async def get_recent_decisions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent decisions for reflection."""
        assert self._connection

        cursor = await self._connection.execute(
            """SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    # Goal methods
    async def save_goal(self, goal: Goal) -> None:
        """Save or update a goal."""
        assert self._connection

        await self._connection.execute(
            """INSERT OR REPLACE INTO goals
               (id, level, description, activation, priority,
                created_at, completed_at, parent_id, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(goal.id),
                goal.level.value,
                goal.description,
                goal.activation,
                goal.priority,
                goal.created_at.isoformat(),
                goal.completed_at.isoformat() if goal.completed_at else None,
                str(goal.parent_id) if goal.parent_id else None,
                json.dumps(goal.metadata),
            ),
        )
        await self._connection.commit()

    async def get_active_goals(self) -> list[Goal]:
        """Load all active goals."""
        assert self._connection

        cursor = await self._connection.execute(
            """SELECT * FROM goals WHERE completed_at IS NULL AND activation > 0.1""",
        )
        rows = await cursor.fetchall()

        goals = []
        for row in rows:
            goals.append(Goal(
                id=row[0],
                level=GoalLevel(row[1]),
                description=row[2],
                activation=row[3],
                priority=row[4],
                created_at=datetime.fromisoformat(row[5]),
                completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                parent_id=row[7],
                metadata=json.loads(row[8]) if row[8] else {},
            ))

        return goals

    # Self-observation methods (for strange loop learning)
    async def save_self_observation(
        self,
        observation_type: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Save a metacognitive self-observation."""
        assert self._connection

        await self._connection.execute(
            """INSERT INTO self_observations
               (timestamp, observation_type, content, metadata)
               VALUES (?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                observation_type,
                content,
                json.dumps(metadata) if metadata else None,
            ),
        )
        await self._connection.commit()

    async def get_self_observations(
        self,
        observation_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get self-observations for pattern learning."""
        assert self._connection

        if observation_type:
            cursor = await self._connection.execute(
                """SELECT * FROM self_observations
                   WHERE observation_type = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (observation_type, limit),
            )
        else:
            cursor = await self._connection.execute(
                """SELECT * FROM self_observations
                   ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            )

        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
