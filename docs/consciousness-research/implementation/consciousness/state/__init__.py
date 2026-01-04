"""
Consciousness State - Persistence Layer

Manages:
- Session state (ephemeral, current run only)
- Persistent state (survives restarts)
- Decision history for learning
- Goal persistence
"""

from .database import StateDatabase

__all__ = [
    "StateDatabase",
]
