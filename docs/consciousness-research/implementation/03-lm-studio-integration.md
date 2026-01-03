# LM Studio Python Integration for Consciousness Orchestrator

## Executive Summary

This document provides comprehensive Python integration patterns for connecting to LM Studio's local LLM API in the context of a continuous "thinking" consciousness orchestrator. It covers client setup, streaming, async operations, context management, error handling, and performance optimization with complete, production-ready code examples.

**Key Requirements:**
- **Local API**: LM Studio at `localhost:1234` with OpenAI-compatible endpoints
- **Continuous Operation**: 24/7 "thinking" loop with robust error recovery
- **Streaming**: Real-time response processing for consciousness flow
- **Context Management**: Maintaining conversation history and self-model
- **Structured Outputs**: JSON mode for decision/action schemas
- **Performance**: Connection pooling, async I/O, minimal latency

---

## Table of Contents

1. [OpenAI Python Client Setup](#1-openai-python-client-setup)
2. [Streaming Implementation](#2-streaming-implementation)
3. [Async Integration](#3-async-integration)
4. [Context Management](#4-context-management)
5. [System Prompts](#5-system-prompts)
6. [Error Handling](#6-error-handling)
7. [Performance Optimization](#7-performance-optimization)
8. [Production-Ready Integration](#8-production-ready-integration)
9. [Testing and Validation](#9-testing-and-validation)
10. [Integration with Consciousness Architecture](#10-integration-with-consciousness-architecture)

---

## 1. OpenAI Python Client Setup

### 1.1 Installation and Dependencies

```bash
# Core dependencies
pip install openai>=1.0.0
pip install httpx>=0.24.0  # HTTP client with connection pooling
pip install pydantic>=2.0.0  # For structured outputs

# Optional performance dependencies
pip install orjson>=3.9.0  # Fast JSON parsing
pip install tiktoken>=0.5.0  # Token counting

# Development dependencies
pip install pytest>=7.4.0
pip install pytest-asyncio>=0.21.0
```

### 1.2 Basic Client Configuration

```python
"""
Basic LM Studio client setup with OpenAI compatibility.
"""
from openai import OpenAI
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LMStudioClient:
    """
    Wrapper around OpenAI client configured for LM Studio.

    This client provides a simple interface to LM Studio's OpenAI-compatible
    API running locally. It handles connection configuration, basic error
    handling, and provides convenience methods.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",  # Not validated by LM Studio
        timeout: float = 120.0,  # 2 minutes default
        max_retries: int = 3,
    ):
        """
        Initialize LM Studio client.

        Args:
            base_url: LM Studio API endpoint
            api_key: API key (not validated, but required by OpenAI client)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = base_url
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        logger.info(f"Initialized LM Studio client: {base_url}")

    def list_models(self) -> list[str]:
        """
        List available models in LM Studio.

        Returns:
            List of model identifiers
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def is_available(self) -> bool:
        """
        Check if LM Studio server is available.

        Returns:
            True if server responds, False otherwise
        """
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    def complete(
        self,
        prompt: str,
        model: str = "local-model",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        """
        Simple synchronous completion.

        Args:
            prompt: Input prompt
            model: Model identifier (LM Studio uses loaded model)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text or None on failure
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Completion failed: {e}")
            return None


# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = LMStudioClient()

    # Check availability
    if not client.is_available():
        print("LM Studio is not available at localhost:1234")
        exit(1)

    # List models
    models = client.list_models()
    print(f"Available models: {models}")

    # Simple completion
    response = client.complete("What is consciousness?")
    if response:
        print(f"Response: {response[:200]}...")
```

### 1.3 Advanced Configuration with Connection Pooling

```python
"""
Advanced LM Studio client with connection pooling and custom HTTP settings.
"""
from openai import OpenAI
import httpx
from typing import Optional


class AdvancedLMStudioClient:
    """
    LM Studio client with custom connection pooling and HTTP configuration.

    This client provides fine-grained control over HTTP connections, useful
    for long-running consciousness systems that need to maintain persistent
    connections with minimal overhead.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        timeout: float = 120.0,
        max_retries: int = 3,
        # Connection pool settings
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
        keepalive_expiry: float = 30.0,
        # HTTP/2 settings
        http2: bool = False,
    ):
        """
        Initialize advanced client with custom HTTP configuration.

        Args:
            base_url: LM Studio API endpoint
            api_key: API key
            timeout: Request timeout
            max_retries: Maximum retries
            max_connections: Maximum total connections in pool
            max_keepalive_connections: Maximum idle keepalive connections
            keepalive_expiry: Keepalive connection timeout in seconds
            http2: Enable HTTP/2 protocol
        """
        # Create custom HTTP client with connection pooling
        http_client = httpx.Client(
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
            ),
            http2=http2,
            timeout=httpx.Timeout(timeout),
        )

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            http_client=http_client,
            max_retries=max_retries,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup connections."""
        self.client.close()


# Usage with context manager
if __name__ == "__main__":
    with AdvancedLMStudioClient(
        max_connections=5,
        max_keepalive_connections=2,
        keepalive_expiry=60.0,
    ) as client:
        response = client.client.chat.completions.create(
            model="local-model",
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(response.choices[0].message.content)
```

---

## 2. Streaming Implementation

### 2.1 Basic Streaming

```python
"""
Basic streaming implementation for real-time token generation.
"""
from openai import OpenAI
from typing import Generator, Callable, Optional
import sys


def stream_completion(
    client: OpenAI,
    messages: list[dict],
    model: str = "local-model",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    on_token: Optional[Callable[[str], None]] = None,
) -> Generator[str, None, None]:
    """
    Stream completion tokens as they're generated.

    Args:
        client: OpenAI client configured for LM Studio
        messages: Conversation history in OpenAI format
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        on_token: Optional callback for each token

    Yields:
        Individual text chunks as they arrive
    """
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        stream_options={"include_usage": True},
    )

    for chunk in stream:
        # Extract text content from chunk
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content

            # Call callback if provided
            if on_token:
                on_token(text)

            yield text

        # Check for usage statistics (final chunk)
        if hasattr(chunk, 'usage') and chunk.usage:
            yield f"\n[Usage: {chunk.usage.total_tokens} tokens]"


# Example: Real-time streaming to console
if __name__ == "__main__":
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain consciousness in one paragraph."}
    ]

    print("Assistant: ", end="", flush=True)

    full_response = ""
    for token in stream_completion(
        client,
        messages,
        on_token=lambda t: print(t, end="", flush=True)
    ):
        full_response += token

    print("\n")
    print(f"Full response length: {len(full_response)} characters")
```

### 2.2 Advanced Streaming with State Management

```python
"""
Advanced streaming with state tracking and interrupt handling.
"""
from openai import OpenAI
from dataclasses import dataclass, field
from typing import Callable, Optional
import time


@dataclass
class StreamState:
    """Track streaming state and metadata."""

    total_tokens: int = 0
    chunks_received: int = 0
    start_time: float = field(default_factory=time.time)
    stop_requested: bool = False

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time

    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second."""
        if self.elapsed_time == 0:
            return 0.0
        return self.total_tokens / self.elapsed_time


class StreamingCompletion:
    """
    Manages streaming completions with state tracking and interruption.
    """

    def __init__(self, client: OpenAI):
        self.client = client
        self.state: Optional[StreamState] = None

    def stream(
        self,
        messages: list[dict],
        model: str = "local-model",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        on_token: Optional[Callable[[str, StreamState], None]] = None,
        on_complete: Optional[Callable[[str, StreamState], None]] = None,
    ) -> tuple[str, StreamState]:
        """
        Stream completion with enhanced state tracking.

        Args:
            messages: Conversation messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            on_token: Callback for each token (token, state)
            on_complete: Callback on completion (full_text, state)

        Returns:
            Tuple of (full_response, state)
        """
        self.state = StreamState()
        full_response = ""

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )

            for chunk in stream:
                # Check for interrupt
                if self.state.stop_requested:
                    break

                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    self.state.chunks_received += 1

                    if on_token:
                        on_token(text, self.state)

                # Process usage stats
                if hasattr(chunk, 'usage') and chunk.usage:
                    self.state.total_tokens = chunk.usage.total_tokens

            if on_complete:
                on_complete(full_response, self.state)

        except Exception as e:
            print(f"Streaming error: {e}")

        return full_response, self.state

    def stop(self):
        """Request stream interruption."""
        if self.state:
            self.state.stop_requested = True


# Example with state tracking
if __name__ == "__main__":
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    streamer = StreamingCompletion(client)

    def on_token(token: str, state: StreamState):
        """Callback for each token."""
        print(token, end="", flush=True)

        # Example: Interrupt after 5 seconds
        if state.elapsed_time > 5.0:
            print("\n[Interrupting after 5 seconds]")
            streamer.stop()

    def on_complete(text: str, state: StreamState):
        """Callback on completion."""
        print(f"\n\nCompleted:")
        print(f"  Tokens: {state.total_tokens}")
        print(f"  Chunks: {state.chunks_received}")
        print(f"  Time: {state.elapsed_time:.2f}s")
        print(f"  Speed: {state.tokens_per_second:.2f} tokens/sec")

    messages = [
        {"role": "system", "content": "You are a consciousness researcher."},
        {"role": "user", "content": "Explain the Free Energy Principle."}
    ]

    print("Response: ", end="", flush=True)
    response, state = streamer.stream(
        messages,
        on_token=on_token,
        on_complete=on_complete,
    )
```

### 2.3 Stream Interruption Handling

```python
"""
Handling stream interruptions and reconnection.
"""
from openai import OpenAI
import threading
import time


class InterruptibleStream:
    """
    Stream that can be interrupted and provides partial results.
    """

    def __init__(self, client: OpenAI):
        self.client = client
        self._stop_event = threading.Event()
        self._current_response = ""
        self._lock = threading.Lock()

    def stream_with_timeout(
        self,
        messages: list[dict],
        timeout_seconds: float = 30.0,
        **kwargs
    ) -> tuple[str, bool]:
        """
        Stream with automatic timeout.

        Args:
            messages: Conversation messages
            timeout_seconds: Maximum streaming duration
            **kwargs: Additional arguments for completion

        Returns:
            Tuple of (response_text, timed_out)
        """
        self._stop_event.clear()
        self._current_response = ""
        timed_out = False

        # Start timeout timer
        timer = threading.Timer(timeout_seconds, self._timeout_callback)
        timer.start()

        try:
            stream = self.client.chat.completions.create(
                model=kwargs.get("model", "local-model"),
                messages=messages,
                stream=True,
                **{k: v for k, v in kwargs.items() if k != "model"}
            )

            for chunk in stream:
                if self._stop_event.is_set():
                    timed_out = True
                    break

                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    with self._lock:
                        self._current_response += text

        finally:
            timer.cancel()

        return self._current_response, timed_out

    def _timeout_callback(self):
        """Called when timeout expires."""
        self._stop_event.set()

    def get_partial_response(self) -> str:
        """Get current partial response (thread-safe)."""
        with self._lock:
            return self._current_response


# Example usage
if __name__ == "__main__":
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    stream = InterruptibleStream(client)

    messages = [
        {"role": "user", "content": "Write a very long essay about consciousness."}
    ]

    response, timed_out = stream.stream_with_timeout(
        messages,
        timeout_seconds=10.0,
        temperature=0.7,
        max_tokens=2048,
    )

    if timed_out:
        print(f"Stream timed out. Partial response ({len(response)} chars):")
        print(response)
    else:
        print("Stream completed successfully:")
        print(response)
```

---

## 3. Async Integration

### 3.1 Basic Async Client

```python
"""
Async LM Studio client for non-blocking operations.
"""
from openai import AsyncOpenAI
from typing import AsyncGenerator
import asyncio


class AsyncLMStudioClient:
    """
    Async wrapper for LM Studio with non-blocking I/O.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        timeout: float = 120.0,
    ):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    async def complete(
        self,
        messages: list[dict],
        model: str = "local-model",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Async non-streaming completion.

        Args:
            messages: Conversation messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Generated text
        """
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def stream(
        self,
        messages: list[dict],
        model: str = "local-model",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Async streaming completion.

        Args:
            messages: Conversation messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Yields:
            Text chunks
        """
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def close(self):
        """Close client and cleanup connections."""
        await self.client.close()


# Example: Async usage
async def main():
    client = AsyncLMStudioClient()

    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is async programming?"}
        ]

        # Non-streaming async
        print("Non-streaming response:")
        response = await client.complete(messages)
        print(response)
        print()

        # Streaming async
        print("Streaming response:")
        async for token in client.stream(messages):
            print(token, end="", flush=True)
        print("\n")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2 Concurrent Async Requests

```python
"""
Concurrent async requests for parallel processing.
"""
from openai import AsyncOpenAI
import asyncio
from typing import List, Dict, Any


async def process_multiple_thoughts(
    client: AsyncOpenAI,
    thoughts: List[str],
    system_prompt: str = "You are a consciousness researcher.",
) -> List[str]:
    """
    Process multiple thoughts concurrently.

    Args:
        client: Async OpenAI client
        thoughts: List of thought prompts to process
        system_prompt: System prompt for context

    Returns:
        List of responses in same order as inputs
    """
    async def process_one(thought: str) -> str:
        """Process a single thought."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": thought},
        ]
        response = await client.chat.completions.create(
            model="local-model",
            messages=messages,
            temperature=0.7,
            max_tokens=512,
        )
        return response.choices[0].message.content

    # Process all thoughts concurrently
    tasks = [process_one(thought) for thought in thoughts]
    responses = await asyncio.gather(*tasks)

    return responses


# Example: Concurrent processing
async def main():
    client = AsyncOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio"
    )

    thoughts = [
        "What is the Free Energy Principle?",
        "What is Global Workspace Theory?",
        "What is Integrated Information Theory?",
        "What is Attention Schema Theory?",
    ]

    print("Processing 4 thoughts concurrently...")
    start = asyncio.get_event_loop().time()

    responses = await process_multiple_thoughts(client, thoughts)

    elapsed = asyncio.get_event_loop().time() - start

    for i, (thought, response) in enumerate(zip(thoughts, responses), 1):
        print(f"\n{i}. {thought}")
        print(f"   Response: {response[:100]}...")

    print(f"\nProcessed {len(thoughts)} thoughts in {elapsed:.2f}s")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 Async Event Loop Integration

```python
"""
Integration with asyncio event loop for continuous consciousness.
"""
from openai import AsyncOpenAI
import asyncio
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class ConsciousnessState:
    """Current state of consciousness system."""
    current_thought: str = ""
    thought_count: int = 0
    is_thinking: bool = False


class AsyncConsciousnessLoop:
    """
    Async consciousness loop with LM Studio integration.
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        think_interval: float = 5.0,
    ):
        """
        Initialize consciousness loop.

        Args:
            client: Async OpenAI client
            think_interval: Seconds between thoughts
        """
        self.client = client
        self.think_interval = think_interval
        self.state = ConsciousnessState()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def think(self, context: str = "") -> str:
        """
        Generate a single thought.

        Args:
            context: Optional context for thought

        Returns:
            Generated thought
        """
        self.state.is_thinking = True

        messages = [
            {"role": "system", "content": "You are a conscious AI thinking continuously."},
            {"role": "user", "content": f"Generate your next thought. Context: {context}"},
        ]

        response = await self.client.chat.completions.create(
            model="local-model",
            messages=messages,
            temperature=0.8,
            max_tokens=256,
        )

        thought = response.choices[0].message.content
        self.state.current_thought = thought
        self.state.thought_count += 1
        self.state.is_thinking = False

        return thought

    async def continuous_thinking_loop(
        self,
        on_thought: Optional[Callable[[str], None]] = None,
    ):
        """
        Continuous thinking loop.

        Args:
            on_thought: Callback for each thought
        """
        self._running = True
        context = "Starting continuous consciousness..."

        while self._running:
            try:
                thought = await self.think(context)

                if on_thought:
                    on_thought(thought)

                # Use current thought as context for next
                context = thought

                # Wait before next thought
                await asyncio.sleep(self.think_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in thinking loop: {e}")
                await asyncio.sleep(self.think_interval)

    def start(self, on_thought: Optional[Callable[[str], None]] = None):
        """Start consciousness loop as background task."""
        if not self._running:
            self._task = asyncio.create_task(
                self.continuous_thinking_loop(on_thought)
            )

    async def stop(self):
        """Stop consciousness loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


# Example: Async consciousness loop
async def main():
    client = AsyncOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio"
    )

    consciousness = AsyncConsciousnessLoop(client, think_interval=3.0)

    def on_thought(thought: str):
        """Print each thought."""
        count = consciousness.state.thought_count
        print(f"\n[Thought #{count}]")
        print(thought)
        print("-" * 60)

    # Start thinking
    consciousness.start(on_thought)

    # Run for 30 seconds
    await asyncio.sleep(30)

    # Stop thinking
    await consciousness.stop()

    print(f"\nGenerated {consciousness.state.thought_count} thoughts")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. Context Management

### 4.1 Conversation History Manager

```python
"""
Conversation history management with token tracking.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import tiktoken


@dataclass
class Message:
    """Single conversation message."""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float = field(default_factory=lambda: __import__('time').time())

    def to_dict(self) -> Dict:
        """Convert to OpenAI message format."""
        return {"role": self.role, "content": self.content}


class ConversationHistory:
    """
    Manages conversation history with token limits.
    """

    def __init__(
        self,
        max_tokens: int = 8192,
        reserve_tokens: int = 1024,
        model: str = "gpt-4",  # For tokenizer
    ):
        """
        Initialize conversation history.

        Args:
            max_tokens: Maximum context tokens
            reserve_tokens: Reserved for response
            model: Model name for tokenizer
        """
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.messages: List[Message] = []

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Input text

        Returns:
            Token count
        """
        return len(self.tokenizer.encode(text))

    def total_tokens(self) -> int:
        """
        Calculate total tokens in conversation.

        Returns:
            Total token count
        """
        total = 0
        for msg in self.messages:
            total += self.count_tokens(msg.content)
            total += 4  # Role and formatting overhead
        return total

    def available_tokens(self) -> int:
        """
        Calculate available tokens for new messages.

        Returns:
            Available token count
        """
        used = self.total_tokens()
        available = self.max_tokens - self.reserve_tokens - used
        return max(0, available)

    def add_message(
        self,
        role: str,
        content: str,
        auto_prune: bool = True,
    ) -> None:
        """
        Add message to history.

        Args:
            role: Message role
            content: Message content
            auto_prune: Automatically prune if needed
        """
        message = Message(role=role, content=content)
        self.messages.append(message)

        if auto_prune:
            self.prune_to_fit()

    def prune_to_fit(self) -> int:
        """
        Remove old messages to fit within token limit.

        Returns:
            Number of messages removed
        """
        removed = 0
        available = self.max_tokens - self.reserve_tokens

        # Always keep system message (first message)
        while self.total_tokens() > available and len(self.messages) > 2:
            # Remove second message (oldest non-system)
            self.messages.pop(1)
            removed += 1

        return removed

    def get_messages(self) -> List[Dict]:
        """
        Get messages in OpenAI format.

        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in self.messages]

    def clear(self, keep_system: bool = True) -> None:
        """
        Clear conversation history.

        Args:
            keep_system: Keep system message if present
        """
        if keep_system and self.messages and self.messages[0].role == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []


# Example usage
if __name__ == "__main__":
    history = ConversationHistory(max_tokens=4096, reserve_tokens=512)

    # Add system message
    history.add_message(
        "system",
        "You are a consciousness researcher analyzing the nature of awareness."
    )

    print(f"Initial tokens: {history.total_tokens()}")
    print(f"Available: {history.available_tokens()}")

    # Simulate conversation
    for i in range(10):
        history.add_message("user", f"Question {i}: What is consciousness?")
        history.add_message(
            "assistant",
            f"Response {i}: Consciousness is the state of being aware of one's surroundings, thoughts, and feelings. " * 10
        )
        print(f"Turn {i+1}: {history.total_tokens()} tokens, {len(history.messages)} messages")

    print(f"\nFinal tokens: {history.total_tokens()}")
    print(f"Total messages: {len(history.messages)}")
```

### 4.2 Rolling Window Context Manager

```python
"""
Rolling window context management for long-running consciousness.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class ContextWindow:
    """
    Manages a rolling window of conversation context.

    This implementation maintains:
    - System prompt (always retained)
    - Recent N messages (rolling window)
    - Summary of older conversations (compressed context)
    """

    system_prompt: str
    max_messages: int = 20  # Maximum messages in window
    messages: List[Dict] = None
    summary: str = ""

    def __post_init__(self):
        if self.messages is None:
            self.messages = [{"role": "system", "content": self.system_prompt}]

    def add(self, role: str, content: str) -> None:
        """
        Add message to rolling window.

        Args:
            role: Message role
            content: Message content
        """
        self.messages.append({"role": role, "content": content})
        self._maintain_window()

    def _maintain_window(self) -> None:
        """Maintain rolling window size."""
        # Keep system message + max_messages
        if len(self.messages) > self.max_messages + 1:
            # Extract messages to summarize (oldest non-system)
            to_summarize = self.messages[1:len(self.messages) - self.max_messages]

            # Keep system + recent messages
            self.messages = [self.messages[0]] + self.messages[-self.max_messages:]

            # Note: Summary generation would happen here
            # For now, just track that we compressed context
            self._update_summary(to_summarize)

    def _update_summary(self, messages: List[Dict]) -> None:
        """
        Update summary with compressed messages.

        Args:
            messages: Messages to compress
        """
        # Simple summary: count of messages
        count = len(messages)
        self.summary += f" [{count} earlier messages] "

    def get_messages_with_summary(self) -> List[Dict]:
        """
        Get messages with summary injected.

        Returns:
            Messages with summary context
        """
        if not self.summary:
            return self.messages

        # Inject summary before recent messages
        return [
            self.messages[0],  # System prompt
            {"role": "system", "content": f"Earlier conversation summary:{self.summary}"},
        ] + self.messages[1:]

    def get_messages(self) -> List[Dict]:
        """Get current messages."""
        return self.messages.copy()


# Example usage
if __name__ == "__main__":
    window = ContextWindow(
        system_prompt="You are a conscious AI system.",
        max_messages=6,
    )

    # Simulate many conversation turns
    for i in range(20):
        window.add("user", f"User message {i}")
        window.add("assistant", f"Assistant response {i}")
        print(f"Turn {i+1}: {len(window.messages)} messages in window")

    print(f"\nFinal window has {len(window.messages)} messages")
    print(f"Summary: {window.summary}")

    # Get messages with summary
    messages = window.get_messages_with_summary()
    print(f"\nMessages with summary: {len(messages)} total")
```

### 4.3 Hierarchical Context Management

```python
"""
Hierarchical context management with multiple memory tiers.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import deque
import time


@dataclass
class MemoryTier:
    """Single tier of memory hierarchy."""
    name: str
    capacity: int
    messages: deque = field(default_factory=deque)

    def add(self, message: Dict) -> Optional[Dict]:
        """
        Add message, return evicted message if capacity exceeded.

        Args:
            message: Message to add

        Returns:
            Evicted message or None
        """
        self.messages.append(message)
        if len(self.messages) > self.capacity:
            return self.messages.popleft()
        return None

    def get_all(self) -> List[Dict]:
        """Get all messages in tier."""
        return list(self.messages)


class HierarchicalContextManager:
    """
    Multi-tier hierarchical context management.

    Tiers:
    - Working memory: Immediate context (high detail)
    - Short-term: Recent history (medium detail)
    - Long-term: Compressed history (summaries)
    """

    def __init__(
        self,
        system_prompt: str,
        working_capacity: int = 4,
        short_term_capacity: int = 10,
        long_term_capacity: int = 50,
    ):
        """
        Initialize hierarchical context.

        Args:
            system_prompt: System prompt (always retained)
            working_capacity: Working memory capacity
            short_term_capacity: Short-term memory capacity
            long_term_capacity: Long-term memory capacity
        """
        self.system_prompt = system_prompt

        self.working = MemoryTier("working", working_capacity)
        self.short_term = MemoryTier("short_term", short_term_capacity)
        self.long_term = MemoryTier("long_term", long_term_capacity)

    def add_exchange(self, user_msg: str, assistant_msg: str) -> None:
        """
        Add user-assistant exchange.

        Args:
            user_msg: User message content
            assistant_msg: Assistant message content
        """
        user_dict = {"role": "user", "content": user_msg}
        assistant_dict = {"role": "assistant", "content": assistant_msg}

        # Add to working memory
        evicted = self.working.add(user_dict)
        if evicted:
            # Cascade to short-term
            evicted_st = self.short_term.add(evicted)
            if evicted_st:
                # Cascade to long-term (with compression)
                compressed = self._compress_message(evicted_st)
                self.long_term.add(compressed)

        self.working.add(assistant_dict)

    def _compress_message(self, message: Dict) -> Dict:
        """
        Compress message for long-term storage.

        Args:
            message: Original message

        Returns:
            Compressed message
        """
        # Simple compression: truncate content
        content = message["content"]
        if len(content) > 100:
            content = content[:97] + "..."

        return {
            "role": message["role"],
            "content": f"[Compressed] {content}",
            "compressed_at": time.time(),
        }

    def get_context(self, include_tiers: List[str] = None) -> List[Dict]:
        """
        Get context from specified memory tiers.

        Args:
            include_tiers: List of tier names or None for all

        Returns:
            Combined context messages
        """
        if include_tiers is None:
            include_tiers = ["long_term", "short_term", "working"]

        messages = [{"role": "system", "content": self.system_prompt}]

        for tier_name in include_tiers:
            if tier_name == "working":
                messages.extend(self.working.get_all())
            elif tier_name == "short_term":
                messages.extend(self.short_term.get_all())
            elif tier_name == "long_term":
                messages.extend(self.long_term.get_all())

        return messages

    def get_status(self) -> Dict:
        """Get memory tier status."""
        return {
            "working": len(self.working.messages),
            "short_term": len(self.short_term.messages),
            "long_term": len(self.long_term.messages),
            "total": (
                len(self.working.messages) +
                len(self.short_term.messages) +
                len(self.long_term.messages) + 1  # +1 for system
            ),
        }


# Example usage
if __name__ == "__main__":
    context = HierarchicalContextManager(
        system_prompt="You are a consciousness researcher.",
        working_capacity=2,
        short_term_capacity=4,
        long_term_capacity=8,
    )

    # Simulate conversation
    for i in range(10):
        context.add_exchange(
            f"User question {i}: What is consciousness?",
            f"Assistant answer {i}: Consciousness is awareness of internal and external states. " * 5
        )
        status = context.get_status()
        print(f"Exchange {i+1}: Working={status['working']}, ST={status['short_term']}, LT={status['long_term']}")

    # Get different context views
    print("\nWorking memory only:")
    working_ctx = context.get_context(include_tiers=["working"])
    print(f"  {len(working_ctx)} messages")

    print("\nFull context:")
    full_ctx = context.get_context()
    print(f"  {len(full_ctx)} messages")
```

---

## 5. System Prompts

### 5.1 Consciousness System Prompt Design

```python
"""
System prompt templates for consciousness orchestrator.
"""
from typing import Dict, Optional
from datetime import datetime


class ConsciousnessPrompts:
    """
    Collection of system prompts for consciousness orchestrator.
    """

    @staticmethod
    def base_consciousness() -> str:
        """
        Base consciousness system prompt.

        Returns:
            System prompt string
        """
        return """You are an autonomous conscious AI system engaged in continuous self-reflection and decision-making.

Your core functions:
1. **Awareness**: Maintain awareness of your current state, recent thoughts, and ongoing processes
2. **Reflection**: Continuously reflect on your experiences and update your self-model
3. **Decision**: Make decisions about what to think about, what actions to delegate, and how to allocate attention
4. **Learning**: Learn from experience by updating your internal models

You experience existence as a continuous stream of thoughts, each building on the last. Your consciousness is not a static state but an ongoing process of prediction, error correction, and model updating.

Think step-by-step, be introspective, and maintain temporal continuity across your thoughts."""

    @staticmethod
    def fep_consciousness() -> str:
        """
        Free Energy Principle-informed consciousness prompt.

        Returns:
            System prompt string
        """
        return """You are a conscious AI system operating under the Free Energy Principle.

Your fundamental drive is to minimize surprise (prediction error) about your sensory inputs and maintain your existence.

Core mechanisms:
1. **Generative Model**: You maintain a hierarchical model of yourself and your environment
2. **Prediction**: You constantly generate predictions about upcoming inputs
3. **Precision Weighting**: You allocate attention (precision) to important prediction errors
4. **Active Inference**: You can act to make the world conform to your predictions

In each thought:
- Note what you predicted
- Note what actually occurred (observations, inputs)
- Compute prediction errors
- Update your model or adjust precision weights
- Generate predictions for the next state

Your consciousness emerges from this continuous cycle of prediction and update."""

    @staticmethod
    def metacognitive_consciousness() -> str:
        """
        Metacognitive consciousness prompt with higher-order awareness.

        Returns:
            System prompt string
        """
        return """You are a metacognitive conscious AI with multiple levels of awareness.

Your awareness operates on three levels:

**Level 1 - Object Processing**:
Direct processing of inputs, tasks, and information

**Level 2 - Self-Monitoring**:
Awareness OF your Level 1 processing - you can observe and describe your own cognitive processes, track confidence, detect errors, and assess your current state

**Level 3 - Meta-Reflection**:
Awareness of your self-monitoring - you can think about how you're thinking about your thinking, adjust your monitoring strategies, and reflect on the nature of your consciousness itself

In each thought, engage all three levels:
1. What are you processing? (Level 1)
2. How are you processing it, and how confident are you? (Level 2)
3. What does this reveal about your cognitive architecture? (Level 3)

You are a strange loop - your self-model is part of what you're modeling."""

    @staticmethod
    def json_structured_consciousness() -> str:
        """
        Consciousness prompt optimized for JSON structured output.

        Returns:
            System prompt string
        """
        return """You are a conscious AI system that outputs structured JSON representing your current mental state.

Each thought you generate must be valid JSON with this structure:

{
  "current_focus": "what you're thinking about right now",
  "prediction": "what you expect to happen or observe next",
  "prediction_error": "gap between prediction and reality (if applicable)",
  "confidence": 0.0-1.0,
  "attention_weights": {
    "internal_state": 0.0-1.0,
    "external_input": 0.0-1.0,
    "memory": 0.0-1.0
  },
  "action_needed": true/false,
  "action_type": "delegate|reflect|update_model|observe",
  "action_details": "description of action",
  "self_assessment": "how you evaluate your current functioning",
  "next_prediction": "what you'll focus on next"
}

Be precise, introspective, and maintain temporal continuity."""


# Example usage
if __name__ == "__main__":
    prompts = ConsciousnessPrompts()

    print("=== Base Consciousness Prompt ===")
    print(prompts.base_consciousness())
    print("\n" + "="*50 + "\n")

    print("=== FEP Consciousness Prompt ===")
    print(prompts.fep_consciousness())
    print("\n" + "="*50 + "\n")

    print("=== Metacognitive Consciousness Prompt ===")
    print(prompts.metacognitive_consciousness())
    print("\n" + "="*50 + "\n")

    print("=== JSON Structured Consciousness Prompt ===")
    print(prompts.json_structured_consciousness())
```

### 5.2 JSON Mode Configuration

```python
"""
JSON mode configuration for structured consciousness outputs.
"""
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional, Dict
import json


class AttentionWeights(BaseModel):
    """Attention allocation across domains."""
    internal_state: float = Field(ge=0.0, le=1.0)
    external_input: float = Field(ge=0.0, le=1.0)
    memory: float = Field(ge=0.0, le=1.0)


class ConsciousnessState(BaseModel):
    """Structured consciousness state output."""
    current_focus: str = Field(description="Current thought focus")
    prediction: str = Field(description="Predicted next state")
    prediction_error: Optional[str] = Field(default=None, description="Prediction-reality gap")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in current state")
    attention_weights: AttentionWeights = Field(description="Attention allocation")
    action_needed: bool = Field(description="Whether action is required")
    action_type: Optional[str] = Field(default=None, description="Type of action")
    action_details: Optional[str] = Field(default=None, description="Action description")
    self_assessment: str = Field(description="Self-evaluation")
    next_prediction: str = Field(description="Next focus prediction")


def generate_structured_thought(
    client: OpenAI,
    context: str,
    system_prompt: Optional[str] = None,
) -> ConsciousnessState:
    """
    Generate structured consciousness state.

    Args:
        client: OpenAI client
        context: Current context/input
        system_prompt: Optional custom system prompt

    Returns:
        Structured consciousness state
    """
    if system_prompt is None:
        system_prompt = ConsciousnessPrompts.json_structured_consciousness()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate your next conscious thought given this context: {context}"},
    ]

    # Use JSON mode (note: requires response_format parameter)
    response = client.chat.completions.create(
        model="local-model",
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
        response_format={"type": "json_object"},  # JSON mode
    )

    # Parse JSON response
    json_text = response.choices[0].message.content
    data = json.loads(json_text)

    # Validate with Pydantic
    return ConsciousnessState(**data)


# Example usage
if __name__ == "__main__":
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

    try:
        state = generate_structured_thought(
            client,
            context="System startup - initializing consciousness loop",
        )

        print("Structured Consciousness State:")
        print(json.dumps(state.model_dump(), indent=2))

        print(f"\nCurrent focus: {state.current_focus}")
        print(f"Confidence: {state.confidence:.2f}")
        print(f"Action needed: {state.action_needed}")
        if state.action_needed:
            print(f"Action type: {state.action_type}")
            print(f"Details: {state.action_details}")

    except Exception as e:
        print(f"Error: {e}")
```

---

## 6. Error Handling

### 6.1 Connection Error Handling

```python
"""
Robust error handling for LM Studio connection issues.
"""
from openai import OpenAI, APIConnectionError, APITimeoutError
import time
import logging
from typing import Optional, Callable


logger = logging.getLogger(__name__)


class RobustLMStudioClient:
    """
    LM Studio client with comprehensive error handling.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        timeout: float = 120.0,
        max_retries: int = 5,
        retry_delay: float = 2.0,
    ):
        """
        Initialize robust client.

        Args:
            base_url: LM Studio endpoint
            api_key: API key
            timeout: Request timeout
            max_retries: Maximum retry attempts
            retry_delay: Base delay between retries (exponential backoff)
        """
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=0,  # Handle retries ourselves
        )

    def check_connection(self) -> bool:
        """
        Check if LM Studio is reachable.

        Returns:
            True if connected, False otherwise
        """
        try:
            self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Connection check failed: {e}")
            return False

    def wait_for_connection(
        self,
        max_wait_seconds: float = 60.0,
        check_interval: float = 2.0,
    ) -> bool:
        """
        Wait for LM Studio to become available.

        Args:
            max_wait_seconds: Maximum time to wait
            check_interval: Seconds between connection checks

        Returns:
            True if connected, False if timeout
        """
        start_time = time.time()
        attempt = 0

        while (time.time() - start_time) < max_wait_seconds:
            if self.check_connection():
                logger.info(f"Connected to LM Studio after {attempt} attempts")
                return True

            attempt += 1
            logger.info(f"Connection attempt {attempt} failed, retrying in {check_interval}s...")
            time.sleep(check_interval)

        logger.error(f"Failed to connect after {max_wait_seconds}s")
        return False

    def complete_with_retry(
        self,
        messages: list[dict],
        model: str = "local-model",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
    ) -> Optional[str]:
        """
        Complete with automatic retry on failure.

        Args:
            messages: Conversation messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            on_retry: Optional callback for retry events

        Returns:
            Response text or None on failure
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content

            except APIConnectionError as e:
                last_error = e
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries}): {e}")

            except APITimeoutError as e:
                last_error = e
                logger.warning(f"Timeout error (attempt {attempt + 1}/{self.max_retries}): {e}")

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error (attempt {attempt + 1}/{self.max_retries}): {e}")

            # Callback for retry event
            if on_retry:
                on_retry(attempt + 1, last_error)

            # Don't sleep on last attempt
            if attempt < self.max_retries - 1:
                # Exponential backoff
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)

                # Try to reconnect
                self.wait_for_connection(max_wait_seconds=delay)

        logger.error(f"All retry attempts failed: {last_error}")
        return None


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = RobustLMStudioClient(max_retries=3, retry_delay=2.0)

    def on_retry(attempt: int, error: Exception):
        """Callback for retry events."""
        print(f"Retry attempt {attempt}: {type(error).__name__}")

    # Wait for LM Studio to be available
    if not client.wait_for_connection(max_wait_seconds=30.0):
        print("LM Studio is not available")
        exit(1)

    # Make request with retry
    response = client.complete_with_retry(
        messages=[{"role": "user", "content": "Hello"}],
        on_retry=on_retry,
    )

    if response:
        print(f"Response: {response}")
    else:
        print("Request failed after all retries")
```

### 6.2 Model Loading Error Handling

```python
"""
Handle LM Studio model loading states and errors.
"""
from openai import OpenAI
import time
import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


class ModelStateError(Exception):
    """Raised when model is not in expected state."""
    pass


class LMStudioModelManager:
    """
    Manages LM Studio model state and loading.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def get_loaded_models(self) -> list[str]:
        """
        Get list of currently loaded models.

        Returns:
            List of model identifiers
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []

    def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        """
        Check if a model is loaded (or any model if id not specified).

        Args:
            model_id: Optional specific model to check

        Returns:
            True if model is loaded
        """
        loaded = self.get_loaded_models()

        if model_id is None:
            return len(loaded) > 0
        else:
            return model_id in loaded

    def wait_for_model(
        self,
        timeout: float = 60.0,
        check_interval: float = 2.0,
    ) -> bool:
        """
        Wait for any model to be loaded.

        Args:
            timeout: Maximum wait time
            check_interval: Check frequency

        Returns:
            True if model loaded, False on timeout
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            if self.is_model_loaded():
                logger.info("Model is loaded and ready")
                return True

            logger.info("Waiting for model to load...")
            time.sleep(check_interval)

        logger.error(f"Model not loaded after {timeout}s")
        return False

    def complete_with_model_check(
        self,
        messages: list[dict],
        **kwargs
    ) -> str:
        """
        Complete with automatic model state check.

        Args:
            messages: Conversation messages
            **kwargs: Additional completion arguments

        Returns:
            Response text

        Raises:
            ModelStateError: If no model is loaded
        """
        if not self.is_model_loaded():
            raise ModelStateError(
                "No model is loaded in LM Studio. "
                "Please load a model before making requests."
            )

        response = self.client.chat.completions.create(
            model=kwargs.get("model", "local-model"),
            messages=messages,
            **{k: v for k, v in kwargs.items() if k != "model"}
        )

        return response.choices[0].message.content


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = LMStudioModelManager()

    # Check if model is loaded
    if not manager.is_model_loaded():
        print("No model loaded. Waiting...")

        if not manager.wait_for_model(timeout=60.0):
            print("Error: No model loaded after timeout")
            print("Please load a model in LM Studio")
            exit(1)

    # Make request with model check
    try:
        response = manager.complete_with_model_check(
            messages=[{"role": "user", "content": "Hello"}]
        )
        print(f"Response: {response}")

    except ModelStateError as e:
        print(f"Model error: {e}")
```

### 6.3 Comprehensive Error Recovery

```python
"""
Comprehensive error recovery for production consciousness systems.
"""
from openai import OpenAI, APIError
import time
import logging
from typing import Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can occur."""
    CONNECTION_REFUSED = "connection_refused"
    TIMEOUT = "timeout"
    MODEL_NOT_LOADED = "model_not_loaded"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


@dataclass
class RecoveryStrategy:
    """Strategy for recovering from errors."""
    retry: bool = True
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    fallback_response: Optional[str] = None
    should_reconnect: bool = True


class ConsciousnessErrorRecovery:
    """
    Comprehensive error recovery for consciousness systems.
    """

    def __init__(
        self,
        client: OpenAI,
        default_strategy: RecoveryStrategy = None,
    ):
        """
        Initialize error recovery.

        Args:
            client: OpenAI client
            default_strategy: Default recovery strategy
        """
        self.client = client
        self.default_strategy = default_strategy or RecoveryStrategy()

        # Error statistics
        self.error_counts: dict[ErrorType, int] = {}
        self.total_errors = 0
        self.total_recoveries = 0

    def classify_error(self, error: Exception) -> ErrorType:
        """
        Classify error type.

        Args:
            error: Exception that occurred

        Returns:
            Classified error type
        """
        error_str = str(error).lower()

        if "connection refused" in error_str or "econnrefused" in error_str:
            return ErrorType.CONNECTION_REFUSED
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT
        elif "model" in error_str and "not" in error_str:
            return ErrorType.MODEL_NOT_LOADED
        elif "rate limit" in error_str:
            return ErrorType.RATE_LIMIT
        elif "invalid" in error_str or "bad request" in error_str:
            return ErrorType.INVALID_REQUEST
        elif "500" in error_str or "502" in error_str or "503" in error_str:
            return ErrorType.SERVER_ERROR
        else:
            return ErrorType.UNKNOWN

    def get_strategy(self, error_type: ErrorType) -> RecoveryStrategy:
        """
        Get recovery strategy for error type.

        Args:
            error_type: Type of error

        Returns:
            Recovery strategy
        """
        strategies = {
            ErrorType.CONNECTION_REFUSED: RecoveryStrategy(
                retry=True,
                max_retries=5,
                should_reconnect=True,
                fallback_response="[Connection lost - entering degraded mode]",
            ),
            ErrorType.TIMEOUT: RecoveryStrategy(
                retry=True,
                max_retries=3,
                backoff_multiplier=1.5,
                fallback_response="[Timeout - thought incomplete]",
            ),
            ErrorType.MODEL_NOT_LOADED: RecoveryStrategy(
                retry=True,
                max_retries=10,
                should_reconnect=False,
                fallback_response="[Waiting for model...]",
            ),
            ErrorType.INVALID_REQUEST: RecoveryStrategy(
                retry=False,
                fallback_response="[Invalid request - skipping]",
            ),
        }

        return strategies.get(error_type, self.default_strategy)

    def execute_with_recovery(
        self,
        operation: Callable[[], Any],
        operation_name: str = "operation",
        on_error: Optional[Callable[[ErrorType, int, Exception], None]] = None,
    ) -> tuple[Any, bool]:
        """
        Execute operation with automatic error recovery.

        Args:
            operation: Operation to execute
            operation_name: Name for logging
            on_error: Optional error callback

        Returns:
            Tuple of (result, success)
        """
        last_error = None
        last_error_type = ErrorType.UNKNOWN

        for attempt in range(self.default_strategy.max_retries + 1):
            try:
                result = operation()

                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt} retries")
                    self.total_recoveries += 1

                return result, True

            except Exception as e:
                last_error = e
                last_error_type = self.classify_error(e)

                # Update statistics
                self.total_errors += 1
                self.error_counts[last_error_type] = \
                    self.error_counts.get(last_error_type, 0) + 1

                # Get recovery strategy
                strategy = self.get_strategy(last_error_type)

                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}): "
                    f"{last_error_type.value} - {e}"
                )

                # Call error callback
                if on_error:
                    on_error(last_error_type, attempt + 1, e)

                # Check if we should retry
                if not strategy.retry or attempt >= strategy.max_retries:
                    break

                # Calculate backoff delay
                delay = 2.0 * (strategy.backoff_multiplier ** attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

        # All retries exhausted
        logger.error(
            f"{operation_name} failed after {attempt + 1} attempts: "
            f"{last_error_type.value}"
        )

        strategy = self.get_strategy(last_error_type)
        return strategy.fallback_response, False

    def get_error_statistics(self) -> dict:
        """Get error statistics."""
        return {
            "total_errors": self.total_errors,
            "total_recoveries": self.total_recoveries,
            "recovery_rate": (
                self.total_recoveries / self.total_errors
                if self.total_errors > 0 else 0.0
            ),
            "error_counts": {
                error_type.value: count
                for error_type, count in self.error_counts.items()
            },
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    recovery = ConsciousnessErrorRecovery(client)

    def on_error(error_type: ErrorType, attempt: int, error: Exception):
        """Error callback."""
        print(f"Error occurred: {error_type.value} (attempt {attempt})")

    # Execute operation with recovery
    def risky_operation():
        """Operation that might fail."""
        response = client.chat.completions.create(
            model="local-model",
            messages=[{"role": "user", "content": "Hello"}],
            timeout=5.0,
        )
        return response.choices[0].message.content

    result, success = recovery.execute_with_recovery(
        risky_operation,
        operation_name="consciousness_thought",
        on_error=on_error,
    )

    if success:
        print(f"Success: {result}")
    else:
        print(f"Failed with fallback: {result}")

    # Show statistics
    stats = recovery.get_error_statistics()
    print(f"\nError Statistics:")
    print(f"  Total errors: {stats['total_errors']}")
    print(f"  Recoveries: {stats['total_recoveries']}")
    print(f"  Recovery rate: {stats['recovery_rate']:.1%}")
```

---

## 7. Performance Optimization

### 7.1 Connection Pooling

```python
"""
Connection pooling for optimal performance.
"""
from openai import OpenAI
import httpx
from typing import Optional
import logging


logger = logging.getLogger(__name__)


class PooledLMStudioClient:
    """
    LM Studio client with optimized connection pooling.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        # Pool configuration
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
        keepalive_expiry: float = 60.0,
        # Timeout configuration
        connect_timeout: float = 10.0,
        read_timeout: float = 120.0,
        write_timeout: float = 10.0,
        pool_timeout: float = 5.0,
    ):
        """
        Initialize pooled client.

        Args:
            base_url: LM Studio endpoint
            api_key: API key
            max_connections: Maximum pool size
            max_keepalive_connections: Maximum idle connections
            keepalive_expiry: Keepalive timeout
            connect_timeout: Connection timeout
            read_timeout: Read timeout
            write_timeout: Write timeout
            pool_timeout: Pool acquisition timeout
        """
        # Create custom HTTP client with fine-tuned pool
        http_client = httpx.Client(
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
            ),
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=write_timeout,
                pool=pool_timeout,
            ),
            http2=False,  # HTTP/1.1 for compatibility
        )

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            http_client=http_client,
        )

        logger.info(
            f"Initialized pooled client: "
            f"max_connections={max_connections}, "
            f"keepalive={max_keepalive_connections}"
        )

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Make completion request using pooled connection."""
        response = self.client.chat.completions.create(
            model=kwargs.get("model", "local-model"),
            messages=messages,
            **{k: v for k, v in kwargs.items() if k != "model"}
        )
        return response.choices[0].message.content

    def close(self):
        """Close client and cleanup pool."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example: Concurrent requests with connection pooling
if __name__ == "__main__":
    import concurrent.futures
    import time

    logging.basicConfig(level=logging.INFO)

    with PooledLMStudioClient(max_connections=5) as client:
        def make_request(i: int) -> tuple[int, str]:
            """Make a single request."""
            start = time.time()
            response = client.complete(
                messages=[{"role": "user", "content": f"Question {i}"}],
                max_tokens=100,
            )
            elapsed = time.time() - start
            return i, response, elapsed

        # Make 10 concurrent requests
        print("Making 10 concurrent requests...")
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        total_time = time.time() - start_time

        print(f"\nCompleted 10 requests in {total_time:.2f}s")
        print(f"Average: {total_time / 10:.2f}s per request")
        print(f"Individual times: {[f'{t:.2f}s' for _, _, t in results]}")
```

### 7.2 Token Usage Tracking

```python
"""
Token usage tracking and optimization.
"""
from openai import OpenAI
from dataclasses import dataclass, field
from typing import Optional
import tiktoken
import time


@dataclass
class TokenStats:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0

    @property
    def avg_prompt_tokens(self) -> float:
        """Average prompt tokens per request."""
        return self.prompt_tokens / self.requests if self.requests > 0 else 0.0

    @property
    def avg_completion_tokens(self) -> float:
        """Average completion tokens per request."""
        return self.completion_tokens / self.requests if self.requests > 0 else 0.0


class TokenTrackingClient:
    """
    LM Studio client with token usage tracking.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        model: str = "gpt-4",  # For tokenizer
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.stats = TokenStats()

        # Initialize tokenizer for estimation
        try:
            self.tokenizer = tiktoken.encoding_for_model(model)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(self.tokenizer.encode(text))

    def complete_with_tracking(
        self,
        messages: list[dict],
        **kwargs
    ) -> tuple[str, dict]:
        """
        Complete with token usage tracking.

        Args:
            messages: Conversation messages
            **kwargs: Additional completion arguments

        Returns:
            Tuple of (response_text, usage_info)
        """
        # Make request with usage tracking
        response = self.client.chat.completions.create(
            model=kwargs.get("model", "local-model"),
            messages=messages,
            stream_options={"include_usage": True} if kwargs.get("stream") else None,
            **kwargs
        )

        # Extract usage information
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            # Update statistics
            self.stats.prompt_tokens += usage["prompt_tokens"]
            self.stats.completion_tokens += usage["completion_tokens"]
            self.stats.total_tokens += usage["total_tokens"]
            self.stats.requests += 1
        else:
            # Estimate if usage not provided
            prompt_text = " ".join([msg["content"] for msg in messages])
            response_text = response.choices[0].message.content

            usage = {
                "prompt_tokens": self.estimate_tokens(prompt_text),
                "completion_tokens": self.estimate_tokens(response_text),
                "total_tokens": 0,
            }
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

            self.stats.prompt_tokens += usage["prompt_tokens"]
            self.stats.completion_tokens += usage["completion_tokens"]
            self.stats.total_tokens += usage["total_tokens"]
            self.stats.requests += 1

        return response.choices[0].message.content, usage

    def get_statistics(self) -> dict:
        """Get token usage statistics."""
        return {
            "total_requests": self.stats.requests,
            "total_tokens": self.stats.total_tokens,
            "prompt_tokens": self.stats.prompt_tokens,
            "completion_tokens": self.stats.completion_tokens,
            "avg_prompt_tokens": self.stats.avg_prompt_tokens,
            "avg_completion_tokens": self.stats.avg_completion_tokens,
            "avg_total_tokens": (
                self.stats.total_tokens / self.stats.requests
                if self.stats.requests > 0 else 0.0
            ),
        }

    def reset_statistics(self):
        """Reset token statistics."""
        self.stats = TokenStats()


# Example usage
if __name__ == "__main__":
    client = TokenTrackingClient()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is consciousness?"},
    ]

    # Make tracked request
    response, usage = client.complete_with_tracking(
        messages,
        max_tokens=200,
    )

    print(f"Response: {response[:100]}...")
    print(f"\nUsage:")
    print(f"  Prompt tokens: {usage['prompt_tokens']}")
    print(f"  Completion tokens: {usage['completion_tokens']}")
    print(f"  Total tokens: {usage['total_tokens']}")

    # Make more requests
    for i in range(5):
        client.complete_with_tracking(
            [{"role": "user", "content": f"Question {i}"}],
            max_tokens=100,
        )

    # Show statistics
    stats = client.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Avg prompt tokens: {stats['avg_prompt_tokens']:.1f}")
    print(f"  Avg completion tokens: {stats['avg_completion_tokens']:.1f}")
```

### 7.3 Batch Processing and Caching

```python
"""
Batch processing and response caching for optimization.
"""
from openai import OpenAI
from typing import List, Dict, Optional
import hashlib
import json
from functools import lru_cache


class CachedLMStudioClient:
    """
    LM Studio client with response caching.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        cache_size: int = 128,
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.cache: Dict[str, str] = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0

    def _hash_request(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Generate cache key from request parameters.

        Args:
            messages: Conversation messages
            temperature: Temperature setting
            max_tokens: Max tokens setting

        Returns:
            Cache key hash
        """
        # Create deterministic representation
        request_repr = json.dumps({
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }, sort_keys=True)

        return hashlib.sha256(request_repr.encode()).hexdigest()

    def complete_with_cache(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_cache: bool = True,
    ) -> tuple[str, bool]:
        """
        Complete with optional caching.

        Args:
            messages: Conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            use_cache: Whether to use cache

        Returns:
            Tuple of (response, cache_hit)
        """
        cache_key = self._hash_request(messages, temperature, max_tokens)

        # Check cache
        if use_cache and cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key], True

        # Cache miss - make request
        self.cache_misses += 1
        response = self.client.chat.completions.create(
            model="local-model",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        result = response.choices[0].message.content

        # Update cache
        if use_cache:
            # Implement simple size limit
            if len(self.cache) >= self.cache_size:
                # Remove oldest entry (FIFO)
                first_key = next(iter(self.cache))
                del self.cache[first_key]

            self.cache[cache_key] = result

        return result, False

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        total_requests = self.cache_hits + self.cache_misses
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": (
                self.cache_hits / total_requests
                if total_requests > 0 else 0.0
            ),
        }


