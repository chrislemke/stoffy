"""
Consciousness Orchestrator - Autonomous OIDA Loop Implementation

This package implements a consciousness system based on:
- Free Energy Principle (FEP) for active inference
- Global Workspace Theory (GWT) for information broadcast
- Transparent Self-Loop Architecture for self-awareness
- Strange Loop dynamics for genuine metacognition

Architecture Decisions (from Hive Mind consensus):
- ARCH-001: Transparent Self-Loop Architecture
- ARCH-002: Four-level self-model hierarchy (Computational→Relational→Introspective→Narrative)
- ARCH-003: Expected Free Energy minimization for decisions
- ARCH-004: Global Workspace with capacity 7 (Miller's number)
- ARCH-005: Implicit confidence over explicit (logit-based)
- ARCH-006: Metacognitive gate with 0.7 confidence threshold
"""

__version__ = "0.1.0"
__author__ = "Consciousness Hive Mind"

from .config import ConsciousnessConfig
from .orchestrator import ConsciousnessOrchestrator

__all__ = [
    "ConsciousnessConfig",
    "ConsciousnessOrchestrator",
    "__version__",
]
