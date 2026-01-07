"""Configuration management for the Consciousness daemon."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LMStudioConfig(BaseModel):
    """LM Studio API configuration."""

    base_url: str = "http://localhost:1234/v1"
    model: str = "qwen2.5-14b-instruct"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_seconds: int = 60


class WatcherConfig(BaseModel):
    """File system watcher configuration."""

    root_path: str = "."
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            ".git",
            "__pycache__",
            ".venv",
            "*.pyc",
            ".DS_Store",
            "logs/",
            "*.db",
            "node_modules",
            ".claude-flow",
            ".hive-mind",
            ".swarm",
        ]
    )
    debounce_ms: int = 500
    max_file_size_kb: int = 1024


class ExecutorConfig(BaseModel):
    """Command executor configuration."""

    timeout_seconds: int = 300
    working_dir: str = "."
    allowed_commands: list[str] = Field(
        default_factory=lambda: [
            "git",
            "python",
            "pip",
            "uv",
            "npm",
            "node",
            "cat",
            "ls",
            "find",
            "grep",
        ]
    )
    blocked_patterns: list[str] = Field(
        default_factory=lambda: ["rm -rf /", "sudo", "> /dev"]
    )


class DecisionConfig(BaseModel):
    """Decision-making configuration."""

    min_confidence: float = 0.7
    thinking_interval_seconds: int = 5
    max_actions_per_cycle: int = 3
    require_confirmation_above: float = 0.9


class StateConfig(BaseModel):
    """State persistence configuration."""

    database_path: str = "./consciousness.db"
    max_history_entries: int = 10000
    checkpoint_interval_seconds: int = 300


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: str = "./logs/consciousness.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    format: str = "json"


class DisplayConfig(BaseModel):
    """CLI display configuration for consciousness output."""

    show_thinking: bool = True  # Show the LLM's reasoning/thinking process
    show_observations: bool = True  # Show file change observations
    show_decisions: bool = True  # Show decision summaries
    show_actions: bool = True  # Show action execution details
    thinking_style: str = "full"  # "full", "summary", "minimal"
    use_colors: bool = True  # Use Rich console colors
    panel_width: int = 100  # Width of display panels


class LoopConfig(BaseModel):
    """Main loop configuration."""

    tick_interval_seconds: float = 1.0
    idle_threshold_seconds: int = 30
    max_consecutive_errors: int = 5


class FallbackConfig(BaseModel):
    """Configuration for the fallback system.

    The fallback system provides graceful degradation when the primary
    LM Studio backend is unavailable, switching to Gemini consciousness
    mode or Claude Code integration.
    """

    # Mode settings
    enabled: bool = True  # Whether fallback system is active
    prefer_lm_studio: bool = True  # Prefer LM Studio when available
    check_interval_seconds: float = 30.0  # How often to check primary availability

    # LM Studio settings (overrides for fallback context)
    lm_studio_url: str = "http://localhost:1234/v1"
    lm_studio_timeout: float = 5.0  # Quick timeout for availability checks
    lm_studio_retry_count: int = 2  # Retries before switching to fallback

    # Gemini consciousness settings
    gemini_model: str = "gemini-1.5-flash"  # Model for consciousness mode
    gemini_timeout: float = 30.0  # Timeout for Gemini API calls
    gemini_enabled: bool = True  # Whether Gemini fallback is available

    # Claude Code settings
    claude_timeout: float = 120.0  # Timeout for Claude Code operations
    auto_execute_threshold: float = 0.8  # Confidence threshold for auto-execution

    # Behavior settings
    show_mode_changes: bool = True  # Display notifications when mode changes
    log_consciousness_thoughts: bool = False  # Log internal reasoning
    sign_off: str = "- Stoffy"  # Signature for consciousness-mode responses


class ConsciousnessConfig(BaseSettings):
    """Root configuration for the Consciousness daemon."""

    model_config = SettingsConfigDict(
        env_prefix="CONSCIOUSNESS_",
        env_nested_delimiter="__",
    )

    lm_studio: LMStudioConfig = Field(default_factory=LMStudioConfig)
    watcher: WatcherConfig = Field(default_factory=WatcherConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    decision: DecisionConfig = Field(default_factory=DecisionConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ConsciousnessConfig":
        """Load configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            return cls()

        with path.open() as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to a YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump()
        with path.open("w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_config(config_path: str | Path | None = None) -> ConsciousnessConfig:
    """Load configuration from file or defaults.

    Args:
        config_path: Path to YAML config file. If None, searches for
                     consciousness.yaml in current directory.

    Returns:
        Loaded configuration object.
    """
    if config_path is None:
        default_paths = [
            Path("consciousness.yaml"),
            Path("config/consciousness.yaml"),
            Path.home() / ".config" / "consciousness" / "config.yaml",
        ]
        for path in default_paths:
            if path.exists():
                config_path = path
                break

    if config_path is not None:
        return ConsciousnessConfig.from_yaml(config_path)

    return ConsciousnessConfig()


def load_fallback_config(config_path: str | Path | None = None) -> FallbackConfig:
    """Load fallback configuration from file or defaults.

    This is a convenience function that loads just the fallback portion
    of the configuration, useful for components that only need fallback
    settings without the full consciousness config.

    Args:
        config_path: Path to YAML config file. If None, searches for
                     consciousness.yaml in standard locations.

    Returns:
        Loaded fallback configuration object.
    """
    full_config = load_config(config_path)
    return full_config.fallback
