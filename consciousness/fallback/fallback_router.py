"""
Fallback Router - Routes requests to appropriate backends.

When the primary LM Studio backend is unavailable, this router
directs requests to fallback backends (Gemini, Claude Code)
based on task type and configuration.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Callable, Any

import structlog

from .lm_studio_detector import LMStudioDetector, LMStudioStatus, DetectorConfig

logger = structlog.get_logger(__name__)


class FallbackMode(Enum):
    """Current operating mode of the fallback system."""
    PRIMARY = "primary"  # Using LM Studio (normal mode)
    FALLBACK_GEMINI = "fallback_gemini"  # Using Gemini for consciousness
    FALLBACK_CLAUDE = "fallback_claude"  # Using Claude Code for tasks
    HYBRID = "hybrid"  # Using both fallbacks as appropriate
    DEGRADED = "degraded"  # Limited functionality


class BackendType(Enum):
    """Available backend types."""
    LM_STUDIO = "lm_studio"
    GEMINI = "gemini"
    CLAUDE_CODE = "claude_code"
    CLAUDE_FLOW = "claude_flow"


@dataclass
class BackendStatus:
    """Status of a backend."""
    backend: BackendType
    available: bool
    last_check: datetime
    error: Optional[str] = None


@dataclass
class RouterConfig:
    """Configuration for the fallback router."""
    # Primary backend
    lm_studio_url: str = "http://localhost:1234/v1"
    prefer_lm_studio: bool = True

    # Fallback preferences
    fallback_order: List[BackendType] = field(default_factory=lambda: [
        BackendType.GEMINI,
        BackendType.CLAUDE_CODE,
    ])

    # Auto-switching
    auto_switch_to_fallback: bool = True
    auto_switch_back: bool = True
    check_interval_seconds: float = 30.0

    # Mode preferences
    consciousness_backend: BackendType = BackendType.GEMINI  # For thinking
    execution_backend: BackendType = BackendType.CLAUDE_CODE  # For actions


@dataclass
class RouteDecision:
    """Decision about which backend to use."""
    backend: BackendType
    mode: FallbackMode
    reason: str
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "backend": self.backend.value,
            "mode": self.mode.value,
            "reason": self.reason,
            "confidence": self.confidence,
        }


class FallbackRouter:
    """
    Routes requests to appropriate backends based on availability.

    Provides:
    - Automatic failover when LM Studio is down
    - Task-based routing (consciousness vs execution)
    - Status monitoring and reporting
    - Configurable fallback preferences
    """

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        detector: Optional[LMStudioDetector] = None,
        on_mode_change: Optional[Callable[[FallbackMode, FallbackMode], Any]] = None,
    ):
        """
        Initialize the router.

        Args:
            config: Router configuration
            detector: LM Studio detector (created if not provided)
            on_mode_change: Callback when mode changes (old_mode, new_mode)
        """
        self.config = config or RouterConfig()
        self.on_mode_change = on_mode_change

        # Initialize detector
        self._detector = detector or LMStudioDetector(
            config=DetectorConfig(
                base_url=self.config.lm_studio_url,
                check_interval_seconds=self.config.check_interval_seconds,
            ),
            on_status_change=self._on_lm_studio_status_change,
        )

        # Current mode
        self._mode = FallbackMode.PRIMARY
        self._mode_lock = asyncio.Lock()

        # Backend status tracking
        self._backend_status: dict[BackendType, BackendStatus] = {}

        # Statistics
        self._route_count = 0
        self._fallback_count = 0
        self._last_mode_change: Optional[datetime] = None

    @property
    def mode(self) -> FallbackMode:
        """Get current operating mode."""
        return self._mode

    @property
    def is_primary_mode(self) -> bool:
        """Check if using primary (LM Studio) mode."""
        return self._mode == FallbackMode.PRIMARY

    @property
    def is_fallback_mode(self) -> bool:
        """Check if using any fallback mode."""
        return self._mode in (
            FallbackMode.FALLBACK_GEMINI,
            FallbackMode.FALLBACK_CLAUDE,
            FallbackMode.HYBRID,
        )

    async def initialize(self) -> None:
        """Initialize the router and check backends."""
        # Check LM Studio
        await self._detector.check_health()

        # Determine initial mode
        if self._detector.is_available:
            await self._set_mode(FallbackMode.PRIMARY, "LM Studio available at startup")
        else:
            await self._set_mode(FallbackMode.HYBRID, "LM Studio unavailable at startup")

        # Start monitoring if auto-switch is enabled
        if self.config.auto_switch_to_fallback or self.config.auto_switch_back:
            await self._detector.start_monitoring()

    async def shutdown(self) -> None:
        """Shutdown the router and stop monitoring."""
        await self._detector.stop_monitoring()

    async def _set_mode(self, new_mode: FallbackMode, reason: str) -> None:
        """Set the current mode and notify listeners."""
        async with self._mode_lock:
            if new_mode == self._mode:
                return

            old_mode = self._mode
            self._mode = new_mode
            self._last_mode_change = datetime.now(timezone.utc)

            logger.info(
                "fallback_router.mode_changed",
                old_mode=old_mode.value,
                new_mode=new_mode.value,
                reason=reason,
            )

            if self.on_mode_change:
                try:
                    result = self.on_mode_change(old_mode, new_mode)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.warning(f"fallback_router.mode_callback_error: {e}")

    def _on_lm_studio_status_change(
        self,
        old_status: LMStudioStatus,
        new_status: LMStudioStatus,
    ) -> None:
        """Handle LM Studio status changes."""
        # Schedule async mode update
        asyncio.create_task(self._handle_status_change(old_status, new_status))

    async def _handle_status_change(
        self,
        old_status: LMStudioStatus,
        new_status: LMStudioStatus,
    ) -> None:
        """Handle status change asynchronously."""
        if new_status == LMStudioStatus.CONNECTED:
            if self.config.auto_switch_back and self.is_fallback_mode:
                await self._set_mode(
                    FallbackMode.PRIMARY,
                    "LM Studio reconnected",
                )

        elif new_status == LMStudioStatus.DISCONNECTED:
            if self.config.auto_switch_to_fallback and self.is_primary_mode:
                await self._set_mode(
                    FallbackMode.HYBRID,
                    "LM Studio disconnected",
                )

        elif new_status == LMStudioStatus.DEGRADED:
            # Stay in current mode but log the degradation
            logger.warning("fallback_router.lm_studio_degraded")

    def route_consciousness_request(self) -> RouteDecision:
        """
        Route a consciousness/thinking request.

        Used for: decision making, reasoning, observation analysis.

        Returns:
            RouteDecision indicating which backend to use
        """
        self._route_count += 1

        if self._mode == FallbackMode.PRIMARY:
            return RouteDecision(
                backend=BackendType.LM_STUDIO,
                mode=self._mode,
                reason="Primary mode - using local LM Studio",
            )

        # In fallback mode, use configured consciousness backend
        self._fallback_count += 1
        return RouteDecision(
            backend=self.config.consciousness_backend,
            mode=self._mode,
            reason=f"Fallback mode - using {self.config.consciousness_backend.value}",
        )

    def route_execution_request(self) -> RouteDecision:
        """
        Route an execution/action request.

        Used for: code execution, file operations, task completion.

        Returns:
            RouteDecision indicating which backend to use
        """
        self._route_count += 1

        # Execution always prefers Claude Code regardless of mode
        # (LM Studio can't execute code anyway)
        return RouteDecision(
            backend=self.config.execution_backend,
            mode=self._mode,
            reason=f"Execution request - using {self.config.execution_backend.value}",
        )

    def route_request(
        self,
        is_consciousness: bool = True,
        preferred_backend: Optional[BackendType] = None,
    ) -> RouteDecision:
        """
        Route a generic request.

        Args:
            is_consciousness: True for thinking, False for execution
            preferred_backend: Override backend if specified

        Returns:
            RouteDecision
        """
        if preferred_backend:
            return RouteDecision(
                backend=preferred_backend,
                mode=self._mode,
                reason=f"Preferred backend specified: {preferred_backend.value}",
            )

        if is_consciousness:
            return self.route_consciousness_request()
        else:
            return self.route_execution_request()

    async def force_fallback_mode(self, reason: str = "Manually triggered") -> None:
        """Force switch to fallback mode."""
        await self._set_mode(FallbackMode.HYBRID, reason)

    async def force_primary_mode(self, reason: str = "Manually triggered") -> None:
        """Force switch to primary mode (if LM Studio available)."""
        if self._detector.is_available:
            await self._set_mode(FallbackMode.PRIMARY, reason)
        else:
            logger.warning("fallback_router.cannot_switch_primary_unavailable")

    async def check_all_backends(self) -> dict[BackendType, BackendStatus]:
        """Check status of all backends."""
        # Check LM Studio
        lm_health = await self._detector.check_health()
        self._backend_status[BackendType.LM_STUDIO] = BackendStatus(
            backend=BackendType.LM_STUDIO,
            available=lm_health.is_available(),
            last_check=lm_health.last_check,
            error=lm_health.error_message,
        )

        # Gemini and Claude are assumed available (they have their own error handling)
        # In a production system, we'd check these too
        for backend in [BackendType.GEMINI, BackendType.CLAUDE_CODE]:
            if backend not in self._backend_status:
                self._backend_status[backend] = BackendStatus(
                    backend=backend,
                    available=True,  # Assume available
                    last_check=datetime.now(timezone.utc),
                )

        return self._backend_status

    def get_status(self) -> dict:
        """Get comprehensive router status."""
        return {
            "mode": self._mode.value,
            "is_primary": self.is_primary_mode,
            "is_fallback": self.is_fallback_mode,
            "lm_studio": self._detector.get_status_summary(),
            "backends": {
                b.value: {
                    "available": s.available,
                    "last_check": s.last_check.isoformat(),
                    "error": s.error,
                }
                for b, s in self._backend_status.items()
            },
            "statistics": {
                "route_count": self._route_count,
                "fallback_count": self._fallback_count,
                "last_mode_change": (
                    self._last_mode_change.isoformat()
                    if self._last_mode_change else None
                ),
            },
        }


if __name__ == "__main__":
    async def test():
        print("Testing Fallback Router...")

        def on_mode_change(old: FallbackMode, new: FallbackMode):
            print(f"Mode changed: {old.value} -> {new.value}")

        router = FallbackRouter(
            config=RouterConfig(check_interval_seconds=5.0),
            on_mode_change=on_mode_change,
        )

        await router.initialize()

        print(f"\nInitial status: {router.get_status()}")

        # Test routing
        consciousness_route = router.route_consciousness_request()
        print(f"\nConsciousness route: {consciousness_route.to_dict()}")

        execution_route = router.route_execution_request()
        print(f"Execution route: {execution_route.to_dict()}")

        await router.shutdown()

    asyncio.run(test())
