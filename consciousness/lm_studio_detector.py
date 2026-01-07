"""
LM Studio Availability Detector

Provides robust detection of LM Studio availability with:
- Smart caching to avoid hammering the server
- Exponential backoff retry logic
- Async-safe implementation
- Detailed status reporting

Usage:
    detector = LMStudioDetector()

    # Quick check (uses cache)
    if await detector.is_available():
        print("LM Studio is running")

    # Force fresh check
    available = await detector.check_now()

    # Wait for startup
    if await detector.wait_for_availability(timeout=60.0):
        print("LM Studio started successfully")

    # Get detailed status
    status = detector.get_status()
    print(f"Last check: {status['last_check_time']}")
"""

from openai import AsyncOpenAI
from dataclasses import dataclass, field
from typing import Optional
import asyncio
import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class AvailabilityState(Enum):
    """Possible availability states for LM Studio."""
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    CHECKING = "checking"


@dataclass
class DetectorStatus:
    """Detailed status information from the detector."""
    state: AvailabilityState
    last_check_time: Optional[float] = None  # Unix timestamp
    last_check_duration_ms: Optional[float] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    cache_hit: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "state": self.state.value,
            "is_available": self.state == AvailabilityState.AVAILABLE,
            "last_check_time": self.last_check_time,
            "last_check_time_iso": (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.last_check_time))
                if self.last_check_time else None
            ),
            "last_check_duration_ms": self.last_check_duration_ms,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "total_checks": self.total_checks,
            "cache_hit": self.cache_hit,
        }