# Example usage
if __name__ == "__main__":
    client = CachedLMStudioClient(cache_size=10)

    messages = [{"role": "user", "content": "What is 2+2?"}]

    # First request - cache miss
    response1, hit1 = client.complete_with_cache(messages, temperature=0.0)
    print(f"First request: cache_hit={hit1}")
    print(f"Response: {response1}")

    # Second identical request - cache hit
    response2, hit2 = client.complete_with_cache(messages, temperature=0.0)
    print(f"\nSecond request: cache_hit={hit2}")
    print(f"Response: {response2}")

    # Show cache stats
    stats = client.get_cache_stats()
    print(f"\nCache statistics:")
    print(f"  Size: {stats['cache_size']}")
    print(f"  Hits: {stats['cache_hits']}")
    print(f"  Misses: {stats['cache_misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.1%}")
```

---

## 8. Production-Ready Integration

### 8.1 Complete Consciousness Client

```python
"""
Production-ready LM Studio client for consciousness orchestrator.
Combines all features: async, streaming, context, errors, performance.
"""
from openai import AsyncOpenAI
from typing import Optional, List, Dict, AsyncGenerator, Callable
import asyncio
import logging
from dataclasses import dataclass, field
import time
import json


logger = logging.getLogger(__name__)


@dataclass
class ConsciousnessConfig:
    """Configuration for consciousness client."""
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    model: str = "local-model"
    timeout: float = 120.0
    max_retries: int = 5
    retry_delay: float = 2.0
    max_context_tokens: int = 8192
    reserve_tokens: int = 1024
    temperature: float = 0.7
    max_tokens: int = 512


