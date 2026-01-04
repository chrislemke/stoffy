"""State persistence for the Consciousness daemon using SQLite."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events tracked by the daemon."""

    FILE_CHANGE = "file_change"
    PROCESS_EVENT = "process_event"
    THOUGHT = "thought"
    DECISION = "decision"
    ACTION = "action"
    ERROR = "error"
    OBSERVATION = "observation"


class Event(BaseModel):
    """An event in the consciousness stream."""

    id: int | None = None
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class ThoughtRecord(BaseModel):
    """A recorded thought from the LLM."""

    id: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prompt: str
    response: str
    confidence: float = 0.0
    tokens_used: int = 0
    latency_ms: float = 0.0


class ActionRecord(BaseModel):
    """A recorded action taken by the daemon."""

    id: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action_type: str
    command: str
    result: str = ""
    success: bool = False
    thought_id: int | None = None


class StateManager:
    """Manages persistent state using SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get a database connection."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        yield self._connection

    async def initialize(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with self.connection() as conn:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL,
                    context TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS thoughts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    tokens_used INTEGER DEFAULT 0,
                    latency_ms REAL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    command TEXT NOT NULL,
                    result TEXT DEFAULT '',
                    success INTEGER DEFAULT 0,
                    thought_id INTEGER,
                    FOREIGN KEY (thought_id) REFERENCES thoughts(id)
                );

                CREATE TABLE IF NOT EXISTS state_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    snapshot TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_thoughts_timestamp ON thoughts(timestamp);
                CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp);
                """
            )
            await conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def record_event(self, event: Event) -> int:
        """Record an event to the database."""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO events (event_type, timestamp, data, context)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    json.dumps(event.data),
                    json.dumps(event.context),
                ),
            )
            await conn.commit()
            return cursor.lastrowid or 0

    async def record_thought(self, thought: ThoughtRecord) -> int:
        """Record a thought to the database."""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO thoughts (timestamp, prompt, response, confidence, tokens_used, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    thought.timestamp.isoformat(),
                    thought.prompt,
                    thought.response,
                    thought.confidence,
                    thought.tokens_used,
                    thought.latency_ms,
                ),
            )
            await conn.commit()
            return cursor.lastrowid or 0

    async def record_action(self, action: ActionRecord) -> int:
        """Record an action to the database."""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO actions (timestamp, action_type, command, result, success, thought_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    action.timestamp.isoformat(),
                    action.action_type,
                    action.command,
                    action.result,
                    1 if action.success else 0,
                    action.thought_id,
                ),
            )
            await conn.commit()
            return cursor.lastrowid or 0

    async def get_recent_events(
        self, limit: int = 100, event_type: EventType | None = None
    ) -> list[Event]:
        """Get recent events from the database."""
        async with self.connection() as conn:
            if event_type:
                cursor = await conn.execute(
                    """
                    SELECT * FROM events
                    WHERE event_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (event_type.value, limit),
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT * FROM events
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

            rows = await cursor.fetchall()
            return [
                Event(
                    id=row["id"],
                    event_type=EventType(row["event_type"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    data=json.loads(row["data"]),
                    context=json.loads(row["context"]),
                )
                for row in rows
            ]

    async def get_recent_thoughts(self, limit: int = 50) -> list[ThoughtRecord]:
        """Get recent thoughts from the database."""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM thoughts
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                ThoughtRecord(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    prompt=row["prompt"],
                    response=row["response"],
                    confidence=row["confidence"],
                    tokens_used=row["tokens_used"],
                    latency_ms=row["latency_ms"],
                )
                for row in rows
            ]

    async def get_recent_actions(self, limit: int = 50) -> list[ActionRecord]:
        """Get recent actions from the database."""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM actions
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                ActionRecord(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    action_type=row["action_type"],
                    command=row["command"],
                    result=row["result"],
                    success=bool(row["success"]),
                    thought_id=row["thought_id"],
                )
                for row in rows
            ]

    async def save_snapshot(self, snapshot: dict[str, Any]) -> int:
        """Save a state snapshot."""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO state_snapshots (timestamp, snapshot)
                VALUES (?, ?)
                """,
                (datetime.now(timezone.utc).isoformat(), json.dumps(snapshot)),
            )
            await conn.commit()
            return cursor.lastrowid or 0

    async def get_latest_snapshot(self) -> dict[str, Any] | None:
        """Get the most recent state snapshot."""
        async with self.connection() as conn:
            cursor = await conn.execute(
                """
                SELECT snapshot FROM state_snapshots
                ORDER BY timestamp DESC
                LIMIT 1
                """
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row["snapshot"])
            return None

    async def get_statistics(self) -> dict[str, Any]:
        """Get database statistics."""
        async with self.connection() as conn:
            stats: dict[str, Any] = {}

            cursor = await conn.execute("SELECT COUNT(*) FROM events")
            row = await cursor.fetchone()
            stats["total_events"] = row[0] if row else 0

            cursor = await conn.execute("SELECT COUNT(*) FROM thoughts")
            row = await cursor.fetchone()
            stats["total_thoughts"] = row[0] if row else 0

            cursor = await conn.execute("SELECT COUNT(*) FROM actions")
            row = await cursor.fetchone()
            stats["total_actions"] = row[0] if row else 0

            cursor = await conn.execute(
                "SELECT COUNT(*) FROM actions WHERE success = 1"
            )
            row = await cursor.fetchone()
            stats["successful_actions"] = row[0] if row else 0

            cursor = await conn.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM events
                GROUP BY event_type
                """
            )
            rows = await cursor.fetchall()
            stats["events_by_type"] = {row["event_type"]: row["count"] for row in rows}

            return stats

    async def cleanup_old_entries(self, max_entries: int = 10000) -> int:
        """Remove old entries exceeding the maximum."""
        deleted = 0
        async with self.connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM events")
            row = await cursor.fetchone()
            count = row[0] if row else 0

            if count > max_entries:
                to_delete = count - max_entries
                await conn.execute(
                    """
                    DELETE FROM events
                    WHERE id IN (
                        SELECT id FROM events
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                    """,
                    (to_delete,),
                )
                deleted = to_delete
                await conn.commit()

        return deleted
