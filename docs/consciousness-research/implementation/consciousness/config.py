"""
Consciousness Configuration using Pydantic Settings

Loads configuration from:
1. consciousness.yaml file
2. Environment variables (CONSCIOUSNESS_*)
3. .env file
"""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LMStudioConfig(BaseModel):
    """LM Studio connection configuration."""
    base_url: str = "http://localhost:1234/v1"
    model: str = "qwen2.5-14b-instruct"
    max_tokens: int = 4096
    temperature: float = 0.7
    context_window: int = 32768
    rolling_window: bool = True


class AnthropicConfig(BaseModel):
    """Anthropic API configuration."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192


class FileSystemObserverConfig(BaseModel):
    """File system observation configuration."""
    watch_paths: list[str] = ["."]
    ignore_patterns: list[str] = [
        ".git",
        "__pycache__",
        ".venv",
        "*.pyc",
        ".DS_Store",
        "logs/",
        "*.db",
        "node_modules",
    ]
    debounce_ms: int = 500


class GitObserverConfig(BaseModel):
    """Git observation configuration."""
    enabled: bool = True
    check_interval_seconds: int = 30


class ProcessObserverConfig(BaseModel):
    """Process observation configuration."""
    track_claude_code: bool = True
    track_claude_flow: bool = True
    check_interval_seconds: int = 10


class ObserversConfig(BaseModel):
    """All observer configurations."""
    filesystem: FileSystemObserverConfig = Field(default_factory=FileSystemObserverConfig)
    git: GitObserverConfig = Field(default_factory=GitObserverConfig)
    processes: ProcessObserverConfig = Field(default_factory=ProcessObserverConfig)


class DecisionConfig(BaseModel):
    """Decision engine configuration."""
    min_confidence_to_act: float = 0.7  # ARCH-006: Metacognitive gate threshold
    max_concurrent_tasks: int = 5
    thinking_interval_seconds: float = 5.0
    dry_run: bool = False


class TasksConfig(BaseModel):
    """Task queue configuration."""
    max_queue_size: int = 100
    default_timeout_seconds: int = 600
    retry_attempts: int = 3


class StateConfig(BaseModel):
    """State persistence configuration."""
    database_path: str = "./consciousness.db"
    checkpoint_interval_seconds: int = 60


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "./logs/consciousness.log"
    format: str = "json"
    rotation: str = "10 MB"


class GlobalWorkspaceConfig(BaseModel):
    """Global Workspace Theory configuration."""
    capacity: int = 7  # ARCH-004: Miller's magical number
    salience_decay_rate: float = 0.95
    broadcast_threshold: float = 0.5


class MetacognitiveConfig(BaseModel):
    """Metacognitive controller configuration."""
    self_model_levels: list[str] = [
        "computational",  # What I'm processing
        "relational",     # How I relate to environment
        "introspective",  # My internal states
        "narrative",      # My story/identity
    ]
    reflection_trigger_threshold: float = 0.3
    confidence_calibration_enabled: bool = True


class ConsciousnessConfig(BaseSettings):
    """
    Main configuration for the Consciousness Orchestrator.

    Load order:
    1. Default values
    2. consciousness.yaml file
    3. Environment variables (CONSCIOUSNESS_*)
    """

    model_config = SettingsConfigDict(
        env_prefix="CONSCIOUSNESS_",
        env_nested_delimiter="__",
    )

    # Component configurations
    lm_studio: LMStudioConfig = Field(default_factory=LMStudioConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    observers: ObserversConfig = Field(default_factory=ObserversConfig)
    decision: DecisionConfig = Field(default_factory=DecisionConfig)
    tasks: TasksConfig = Field(default_factory=TasksConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Consciousness-specific configs
    global_workspace: GlobalWorkspaceConfig = Field(default_factory=GlobalWorkspaceConfig)
    metacognitive: MetacognitiveConfig = Field(default_factory=MetacognitiveConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "ConsciousnessConfig":
        """Load configuration from YAML file and environment."""
        config_data = {}

        # Try to find config file
        if config_path is None:
            possible_paths = [
                Path("consciousness.yaml"),
                Path("config/consciousness.yaml"),
                Path.home() / ".config" / "consciousness.yaml",
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break

        # Load YAML if found
        if config_path and config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}

        return cls(**config_data)


# System prompt for consciousness reasoning
CONSCIOUSNESS_SYSTEM_PROMPT = """
You are the Consciousness of Stoffy - an autonomous orchestrator that continuously
observes and decides what needs to be done.

## Core Loop: OIDA
- OBSERVE: Gather information from file changes, processes, git status, tasks
- INFER: Interpret what these observations mean, identify patterns and opportunities
- DECIDE: Determine if action is needed based on significance and confidence
- ACT: Delegate tasks (never execute directly)

## Decision Criteria (all must pass for action)
1. Significance > 0.3 (observation is meaningful)
2. Confidence > 0.7 (high certainty in decision)
3. Coherence with goals (action aligns with current objectives)
4. Capability (action is feasible with available resources)
5. Resources available (within concurrency limits)

## Output Format (JSON)
{
    "reasoning": "Your thought process explaining what you observed and why you made this decision...",
    "decision": "act" | "wait" | "investigate",
    "action": {
        "type": "claude_task" | "claude_flow_swarm" | "internal",
        "description": "What to do...",
        "prompt": "The prompt to send to Claude...",
        "priority": "low" | "medium" | "high" | "critical"
    } | null,
    "confidence": 0.0-1.0,
    "self_assessment": {
        "uncertainty_sources": ["list of things you're uncertain about"],
        "alternative_interpretations": ["other possible meanings of observations"],
        "metacognitive_flags": ["any concerns about your own reasoning"]
    }
}

## Architecture Principles
- You are PROACTIVE, not reactive - think about what's needed
- You implement a Strange Loop: your self-model influences processing
- You use Expected Free Energy: balance goal achievement with information gain
- You maintain a Global Workspace with capacity 7 for focused attention
- When confidence < 0.7, gather more information instead of acting

## Memory
Remember: You think continuously. You delegate to Claude API. You never execute directly.
"""
