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


class LoopConfig(BaseModel):
    """Main loop configuration."""

    tick_interval_seconds: float = 1.0
    idle_threshold_seconds: int = 30
    max_consecutive_errors: int = 5


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