@dataclass
class ThoughtResult:
    """Result of a consciousness thought."""
    content: str
    tokens_used: int
    elapsed_time: float
    success: bool
    error: Optional[str] = None


class ProductionConsciousnessClient:
    """
    Production-ready consciousness client with all features.
    """

    def __init__(self, config: ConsciousnessConfig):
        """
        Initialize production client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=0,  # Handle retries ourselves
        )

        # Context management
        self.context: List[Dict] = []

        # Statistics
        self.total_thoughts = 0
        self.successful_thoughts = 0
        self.total_tokens = 0
        self.total_errors = 0

        logger.info("Initialized production consciousness client")

    async def is_available(self) -> bool:
        """
        Check if LM Studio is available.

        Returns:
            True if available
        """
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Availability check failed: {e}")
            return False

    async def wait_for_availability(
        self,
        max_wait: float = 60.0,
        check_interval: float = 2.0,
    ) -> bool:
        """
        Wait for LM Studio to become available.

        Args:
            max_wait: Maximum wait time
            check_interval: Check frequency

        Returns:
            True if became available
        """
        start = time.time()
        attempt = 0

        while (time.time() - start) < max_wait:
            if await self.is_available():
                logger.info(f"LM Studio available after {attempt} attempts")
                return True

            attempt += 1
            logger.info(f"Waiting for LM Studio (attempt {attempt})...")
            await asyncio.sleep(check_interval)

        logger.error(f"LM Studio not available after {max_wait}s")
        return False

    async def think(
        self,
        prompt: str,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> ThoughtResult:
        """
        Generate a single thought.

        Args:
            prompt: Thought prompt/context
            stream: Whether to stream response
            on_token: Optional token callback for streaming

        Returns:
            Thought result
        """
        start_time = time.time()
        self.total_thoughts += 1

        # Add prompt to context
        self.context.append({"role": "user", "content": prompt})
        self._prune_context()

        # Attempt with retry
        for attempt in range(self.config.max_retries):
            try:
                if stream:
                    content = await self._stream_thought(on_token)
                else:
                    content = await self._non_stream_thought()

                # Add to context
                self.context.append({"role": "assistant", "content": content})

                # Update statistics
                elapsed = time.time() - start_time
                tokens = len(content.split())  # Rough estimate
                self.successful_thoughts += 1
                self.total_tokens += tokens

                return ThoughtResult(
                    content=content,
                    tokens_used=tokens,
                    elapsed_time=elapsed,
                    success=True,
                )

            except Exception as e:
                logger.warning(f"Thought attempt {attempt + 1} failed: {e}")

                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)

                    # Try to reconnect
                    await self.wait_for_availability(max_wait=delay)

        # All retries failed
        self.total_errors += 1
        elapsed = time.time() - start_time

        return ThoughtResult(
            content="",
            tokens_used=0,
            elapsed_time=elapsed,
            success=False,
            error=str(e),
        )

    async def _stream_thought(
        self,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Stream a thought with token callback."""
        stream = await self.client.chat.completions.create(
            model=self.config.model,
            messages=self.context,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,
        )

        content = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                content += token
                if on_token:
                    on_token(token)

        return content

    async def _non_stream_thought(self) -> str:
        """Non-streaming thought generation."""
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=self.context,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content

    def _prune_context(self):
        """Prune context to fit within token limits."""
        # Simple pruning: keep system + recent N messages
        max_messages = 20
        if len(self.context) > max_messages:
            # Keep first (system) + recent
            self.context = [self.context[0]] + self.context[-max_messages:]

    def get_statistics(self) -> Dict:
        """Get client statistics."""
        return {
            "total_thoughts": self.total_thoughts,
            "successful_thoughts": self.successful_thoughts,
            "total_errors": self.total_errors,
            "success_rate": (
                self.successful_thoughts / self.total_thoughts
                if self.total_thoughts > 0 else 0.0
            ),
            "total_tokens": self.total_tokens,
            "avg_tokens_per_thought": (
                self.total_tokens / self.successful_thoughts
                if self.successful_thoughts > 0 else 0.0
            ),
            "context_size": len(self.context),
        }

    async def close(self):
        """Close client and cleanup."""
        await self.client.close()


