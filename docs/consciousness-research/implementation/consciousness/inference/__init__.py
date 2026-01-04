"""
Consciousness Inference - LLM-based Reasoning

This module provides the connection to LM Studio for continuous thinking.
Uses the OpenAI-compatible API for inference.
"""

from .lm_studio import LMStudioReasoner, Decision, SelfAssessment

__all__ = [
    "LMStudioReasoner",
    "Decision",
    "SelfAssessment",
]
