"""
LM Studio Detector - Monitors LM Studio availability.

Provides continuous health checking and connectivity detection for the
local LM Studio instance. When LM Studio becomes unavailable, the
fallback system can route to alternative backends.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Any

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)


class LMStudioStatus(Enum):
    """Status of the LM Studio connection."""
    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"  # Connected but slow/unreliable


@dataclass
class LMStudioHealth:
    """Health information for LM Studio."""
    status: LMStudioStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    model_loaded: Optional[str] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    def is_available(self) -> bool:
        """Check if LM Studio is available for use."""
        return self.status in (LMStudioStatus.CONNECTED, LMStudioStatus.DEGRADED)


@dataclass
class DetectorConfig:
    """Configuration for the LM Studio detector."""
    base_url: str = "http://localhost:1234/v1"
    check_interval_seconds: float = 30.0
    timeout_seconds: float = 5.0
    failure_threshold: int = 3  # Failures before marking disconnected
    recovery_threshold: int = 2  # Successes before marking connected
    degraded_response_ms: float = 2000.0  # Response time threshold for degraded


class LMStudioDetector:
    """
    Monitors LM Studio availability and health.

    Provides:
    - Periodic health checks
    - Status change callbacks
    - Health history tracking
    - Graceful degradation detection
    """

    def __init__(
        self,
        config: Optional[DetectorConfig] = None,
        on_status_change: Optional[Callable[[LMStudioStatus, LMStudioStatus], Any]] = None,
    ):
        """
        Initialize the detector.

        Args:
            config: Detector configuration
            on_status_change: Callback when status changes (old_status, new_status)
        """
        self.config = config or DetectorConfig()
        self.on_status_change = on_status_change

        self._client = AsyncOpenAI(
            base_url=self.config.base_url,
            api_key="not-needed",
            timeout=self.config.timeout_seconds,
        )

        self._health = LMStudioHealth(
            status=LMStudioStatus.UNKNOWN,
            last_check=datetime.now(timezone.utc),
        )

        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._check_lock = asyncio.Lock()

    @property
    def health(self) -> LMStudioHealth:
        """Get current health status."""
        return self._health

    @property
    def is_available(self) -> bool:
        """Check if LM Studio is currently available."""
        return self._health.is_available()

    @property
    def status(self) -> LMStudioStatus:
        """Get current status."""
        return self._health.status

    async def check_health(self) -> LMStudioHealth:
        """
        Perform a health check on LM Studio.

        Returns:
            Updated health information
        """
        async with self._check_lock:
            start_time = time.time()
            old_status = self._health.status

            try:
                # Try to list models - lightweight health check
                models = await asyncio.wait_for(
                    self._client.models.list(),
                    timeout=self.config.timeout_seconds,
                )

                response_time_ms = (time.time() - start_time) * 1000

                # Determine new status
                if response_time_ms > self.config.degraded_response_ms:
                    new_status = LMStudioStatus.DEGRADED
                else:
                    new_status = LMStudioStatus.CONNECTED

                # Extract model info
                model_loaded = None
                if models.data:
                    model_loaded = models.data[0].id

                # Update health
                self._health = LMStudioHealth(
                    status=new_status,
                    last_check=datetime.now(timezone.utc),
                    response_time_ms=response_time_ms,
                    model_loaded=model_loaded,
                    error_message=None,
                    consecutive_failures=0,
                    consecutive_successes=self._health.consecutive_successes + 1,
                )

                logger.debug(
                    "lm_studio.health_check.success",
                    response_time_ms=response_time_ms,
                    model=model_loaded,
                    status=new_status.value,
                )

            except asyncio.TimeoutError:
                self._update_failure("Connection timed out")

            except Exception as e:
                self._update_failure(str(e))

            # Notify on status change
            if old_status != self._health.status and self.on_status_change:
                try:
                    result = self.on_status_change(old_status, self._health.status)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.warning(f"lm_studio.status_callback_error: {e}")

            return self._health

    def _update_failure(self, error_message: str) -> None:
        """Update health after a failure."""
        consecutive_failures = self._health.consecutive_failures + 1

        # Determine status based on failure count
        if consecutive_failures >= self.config.failure_threshold:
            new_status = LMStudioStatus.DISCONNECTED
        elif self._health.status == LMStudioStatus.CONNECTED:
            new_status = LMStudioStatus.DEGRADED
        else:
            new_status = self._health.status

        self._health = LMStudioHealth(
            status=new_status,
            last_check=datetime.now(timezone.utc),
            response_time_ms=None,
            model_loaded=None,
            error_message=error_message,
            consecutive_failures=consecutive_failures,
            consecutive_successes=0,
        )

        logger.debug(
            "lm_studio.health_check.failure",
            error=error_message,
            consecutive_failures=consecutive_failures,
            status=new_status.value,
        )

    async def start_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("lm_studio.monitoring.started")

    async def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("lm_studio.monitoring.stopped")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                await self.check_health()
                await asyncio.sleep(self.config.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"lm_studio.monitor_error: {e}")
                await asyncio.sleep(self.config.check_interval_seconds)

    async def wait_for_connection(
        self,
        timeout: Optional[float] = None,
        check_interval: float = 2.0,
    ) -> bool:
        """
        Wait for LM Studio to become available.

        Args:
            timeout: Maximum time to wait (None = indefinite)
            check_interval: Time between checks

        Returns:
            True if connected, False if timed out
        """
        start_time = time.time()

        while True:
            health = await self.check_health()
            if health.is_available():
                return True

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            await asyncio.sleep(check_interval)

    def get_status_summary(self) -> dict:
        """Get a summary of current status."""
        return {
            "status": self._health.status.value,
            "available": self._health.is_available(),
            "last_check": self._health.last_check.isoformat(),
            "response_time_ms": self._health.response_time_ms,
            "model_loaded": self._health.model_loaded,
            "error": self._health.error_message,
            "consecutive_failures": self._health.consecutive_failures,
            "consecutive_successes": self._health.consecutive_successes,
        }


async def check_lm_studio_available(
    base_url: str = "http://localhost:1234/v1",
    timeout: float = 5.0,
) -> bool:
    """
    Quick check if LM Studio is available.

    Args:
        base_url: LM Studio API URL
        timeout: Connection timeout

    Returns:
        True if available
    """
    detector = LMStudioDetector(DetectorConfig(
        base_url=base_url,
        timeout_seconds=timeout,
    ))
    health = await detector.check_health()
    return health.is_available()


if __name__ == "__main__":
    async def test():
        print("Testing LM Studio Detector...")

        def on_status_change(old: LMStudioStatus, new: LMStudioStatus):
            print(f"Status changed: {old.value} -> {new.value}")

        detector = LMStudioDetector(
            config=DetectorConfig(check_interval_seconds=5.0),
            on_status_change=on_status_change,
        )

        # Single check
        health = await detector.check_health()
        print(f"Health: {detector.get_status_summary()}")

        # Start monitoring for a bit
        print("\nStarting monitoring for 15 seconds...")
        await detector.start_monitoring()
        await asyncio.sleep(15)
        await detector.stop_monitoring()

        print(f"\nFinal status: {detector.get_status_summary()}")

    asyncio.run(test())