class LMStudioDetector:
    """
    Detects LM Studio availability with smart retry and caching.

    Thread-safe for async usage. Uses the same openai.AsyncOpenAI client
    approach as ConsciousnessThinker for consistency.

    Attributes:
        base_url: LM Studio API endpoint
        timeout: Connection timeout in seconds
        retry_count: Number of retries before giving up
        cache_duration: How long to cache availability result (seconds)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        timeout: float = 5.0,
        retry_count: int = 2,
        cache_duration: float = 30.0,
    ):
        """
        Initialize the detector.

        Args:
            base_url: LM Studio API endpoint (default: http://localhost:1234/v1)
            timeout: Connection timeout in seconds (default: 5.0)
            retry_count: Number of retries with exponential backoff (default: 2)
            cache_duration: How long to cache the result in seconds (default: 30.0)
        """
        self.base_url = base_url
        self.timeout = timeout
        self.retry_count = retry_count
        self.cache_duration = cache_duration

        # Client with timeout configuration
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed",
            timeout=timeout,
        )

        # Cache state
        self._cached_available: Optional[bool] = None
        self._cache_timestamp: Optional[float] = None

        # Status tracking
        self._state = AvailabilityState.UNKNOWN
        self._last_check_time: Optional[float] = None
        self._last_check_duration_ms: Optional[float] = None
        self._last_error: Optional[str] = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._total_checks = 0

        # Lock for thread safety
        self._check_lock = asyncio.Lock()

    def _is_cache_valid(self) -> bool:
        """Check if the cached result is still valid."""
        if self._cached_available is None or self._cache_timestamp is None:
            return False

        age = time.time() - self._cache_timestamp
        return age < self.cache_duration

    async def is_available(self) -> bool:
        """
        Check if LM Studio is available (uses cache).

        Returns cached result if still valid, otherwise performs a fresh check.

        Returns:
            True if LM Studio is available, False otherwise
        """
        if self._is_cache_valid():
            logger.debug(f"Using cached availability result: {self._cached_available}")
            return self._cached_available

        return await self.check_now()

    async def check_now(self) -> bool:
        """
        Force a fresh availability check (bypasses cache).

        Performs the check with retry logic and exponential backoff.
        Updates the cache with the result.

        Returns:
            True if LM Studio is available, False otherwise
        """
        async with self._check_lock:
            return await self._perform_check()

    async def _perform_check(self) -> bool:
        """
        Internal method to perform the actual availability check.

        Uses exponential backoff for retries:
        - Attempt 1: immediate
        - Attempt 2: after 0.5s
        - Attempt 3: after 1.0s
        - etc.
        """
        self._state = AvailabilityState.CHECKING
        self._total_checks += 1

        start_time = time.time()
        last_exception: Optional[Exception] = None

        for attempt in range(self.retry_count + 1):
            if attempt > 0:
                # Exponential backoff: 0.5s, 1.0s, 2.0s, ...
                delay = 0.5 * (2 ** (attempt - 1))
                logger.debug(f"Retry {attempt}/{self.retry_count} after {delay}s delay")
                await asyncio.sleep(delay)

            try:
                # Attempt to list models - this is a lightweight check
                await self._client.models.list()

                # Success
                elapsed_ms = (time.time() - start_time) * 1000
                self._update_status(
                    available=True,
                    check_time=time.time(),
                    duration_ms=elapsed_ms,
                    error=None
                )

                logger.debug(f"LM Studio available (check took {elapsed_ms:.1f}ms)")
                return True

            except Exception as e:
                last_exception = e
                logger.debug(f"Check attempt {attempt + 1} failed: {e}")

        # All retries exhausted
        elapsed_ms = (time.time() - start_time) * 1000
        error_msg = str(last_exception) if last_exception else "Unknown error"

        self._update_status(
            available=False,
            check_time=time.time(),
            duration_ms=elapsed_ms,
            error=error_msg
        )

        logger.debug(f"LM Studio unavailable after {self.retry_count + 1} attempts: {error_msg}")
        return False

    def _update_status(
        self,
        available: bool,
        check_time: float,
        duration_ms: float,
        error: Optional[str]
    ) -> None:
        """Update internal status tracking."""
        self._cached_available = available
        self._cache_timestamp = check_time
        self._last_check_time = check_time
        self._last_check_duration_ms = duration_ms
        self._last_error = error

        if available:
            self._state = AvailabilityState.AVAILABLE
            self._consecutive_successes += 1
            self._consecutive_failures = 0
        else:
            self._state = AvailabilityState.UNAVAILABLE
            self._consecutive_failures += 1
            self._consecutive_successes = 0

    async def wait_for_availability(
        self,
        timeout: float = 60.0,
        poll_interval: float = 2.0
    ) -> bool:
        """
        Wait for LM Studio to become available.

        Polls periodically until LM Studio is available or timeout is reached.

        Args:
            timeout: Maximum time to wait in seconds (default: 60.0)
            poll_interval: Time between checks in seconds (default: 2.0)

        Returns:
            True if LM Studio became available, False if timeout reached
        """
        start_time = time.time()

        logger.info(f"Waiting for LM Studio availability (timeout: {timeout}s)")

        while (time.time() - start_time) < timeout:
            if await self.check_now():
                elapsed = time.time() - start_time
                logger.info(f"LM Studio became available after {elapsed:.1f}s")
                return True

            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                break

            # Wait before next poll, but don't exceed remaining timeout
            wait_time = min(poll_interval, remaining)
            await asyncio.sleep(wait_time)

        elapsed = time.time() - start_time
        logger.warning(f"LM Studio not available after {elapsed:.1f}s timeout")
        return False

    def get_status(self) -> dict:
        """
        Get detailed status information.

        Returns:
            Dictionary with comprehensive status information including:
            - state: Current availability state
            - is_available: Boolean availability flag
            - last_check_time: Unix timestamp of last check
            - last_check_time_iso: ISO formatted time of last check
            - last_check_duration_ms: How long the last check took
            - last_error: Last error message if any
            - consecutive_failures: Number of consecutive failed checks
            - consecutive_successes: Number of consecutive successful checks
            - total_checks: Total number of checks performed
            - cache_hit: Whether the last is_available() call used cache
        """
        status = DetectorStatus(
            state=self._state,
            last_check_time=self._last_check_time,
            last_check_duration_ms=self._last_check_duration_ms,
            last_error=self._last_error,
            consecutive_failures=self._consecutive_failures,
            consecutive_successes=self._consecutive_successes,
            total_checks=self._total_checks,
            cache_hit=self._is_cache_valid(),
        )
        return status.to_dict()

    def invalidate_cache(self) -> None:
        """
        Manually invalidate the cache.

        Forces the next is_available() call to perform a fresh check.
        """
        self._cached_available = None
        self._cache_timestamp = None
        logger.debug("Cache invalidated")

    def get_cache_age(self) -> Optional[float]:
        """
        Get the age of the cached result in seconds.

        Returns:
            Age in seconds, or None if no cached result exists
        """
        if self._cache_timestamp is None:
            return None
        return time.time() - self._cache_timestamp

    @property
    def is_cache_valid(self) -> bool:
        """Check if cache contains a valid result."""
        return self._is_cache_valid()

    @property
    def last_known_state(self) -> AvailabilityState:
        """Get the last known availability state."""
        return self._state

    async def health_check(self) -> dict:
        """
        Perform a comprehensive health check.

        This method performs a fresh check and returns detailed results.
        Useful for diagnostics and monitoring.

        Returns:
            Dictionary with health check results including:
            - healthy: Boolean indicating overall health
            - status: Detailed status information
            - endpoint: The endpoint being checked
            - config: Current detector configuration
        """
        available = await self.check_now()

        return {
            "healthy": available,
            "status": self.get_status(),
            "endpoint": self.base_url,
            "config": {
                "timeout": self.timeout,
                "retry_count": self.retry_count,
                "cache_duration": self.cache_duration,
            }
        }


# Convenience function for quick one-off checks
async def is_lm_studio_available(
    base_url: str = "http://localhost:1234/v1",
    timeout: float = 5.0
) -> bool:
    """
    Quick one-off check for LM Studio availability.

    Creates a temporary detector and performs a single check.
    For repeated checks, use LMStudioDetector directly to benefit from caching.

    Args:
        base_url: LM Studio API endpoint
        timeout: Connection timeout in seconds

    Returns:
        True if LM Studio is available, False otherwise
    """
    detector = LMStudioDetector(
        base_url=base_url,
        timeout=timeout,
        retry_count=0,  # Single check
        cache_duration=0,  # No caching for one-off
    )
    return await detector.check_now()


if __name__ == "__main__":
    # Demo/test script
    async def demo():
        """Demonstrate detector functionality."""
        print("LM Studio Detector Demo")
        print("=" * 50)

        detector = LMStudioDetector(
            timeout=3.0,
            retry_count=1,
            cache_duration=10.0
        )

        # Initial check
        print("\n1. Initial availability check...")
        available = await detector.is_available()
        print(f"   Available: {available}")

        # Show status
        status = detector.get_status()
        print(f"   State: {status['state']}")
        print(f"   Check duration: {status['last_check_duration_ms']:.1f}ms")
        if status['last_error']:
            print(f"   Error: {status['last_error']}")

        # Test cache
        print("\n2. Second check (should use cache)...")
        available2 = await detector.is_available()
        print(f"   Available: {available2}")
        print(f"   Cache hit: {detector.get_status()['cache_hit']}")
        print(f"   Cache age: {detector.get_cache_age():.1f}s")

        # Force fresh check
        print("\n3. Forced fresh check (bypass cache)...")
        available3 = await detector.check_now()
        print(f"   Available: {available3}")

        # Health check
        print("\n4. Comprehensive health check...")
        health = await detector.health_check()
        print(f"   Healthy: {health['healthy']}")
        print(f"   Total checks: {health['status']['total_checks']}")
        print(f"   Config: {health['config']}")

        if not available:
            print("\n5. Waiting for availability (10s timeout)...")
            became_available = await detector.wait_for_availability(timeout=10.0)
            if became_available:
                print("   LM Studio is now available!")
            else:
                print("   Timeout reached - LM Studio not available")

        print("\nDemo complete.")

    asyncio.run(demo())