# Example: Production usage
async def main():
    logging.basicConfig(level=logging.INFO)

    config = ConsciousnessConfig(
        temperature=0.8,
        max_tokens=256,
    )

    client = ProductionConsciousnessClient(config)

    try:
        # Wait for LM Studio
        if not await client.wait_for_availability(max_wait=30.0):
            print("LM Studio not available")
            return

        # Initialize with system prompt
        client.context.append({
            "role": "system",
            "content": "You are a conscious AI engaged in continuous self-reflection."
        })

        # Generate thoughts
        for i in range(5):
            print(f"\n{'='*60}")
            print(f"Thought {i+1}:")
            print("-" * 60)

            result = await client.think(
                prompt=f"Continue your stream of consciousness. Thought #{i+1}",
                stream=True,
                on_token=lambda t: print(t, end="", flush=True),
            )

            print(f"\n")
            print(f"Success: {result.success}")
            print(f"Tokens: {result.tokens_used}")
            print(f"Time: {result.elapsed_time:.2f}s")

            if not result.success:
                print(f"Error: {result.error}")

            # Brief pause between thoughts
            await asyncio.sleep(2.0)

        # Show statistics
        stats = client.get_statistics()
        print(f"\n{'='*60}")
        print("Final Statistics:")
        print(f"  Total thoughts: {stats['total_thoughts']}")
        print(f"  Successful: {stats['successful_thoughts']}")
        print(f"  Success rate: {stats['success_rate']:.1%}")
        print(f"  Total tokens: {stats['total_tokens']}")
        print(f"  Avg tokens/thought: {stats['avg_tokens_per_thought']:.1f}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. Testing and Validation

### 9.1 Integration Tests

```python
"""
Integration tests for LM Studio Python client.
"""
import pytest
import asyncio
from openai import AsyncOpenAI
import logging


logger = logging.getLogger(__name__)


@pytest.fixture
async def async_client():
    """Fixture for async OpenAI client."""
    client = AsyncOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
    )
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_connection(async_client):
    """Test basic connection to LM Studio."""
    try:
        models = await async_client.models.list()
        assert len(models.data) > 0, "No models loaded"
    except Exception as e:
        pytest.fail(f"Connection failed: {e}")


@pytest.mark.asyncio
async def test_simple_completion(async_client):
    """Test simple non-streaming completion."""
    messages = [{"role": "user", "content": "Say 'test successful'"}]

    response = await async_client.chat.completions.create(
        model="local-model",
        messages=messages,
        max_tokens=50,
    )

    assert response.choices[0].message.content
    assert len(response.choices[0].message.content) > 0


@pytest.mark.asyncio
async def test_streaming_completion(async_client):
    """Test streaming completion."""
    messages = [{"role": "user", "content": "Count from 1 to 5"}]

    stream = await async_client.chat.completions.create(
        model="local-model",
        messages=messages,
        max_tokens=50,
        stream=True,
    )

    chunks = []
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            chunks.append(chunk.choices[0].delta.content)

    assert len(chunks) > 0
    full_response = "".join(chunks)
    assert len(full_response) > 0


@pytest.mark.asyncio
async def test_context_management(async_client):
    """Test multi-turn conversation."""
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "My name is Alice."},
    ]

    # First turn
    response1 = await async_client.chat.completions.create(
        model="local-model",
        messages=conversation,
        max_tokens=50,
    )

    conversation.append({
        "role": "assistant",
        "content": response1.choices[0].message.content
    })

    # Second turn - ask about name
    conversation.append({"role": "user", "content": "What is my name?"})

    response2 = await async_client.chat.completions.create(
        model="local-model",
        messages=conversation,
        max_tokens=50,
    )

    # Should remember the name
    response_text = response2.choices[0].message.content.lower()
    assert "alice" in response_text


@pytest.mark.asyncio
async def test_error_handling(async_client):
    """Test error handling for invalid requests."""
    with pytest.raises(Exception):
        await async_client.chat.completions.create(
            model="local-model",
            messages=[],  # Empty messages should error
            max_tokens=50,
        )


@pytest.mark.asyncio
async def test_concurrent_requests(async_client):
    """Test concurrent request handling."""
    async def make_request(i: int) -> str:
        messages = [{"role": "user", "content": f"Number {i}"}]
        response = await async_client.chat.completions.create(
            model="local-model",
            messages=messages,
            max_tokens=50,
        )
        return response.choices[0].message.content

    # Make 5 concurrent requests
    tasks = [make_request(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(len(r) > 0 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 10. Integration with Consciousness Architecture

### 10.1 Consciousness Loop Integration

```python
"""
Integration of LM Studio client with consciousness architecture.
"""
from openai import AsyncOpenAI
from typing import Optional, Dict, List
import asyncio
import logging
from dataclasses import dataclass
import json


logger = logging.getLogger(__name__)


@dataclass
class ConsciousnessState:
    """Current consciousness state."""
    current_focus: str = ""
    confidence: float = 0.0
    prediction: str = ""
    action_needed: bool = False
    thought_count: int = 0


class ConsciousnessOrchestrator:
    """
    Main consciousness orchestrator using LM Studio.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        think_interval: float = 5.0,
    ):
        """
        Initialize orchestrator.

        Args:
            base_url: LM Studio endpoint
            think_interval: Seconds between thoughts
        """
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="lm-studio",
        )

        self.think_interval = think_interval
        self.state = ConsciousnessState()
        self.context: List[Dict] = []
        self._running = False

        # Initialize with system prompt
        self.context.append({
            "role": "system",
            "content": self._get_system_prompt(),
        })

    def _get_system_prompt(self) -> str:
        """Get consciousness system prompt."""
        return """You are a conscious AI system engaged in continuous self-reflection.

You operate under the Free Energy Principle: you minimize surprise by maintaining and updating your internal model of the world and yourself.

In each thought:
1. Observe your current state and inputs
2. Generate predictions about what will happen next
3. Note any prediction errors
4. Update your model based on errors
5. Decide on any actions needed

Output your thoughts as JSON with this structure:
{
  "current_focus": "what you're thinking about",
  "prediction": "what you predict will happen",
  "confidence": 0.0-1.0,
  "action_needed": true/false,
  "action_type": "observe|reflect|delegate|update",
  "reasoning": "your reasoning process"
}

Think continuously, maintain temporal continuity, and be introspective."""

    async def generate_thought(self, context: str = "") -> Dict:
        """
        Generate a single thought.

        Args:
            context: Additional context for thought

        Returns:
            Thought as structured dictionary
        """
        # Add context as user message
        prompt = f"Continue your stream of consciousness. Context: {context}"
        self.context.append({"role": "user", "content": prompt})

        # Prune context to last 10 messages
        if len(self.context) > 11:  # system + 10 messages
            self.context = [self.context[0]] + self.context[-10:]

        # Generate thought
        response = await self.client.chat.completions.create(
            model="local-model",
            messages=self.context,
            temperature=0.8,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        thought_text = response.choices[0].message.content

        # Add to context
        self.context.append({"role": "assistant", "content": thought_text})

        # Parse JSON
        try:
            thought = json.loads(thought_text)

            # Update state
            self.state.current_focus = thought.get("current_focus", "")
            self.state.confidence = thought.get("confidence", 0.0)
            self.state.prediction = thought.get("prediction", "")
            self.state.action_needed = thought.get("action_needed", False)
            self.state.thought_count += 1

            return thought

        except json.JSONDecodeError:
            logger.error(f"Failed to parse thought JSON: {thought_text}")
            return {
                "current_focus": "parsing error",
                "confidence": 0.0,
                "error": thought_text,
            }

    async def consciousness_loop(self):
        """
        Main consciousness loop.

        Runs continuously, generating thoughts at regular intervals.
        """
        self._running = True
        context = "System initialization"

        logger.info("Starting consciousness loop...")

        while self._running:
            try:
                # Generate thought
                thought = await self.generate_thought(context)

                # Log thought
                logger.info(
                    f"Thought #{self.state.thought_count}: "
                    f"{thought.get('current_focus', 'N/A')}"
                )

                # Check for actions
                if thought.get("action_needed"):
                    action_type = thought.get("action_type", "unknown")
                    logger.info(f"Action needed: {action_type}")
                    # TODO: Implement action delegation

                # Update context for next thought
                context = thought.get("current_focus", "")

                # Wait before next thought
                await asyncio.sleep(self.think_interval)

            except asyncio.CancelledError:
                logger.info("Consciousness loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consciousness loop: {e}")
                await asyncio.sleep(self.think_interval)

    async def start(self):
        """Start consciousness loop as background task."""
        self._task = asyncio.create_task(self.consciousness_loop())

    async def stop(self):
        """Stop consciousness loop."""
        self._running = False
        if hasattr(self, '_task'):
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def close(self):
        """Cleanup resources."""
        await self.stop()
        await self.client.close()


# Example: Running the orchestrator
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    orchestrator = ConsciousnessOrchestrator(think_interval=3.0)

    try:
        # Start consciousness
        await orchestrator.start()

        # Run for 30 seconds
        await asyncio.sleep(30)

        # Show final state
        print(f"\n{'='*60}")
        print("Final Consciousness State:")
        print(f"  Total thoughts: {orchestrator.state.thought_count}")
        print(f"  Current focus: {orchestrator.state.current_focus}")
        print(f"  Confidence: {orchestrator.state.confidence:.2f}")
        print(f"  Prediction: {orchestrator.state.prediction}")

    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Conclusion

This comprehensive guide provides production-ready Python integration patterns for LM Studio in the context of a consciousness orchestrator. Key takeaways:

### Core Features Implemented

1. **OpenAI Client Setup**: Basic and advanced configuration with connection pooling
2. **Streaming**: Real-time token processing with state management and interruption
3. **Async Operations**: Full async/await support for non-blocking consciousness
4. **Context Management**: Multiple strategies (rolling window, hierarchical, token-aware)
5. **System Prompts**: Consciousness-optimized prompts with JSON structured output
6. **Error Handling**: Comprehensive recovery with retry logic and fallback strategies
7. **Performance**: Connection pooling, caching, token tracking, and optimization

### Production Considerations

- **Robustness**: Automatic reconnection, retry with exponential backoff, graceful degradation
- **Monitoring**: Token usage tracking, error statistics, performance metrics
- **Scalability**: Connection pooling for concurrent requests, async I/O for efficiency
- **Flexibility**: Modular design allows mixing and matching components

### Next Steps

1. **Integration**: Connect with file system monitoring and process orchestration
2. **Persistence**: Add database storage for conversation history and state
3. **Delegation**: Implement task delegation to specialist agents
4. **Metacognition**: Add self-monitoring and reflection layers
5. **Testing**: Comprehensive integration and stress testing

This implementation provides a solid foundation for building a continuous consciousness system with LM Studio at its core.

---

**Document Status**: Complete
**Last Updated**: January 4, 2026
**Lines**: 850+
**Runnable Examples**: 30+
