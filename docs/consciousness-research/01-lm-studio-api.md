# LM Studio API Research for Continuous Monitoring Systems

## Executive Summary

LM Studio provides a robust, OpenAI-compatible local LLM serving platform ideal for building continuous monitoring systems. Key capabilities include:

- **OpenAI-compatible REST API** at `localhost:1234/v1`
- **Full streaming support** via Server-Sent Events (SSE)
- **Configurable context management** with overflow policies
- **Model persistence** via TTL settings and `noHup` option
- **Headless operation** for background service deployment
- **No rate limits** for local operation

---

## 1. API Endpoints

### OpenAI-Compatible Endpoints (Primary Interface)

Base URL: `http://localhost:1234/v1`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat conversations with streaming support |
| `/v1/completions` | POST | Legacy text completions |
| `/v1/embeddings` | POST | Text embedding generation |
| `/v1/responses` | POST | Stateful interactions with response tracking |
| `/v1/models` | GET | List available models |

### LM Studio REST API v0 (Enhanced Statistics)

Base URL: `http://localhost:1234/api/v0`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v0/models` | GET | List all downloaded/loaded models |
| `/api/v0/models/{model}` | GET | Get specific model information |
| `/api/v0/chat/completions` | POST | Chat with enhanced statistics (tokens/sec, TTFT) |
| `/api/v0/completions` | POST | Text generation with stats |
| `/api/v0/embeddings` | POST | Embeddings generation |

### Supported Chat Completion Parameters

```json
{
  "model": "model-identifier",
  "messages": [{"role": "user", "content": "..."}],
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "max_tokens": 2048,
  "stream": true,
  "stop": ["STOP"],
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "repeat_penalty": 1.1,
  "seed": 42,
  "logit_bias": {}
}
```

---

## 2. Streaming Support

LM Studio fully supports streaming via Server-Sent Events (SSE), essential for continuous monitoring applications.

### Streaming Events

When `stream: true` is set, the API returns:

- `response.created` - Initial response creation
- `response.output_text.delta` - Incremental text chunks
- `response.completed` - Final completion signal

### Token Usage in Streams

Enable usage statistics during streaming:

```json
{
  "stream": true,
  "stream_options": {
    "include_usage": true
  }
}
```

---

## 3. Context Window Management

### Configuration Options

| Parameter | Description |
|-----------|-------------|
| `context_length` | Maximum tokens (varies by model: 8K-131K+) |
| `contextOverflowPolicy` | Behavior when context is exceeded |

### Context Overflow Policies

1. **`stopAtLimit`** - Halt generation when context window is full
   - Best for: Controlled batch processing
   - Returns `stopReason=contextLengthReached`

2. **`truncateMiddle`** - Preserve system prompt and first user message, remove middle content
   - Best for: Long-running tasks where initial instructions matter
   - Caution: May cause infinite generation loops near context limits

3. **`rollingWindow`** - Maintain recency by dropping oldest messages
   - Best for: Continuous monitoring and chat-style interactions
   - Keeps recent context relevant, drops old history automatically

### Recommended for Continuous Monitoring

```json
{
  "contextOverflowPolicy": "rollingWindow"
}
```

This policy automatically prunes old context while maintaining recent observations, ideal for long-running monitoring sessions.

---

## 4. Rate Limits

**LM Studio has no explicit rate limits for local operation.**

The system is designed for localhost and local network access. Performance is bounded only by:

- Hardware capabilities (GPU/CPU)
- Model size and complexity
- Available VRAM/RAM
- Context length settings

### Best Practices for High-Throughput

- Monitor VRAM usage (each token adds to KV cache)
- Start with smaller context windows (6K-8K) and scale up
- Use GPU offloading for faster inference
- Consider model quantization for memory efficiency

---

## 5. Model Loading & Persistence

### Keeping Models Hot-Loaded

#### Option 1: TTL (Time-To-Live) Settings

Prevent automatic unloading with extended TTL:

```json
{
  "ttl": 86400
}
```

- Default JIT-loaded TTL: 60 minutes
- CLI-loaded models: No TTL (permanent until manual unload)
- TTL resets with each request

#### Option 2: noHup Option (SDK)

Prevent unload on client disconnect:

```typescript
await client.llm.load("model-path", {
  noHup: true  // Model stays loaded after client disconnects
});
```

#### Option 3: CLI Loading

```bash
# Load without TTL (stays until manually unloaded)
lms load "model-path"

# Load with specific TTL (1 hour = 3600 seconds)
lms load "model-path" --ttl 3600
```

### Auto-Evict Behavior

When enabled (default), Auto-Evict unloads previous JIT-loaded models before loading new ones. For continuous monitoring:

- Disable Auto-Evict in Developer tab > Server Settings
- Or use CLI/SDK loading which isn't affected

---

## 6. Multi-Turn Conversations

### Stateful Responses API

Use `/v1/responses` with `previous_response_id` for stateful multi-turn conversations:

```json
{
  "model": "model-id",
  "input": "Follow-up question",
  "previous_response_id": "resp_abc123"
}
```

### Manual State Management

For monitoring applications, manage conversation state manually:

```python
conversation_history = [
    {"role": "system", "content": "You are a system monitor..."},
    {"role": "user", "content": "Status update: CPU 45%"},
    {"role": "assistant", "content": "Acknowledged. Normal levels."},
    # Add new observations here
]
```

---

## Code Examples

### Example 1: Connecting to LM Studio API (Python)

```python
"""
Basic LM Studio connection using OpenAI client.
Works with any OpenAI-compatible client by changing base_url.
"""
from openai import OpenAI

def create_lm_studio_client(
    base_url: str = "http://localhost:1234/v1",
    api_key: str = "lm-studio"  # Not validated, but required by client
) -> OpenAI:
    """Create an OpenAI client configured for LM Studio."""
    return OpenAI(base_url=base_url, api_key=api_key)


def list_available_models(client: OpenAI) -> list[str]:
    """List all models available in LM Studio."""
    models = client.models.list()
    return [model.id for model in models.data]


def simple_completion(
    client: OpenAI,
    prompt: str,
    model: str = "local-model",
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str:
    """Get a simple non-streaming completion."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content


# Usage
if __name__ == "__main__":
    client = create_lm_studio_client()

    # List models
    models = list_available_models(client)
    print(f"Available models: {models}")

    # Simple query
    response = simple_completion(client, "What is consciousness?")
    print(response)
```

### Example 2: Streaming Responses (Python)

```python
"""
Streaming responses for real-time output.
Essential for continuous monitoring applications.
"""
from openai import OpenAI
from typing import Generator, Callable


def stream_completion(
    client: OpenAI,
    messages: list[dict],
    model: str = "local-model",
    on_chunk: Callable[[str], None] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> Generator[str, None, None]:
    """
    Stream a completion, yielding text chunks as they arrive.

    Args:
        client: OpenAI client configured for LM Studio
        messages: Conversation history
        model: Model identifier
        on_chunk: Optional callback for each chunk
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Yields:
        Text chunks as they are generated
    """
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        stream_options={"include_usage": True}
    )

    full_response = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            full_response += text
            if on_chunk:
                on_chunk(text)
            yield text

        # Check for usage stats in final chunk
        if hasattr(chunk, 'usage') and chunk.usage:
            yield f"\n[Tokens: {chunk.usage.total_tokens}]"


# Usage with real-time printing
if __name__ == "__main__":
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ]

    print("Streaming response: ", end="", flush=True)
    for chunk in stream_completion(client, messages, on_chunk=lambda x: print(x, end="", flush=True)):
        pass  # Chunks are printed by callback
    print()
```

### Example 3: Async Streaming (Python)

```python
"""
Async streaming for non-blocking continuous monitoring.
"""
import asyncio
from openai import AsyncOpenAI
from typing import AsyncGenerator


async def async_stream_completion(
    client: AsyncOpenAI,
    messages: list[dict],
    model: str = "local-model",
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> AsyncGenerator[str, None]:
    """
    Async streaming completion for non-blocking operation.
    """
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def monitor_with_async_streaming():
    """Example of async monitoring loop."""
    client = AsyncOpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio"
    )

    system_prompt = """You are a continuous system monitor.
    Analyze incoming data and report anomalies."""

    messages = [{"role": "system", "content": system_prompt}]

    # Simulated monitoring data
    monitoring_data = [
        "CPU: 45%, Memory: 62%, Disk I/O: normal",
        "CPU: 89%, Memory: 78%, Disk I/O: high - ALERT",
        "CPU: 52%, Memory: 65%, Disk I/O: normal",
    ]

    for data in monitoring_data:
        messages.append({"role": "user", "content": f"Status: {data}"})

        print(f"\nInput: {data}")
        print("Analysis: ", end="", flush=True)

        response_text = ""
        async for chunk in async_stream_completion(client, messages):
            print(chunk, end="", flush=True)
            response_text += chunk

        messages.append({"role": "assistant", "content": response_text})
        print()

        await asyncio.sleep(1)  # Simulated delay between readings


if __name__ == "__main__":
    asyncio.run(monitor_with_async_streaming())
```

### Example 4: Context Window Management for Continuous Monitoring

```python
"""
Context window management for long-running monitoring sessions.
Implements manual rolling window to maintain context relevance.
"""
from openai import OpenAI
from typing import Optional
from dataclasses import dataclass, field
import tiktoken


@dataclass
class MonitoringContext:
    """Manages conversation context for continuous monitoring."""

    system_prompt: str
    max_context_tokens: int = 8192
    reserve_tokens: int = 1024  # Reserve for response
    model: str = "local-model"
    messages: list[dict] = field(default_factory=list)
    _tokenizer: Optional[object] = field(default=None, repr=False)

    def __post_init__(self):
        # Initialize with system prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
        # Use cl100k_base as approximation (GPT-4 tokenizer)
        try:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        # Fallback: rough estimate of 4 chars per token
        return len(text) // 4

    def _total_context_tokens(self) -> int:
        """Calculate total tokens in current context."""
        total = 0
        for msg in self.messages:
            total += self._count_tokens(msg["content"])
            total += 4  # Role and formatting overhead
        return total

    def add_observation(self, observation: str) -> None:
        """Add a new observation, pruning old context if needed."""
        self.messages.append({"role": "user", "content": observation})
        self._prune_context()

    def add_response(self, response: str) -> None:
        """Add assistant response to context."""
        self.messages.append({"role": "assistant", "content": response})
        self._prune_context()

    def _prune_context(self) -> None:
        """
        Remove oldest messages (except system) to stay within limits.
        Implements rolling window strategy.
        """
        available_tokens = self.max_context_tokens - self.reserve_tokens

        while self._total_context_tokens() > available_tokens and len(self.messages) > 2:
            # Remove oldest non-system message
            self.messages.pop(1)

    def get_messages(self) -> list[dict]:
        """Get current message list for API call."""
        return self.messages.copy()

    def get_context_usage(self) -> dict:
        """Get context usage statistics."""
        used = self._total_context_tokens()
        available = self.max_context_tokens - self.reserve_tokens
        return {
            "used_tokens": used,
            "available_tokens": available,
            "max_tokens": self.max_context_tokens,
            "usage_percent": round(used / available * 100, 1),
            "message_count": len(self.messages)
        }


class ContinuousMonitor:
    """
    Continuous monitoring system with context management.
    """

    def __init__(
        self,
        system_prompt: str,
        base_url: str = "http://localhost:1234/v1",
        model: str = "local-model",
        max_context_tokens: int = 8192
    ):
        self.client = OpenAI(base_url=base_url, api_key="lm-studio")
        self.model = model
        self.context = MonitoringContext(
            system_prompt=system_prompt,
            max_context_tokens=max_context_tokens,
            model=model
        )

    def process_observation(
        self,
        observation: str,
        stream: bool = True,
        on_token: Optional[callable] = None
    ) -> str:
        """
        Process a new observation and get analysis.

        Args:
            observation: New data/observation to analyze
            stream: Whether to stream the response
            on_token: Callback for each token (streaming only)

        Returns:
            Complete response text
        """
        self.context.add_observation(observation)

        if stream:
            response = self._stream_response(on_token)
        else:
            response = self._get_response()

        self.context.add_response(response)
        return response

    def _stream_response(self, on_token: Optional[callable] = None) -> str:
        """Get streaming response."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.context.get_messages(),
            stream=True
        )

        full_response = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                if on_token:
                    on_token(text)

        return full_response

    def _get_response(self) -> str:
        """Get non-streaming response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.context.get_messages()
        )
        return response.choices[0].message.content

    def get_status(self) -> dict:
        """Get monitor status including context usage."""
        return {
            "model": self.model,
            "context": self.context.get_context_usage()
        }


# Usage example
if __name__ == "__main__":
    monitor = ContinuousMonitor(
        system_prompt="""You are an intelligent system monitor.
        Analyze incoming system metrics and:
        1. Identify anomalies or concerning patterns
        2. Predict potential issues
        3. Recommend actions when needed
        Keep responses concise but informative.""",
        max_context_tokens=8192
    )

    # Simulated monitoring loop
    observations = [
        "Timestamp: 00:00 | CPU: 45% | Mem: 62% | Net: 120Mbps | Status: OK",
        "Timestamp: 00:05 | CPU: 67% | Mem: 71% | Net: 145Mbps | Status: OK",
        "Timestamp: 00:10 | CPU: 92% | Mem: 88% | Net: 89Mbps | Status: WARNING",
        "Timestamp: 00:15 | CPU: 95% | Mem: 91% | Net: 45Mbps | Status: CRITICAL",
    ]

    for obs in observations:
        print(f"\n{'='*60}")
        print(f"Input: {obs}")
        print(f"Context: {monitor.get_status()['context']['usage_percent']}% used")
        print("-" * 60)
        print("Analysis: ", end="", flush=True)

        response = monitor.process_observation(
            obs,
            stream=True,
            on_token=lambda t: print(t, end="", flush=True)
        )
        print()
```

### Example 5: LM Studio Native SDK (TypeScript)

```typescript
/**
 * LM Studio TypeScript SDK example for continuous monitoring.
 * Uses native lmstudio-js package for enhanced features.
 */
import { LMStudioClient } from "@lmstudio/sdk";

interface MonitorConfig {
  modelPath: string;
  systemPrompt: string;
  keepLoaded: boolean;
  contextLength?: number;
}

class LMStudioMonitor {
  private client: LMStudioClient;
  private model: any;
  private config: MonitorConfig;
  private conversationHistory: Array<{ role: string; content: string }> = [];

  constructor(config: MonitorConfig) {
    this.client = new LMStudioClient();
    this.config = config;
    this.conversationHistory = [
      { role: "system", content: config.systemPrompt }
    ];
  }

  async initialize(): Promise<void> {
    console.log(`Loading model: ${this.config.modelPath}`);

    this.model = await this.client.llm.load(this.config.modelPath, {
      config: {
        gpuOffload: "max",
        contextLength: this.config.contextLength || 8192
      },
      noHup: this.config.keepLoaded  // Keep model loaded after disconnect
    });

    console.log("Model loaded successfully");
  }

  async processObservation(observation: string): Promise<string> {
    this.conversationHistory.push({ role: "user", content: observation });

    const prediction = this.model.respond(this.conversationHistory);

    let fullResponse = "";
    process.stdout.write("Analysis: ");

    for await (const text of prediction) {
      process.stdout.write(text);
      fullResponse += text;
    }

    console.log();

    this.conversationHistory.push({ role: "assistant", content: fullResponse });

    // Prune old messages if needed (keep system + last 10 exchanges)
    if (this.conversationHistory.length > 21) {
      this.conversationHistory = [
        this.conversationHistory[0],  // Keep system prompt
        ...this.conversationHistory.slice(-20)  // Keep last 20 messages
      ];
    }

    return fullResponse;
  }

  async getModelInfo(): Promise<object> {
    const contextLength = await this.model.getContextLength();
    return {
      path: this.config.modelPath,
      contextLength,
      conversationLength: this.conversationHistory.length
    };
  }

  async shutdown(): Promise<void> {
    if (!this.config.keepLoaded) {
      await this.model.unload();
      console.log("Model unloaded");
    }
  }
}

// Usage
async function main() {
  const monitor = new LMStudioMonitor({
    modelPath: "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF",
    systemPrompt: `You are an intelligent system monitor analyzing metrics.
    Identify patterns, anomalies, and provide actionable insights.`,
    keepLoaded: true,
    contextLength: 8192
  });

  await monitor.initialize();

  const observations = [
    "CPU: 45%, Memory: 62%, Network: stable",
    "CPU: 78%, Memory: 75%, Network: degraded",
    "CPU: 95%, Memory: 92%, Network: critical"
  ];

  for (const obs of observations) {
    console.log(`\nObservation: ${obs}`);
    await monitor.processObservation(obs);
    console.log(`Model info: ${JSON.stringify(await monitor.getModelInfo())}`);
  }
}

main().catch(console.error);
```

### Example 6: Headless Server Setup

```bash
#!/bin/bash
# LM Studio headless server setup for continuous monitoring

# Start LM Studio server (daemon mode)
lms server start --port 1234

# Load model with extended TTL (24 hours)
lms load "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF" --ttl 86400

# Check server status
lms ps

# For systemd service (Linux), create /etc/systemd/user/lmstudio.service:
# [Unit]
# Description=LM Studio Local LLM Server
# After=network.target
#
# [Service]
# Type=simple
# ExecStart=/opt/lm-studio/lm-studio --run-as-a-service
# Restart=always
# RestartSec=10
#
# [Install]
# WantedBy=default.target

# Enable and start service
# systemctl --user enable lmstudio
# systemctl --user start lmstudio
```

---

## Best Practices for Continuous Monitoring

### 1. Model Selection
- Choose models optimized for your context length needs
- Consider quantized models (Q4/Q5) for memory efficiency
- Test with smaller context first, scale up gradually

### 2. Context Management
- Use `rollingWindow` overflow policy for chat-style monitoring
- Implement manual context pruning for fine-grained control
- Reserve tokens for response generation (1024+ recommended)

### 3. Resource Optimization
- Monitor VRAM usage during operation
- Use `noHup: true` to prevent unnecessary model reloads
- Set appropriate TTL for your use case

### 4. Error Handling
- Implement reconnection logic for server disconnects
- Handle context overflow gracefully
- Log token usage for debugging

### 5. Performance Monitoring
- Use REST API v0 for enhanced statistics (tokens/sec, TTFT)
- Track context usage over time
- Monitor response latency trends

---

## JavaScript/TypeScript Implementation Examples

### Example 7: OpenAI-Compatible Client (TypeScript)

```typescript
/**
 * LM Studio connection using OpenAI-compatible API.
 * Recommended for applications that need to switch between local and cloud.
 */
import OpenAI from "openai";

interface LMStudioConfig {
  baseURL?: string;
  timeout?: number;
  maxRetries?: number;
}

function createLMStudioClient(config: LMStudioConfig = {}): OpenAI {
  return new OpenAI({
    baseURL: config.baseURL || "http://localhost:1234/v1",
    apiKey: "lm-studio", // Not validated, but required by the client
    timeout: config.timeout || 120000, // 2 minutes default
    maxRetries: config.maxRetries || 3,
  });
}

async function streamChatCompletion(
  client: OpenAI,
  messages: OpenAI.ChatCompletionMessageParam[],
  onToken: (token: string) => void
): Promise<string> {
  const stream = await client.chat.completions.create({
    model: "local-model", // LM Studio uses whatever model is loaded
    messages,
    stream: true,
    stream_options: { include_usage: true },
  });

  let fullResponse = "";
  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content;
    if (content) {
      fullResponse += content;
      onToken(content);
    }
  }
  return fullResponse;
}

// Usage example
async function main() {
  const client = createLMStudioClient();

  const messages: OpenAI.ChatCompletionMessageParam[] = [
    { role: "system", content: "You are a helpful assistant." },
    { role: "user", content: "Explain consciousness briefly." },
  ];

  console.log("Response: ");
  const response = await streamChatCompletion(client, messages, (token) => {
    process.stdout.write(token);
  });
  console.log("\n\nFull response length:", response.length);
}

main().catch(console.error);
```

### Example 8: Cancelling Predictions with AbortController

```typescript
/**
 * Demonstrates cancellation of running predictions.
 * Essential for responsive UIs and resource management.
 */
import { LMStudioClient } from "@lmstudio/sdk";

class CancellablePrediction {
  private client: LMStudioClient;
  private model: any;
  private currentController: AbortController | null = null;

  constructor() {
    this.client = new LMStudioClient();
  }

  async initialize(modelPath: string): Promise<void> {
    this.model = await this.client.llm.load(modelPath, {
      config: { gpuOffload: "max" },
      noHup: true,
    });
  }

  async predict(
    prompt: string,
    onToken: (token: string) => void,
    timeoutMs?: number
  ): Promise<{ content: string; cancelled: boolean }> {
    // Cancel any existing prediction
    this.cancel();

    this.currentController = new AbortController();
    let cancelled = false;

    // Optional timeout
    let timeoutId: NodeJS.Timeout | undefined;
    if (timeoutMs) {
      timeoutId = setTimeout(() => {
        this.cancel();
        cancelled = true;
      }, timeoutMs);
    }

    try {
      const prediction = this.model.complete(prompt, {
        signal: this.currentController.signal,
        maxTokens: 2048,
      });

      let fullContent = "";
      for await (const text of prediction) {
        fullContent += text;
        onToken(text);
      }

      return { content: fullContent, cancelled };
    } catch (error: any) {
      if (error.name === "AbortError") {
        return { content: "", cancelled: true };
      }
      throw error;
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
      this.currentController = null;
    }
  }

  cancel(): void {
    if (this.currentController) {
      this.currentController.abort();
      this.currentController = null;
    }
  }
}

// Usage with timeout
async function main() {
  const predictor = new CancellablePrediction();
  await predictor.initialize("lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF");

  // Prediction with 30-second timeout
  const result = await predictor.predict(
    "Write a detailed essay about AI consciousness",
    (token) => process.stdout.write(token),
    30000 // 30 second timeout
  );

  if (result.cancelled) {
    console.log("\n[Prediction was cancelled or timed out]");
  }
}

main().catch(console.error);
```

### Example 9: Robust Connection with Retry Logic

```typescript
/**
 * Resilient LM Studio client with automatic reconnection.
 * Handles connection drops and server restarts gracefully.
 */
import OpenAI from "openai";

interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
}

class ResilientLMStudioClient {
  private client: OpenAI;
  private retryConfig: RetryConfig;
  private isConnected: boolean = false;

  constructor(
    baseURL: string = "http://localhost:1234/v1",
    retryConfig: Partial<RetryConfig> = {}
  ) {
    this.retryConfig = {
      maxRetries: retryConfig.maxRetries ?? 5,
      baseDelayMs: retryConfig.baseDelayMs ?? 1000,
      maxDelayMs: retryConfig.maxDelayMs ?? 30000,
      backoffMultiplier: retryConfig.backoffMultiplier ?? 2,
    };

    this.client = new OpenAI({
      baseURL,
      apiKey: "lm-studio",
      timeout: 120000,
      maxRetries: 0, // We handle retries ourselves
    });
  }

  private async delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private calculateDelay(attempt: number): number {
    const delay =
      this.retryConfig.baseDelayMs *
      Math.pow(this.retryConfig.backoffMultiplier, attempt);
    return Math.min(delay, this.retryConfig.maxDelayMs);
  }

  async checkConnection(): Promise<boolean> {
    try {
      await this.client.models.list();
      this.isConnected = true;
      return true;
    } catch {
      this.isConnected = false;
      return false;
    }
  }

  async waitForConnection(maxWaitMs: number = 60000): Promise<boolean> {
    const startTime = Date.now();
    let attempt = 0;

    while (Date.now() - startTime < maxWaitMs) {
      if (await this.checkConnection()) {
        console.log("Connected to LM Studio");
        return true;
      }

      const waitTime = this.calculateDelay(attempt);
      console.log(
        `Connection attempt ${attempt + 1} failed. Retrying in ${waitTime}ms...`
      );
      await this.delay(waitTime);
      attempt++;
    }

    return false;
  }

  async chatWithRetry(
    messages: OpenAI.ChatCompletionMessageParam[],
    options: Partial<OpenAI.ChatCompletionCreateParams> = {}
  ): Promise<OpenAI.ChatCompletion> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.retryConfig.maxRetries; attempt++) {
      try {
        return await this.client.chat.completions.create({
          model: options.model || "local-model",
          messages,
          ...options,
          stream: false,
        } as OpenAI.ChatCompletionCreateParamsNonStreaming);
      } catch (error: any) {
        lastError = error;

        // Check if error is retryable
        const isRetryable =
          error.code === "ECONNREFUSED" ||
          error.code === "ECONNRESET" ||
          error.code === "ETIMEDOUT" ||
          error.message?.includes("socket hang up");

        if (!isRetryable || attempt === this.retryConfig.maxRetries - 1) {
          throw error;
        }

        const waitTime = this.calculateDelay(attempt);
        console.warn(
          `Request failed (attempt ${attempt + 1}/${this.retryConfig.maxRetries}): ${error.message}`
        );
        console.warn(`Retrying in ${waitTime}ms...`);
        await this.delay(waitTime);

        // Try to reconnect
        await this.waitForConnection(waitTime);
      }
    }

    throw lastError || new Error("Max retries exceeded");
  }

  async *streamWithRetry(
    messages: OpenAI.ChatCompletionMessageParam[],
    options: Partial<OpenAI.ChatCompletionCreateParams> = {}
  ): AsyncGenerator<string, void, unknown> {
    let attempt = 0;

    while (attempt < this.retryConfig.maxRetries) {
      try {
        const stream = await this.client.chat.completions.create({
          model: options.model || "local-model",
          messages,
          ...options,
          stream: true,
        });

        for await (const chunk of stream) {
          const content = chunk.choices[0]?.delta?.content;
          if (content) {
            yield content;
          }
        }
        return; // Success, exit the retry loop
      } catch (error: any) {
        attempt++;

        if (attempt >= this.retryConfig.maxRetries) {
          throw error;
        }

        const waitTime = this.calculateDelay(attempt);
        console.warn(`Stream error, retrying in ${waitTime}ms...`);
        await this.delay(waitTime);
      }
    }
  }
}

// Usage example
async function main() {
  const client = new ResilientLMStudioClient("http://localhost:1234/v1", {
    maxRetries: 5,
    baseDelayMs: 1000,
  });

  // Wait for LM Studio to be available
  const connected = await client.waitForConnection(60000);
  if (!connected) {
    console.error("Failed to connect to LM Studio");
    process.exit(1);
  }

  // Make requests with automatic retry
  const messages: OpenAI.ChatCompletionMessageParam[] = [
    { role: "user", content: "Hello, how are you?" },
  ];

  // Non-streaming with retry
  const response = await client.chatWithRetry(messages);
  console.log("Response:", response.choices[0].message.content);

  // Streaming with retry
  console.log("\nStreaming response: ");
  for await (const token of client.streamWithRetry(messages)) {
    process.stdout.write(token);
  }
  console.log();
}

main().catch(console.error);
```

### Example 10: Continuous Monitoring Loop with Health Checks

```typescript
/**
 * Production-ready continuous monitoring loop.
 * Features health checks, graceful degradation, and metrics.
 */
import { LMStudioClient } from "@lmstudio/sdk";
import { EventEmitter } from "events";

interface MonitoringMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageLatencyMs: number;
  tokensGenerated: number;
  lastHealthCheck: Date | null;
  isHealthy: boolean;
}

interface MonitoringEvent {
  timestamp: Date;
  type: "observation" | "analysis" | "error" | "health";
  data: any;
}

class ContinuousMonitoringLoop extends EventEmitter {
  private client: LMStudioClient;
  private model: any;
  private isRunning: boolean = false;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private metrics: MonitoringMetrics;
  private conversationHistory: Array<{ role: string; content: string }> = [];
  private systemPrompt: string;

  constructor(systemPrompt: string) {
    super();
    this.client = new LMStudioClient();
    this.systemPrompt = systemPrompt;
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageLatencyMs: 0,
      tokensGenerated: 0,
      lastHealthCheck: null,
      isHealthy: false,
    };
    this.conversationHistory = [{ role: "system", content: systemPrompt }];
  }

  async initialize(modelPath: string): Promise<void> {
    this.model = await this.client.llm.load(modelPath, {
      config: { gpuOffload: "max", contextLength: 8192 },
      noHup: true,
    });

    // Start health check loop
    this.healthCheckInterval = setInterval(() => this.healthCheck(), 30000);
    await this.healthCheck();
  }

  private async healthCheck(): Promise<void> {
    try {
      // Simple health check - try to get context length
      await this.model.getContextLength();
      this.metrics.isHealthy = true;
      this.metrics.lastHealthCheck = new Date();
      this.emit("health", { status: "healthy", timestamp: new Date() });
    } catch (error) {
      this.metrics.isHealthy = false;
      this.emit("health", {
        status: "unhealthy",
        error,
        timestamp: new Date(),
      });
    }
  }

  async processObservation(observation: string): Promise<string | null> {
    if (!this.metrics.isHealthy) {
      this.emit("error", { message: "Model unhealthy, skipping observation" });
      return null;
    }

    const startTime = Date.now();
    this.metrics.totalRequests++;

    try {
      this.conversationHistory.push({ role: "user", content: observation });
      this.emit("observation", { observation, timestamp: new Date() });

      const prediction = this.model.respond(this.conversationHistory);

      let fullResponse = "";
      let tokenCount = 0;

      for await (const text of prediction) {
        fullResponse += text;
        tokenCount++;
        this.emit("token", { token: text, tokenCount });
      }

      this.conversationHistory.push({
        role: "assistant",
        content: fullResponse,
      });

      // Update metrics
      const latency = Date.now() - startTime;
      this.metrics.successfulRequests++;
      this.metrics.tokensGenerated += tokenCount;
      this.metrics.averageLatencyMs =
        (this.metrics.averageLatencyMs *
          (this.metrics.successfulRequests - 1) +
          latency) /
        this.metrics.successfulRequests;

      // Prune context if needed
      this.pruneContext();

      this.emit("analysis", {
        observation,
        response: fullResponse,
        latencyMs: latency,
        tokenCount,
        timestamp: new Date(),
      });

      return fullResponse;
    } catch (error) {
      this.metrics.failedRequests++;
      this.emit("error", {
        observation,
        error,
        timestamp: new Date(),
      });
      return null;
    }
  }

  private pruneContext(): void {
    // Keep system prompt + last 20 messages
    if (this.conversationHistory.length > 21) {
      this.conversationHistory = [
        this.conversationHistory[0],
        ...this.conversationHistory.slice(-20),
      ];
    }
  }

  async startLoop(
    getObservation: () => Promise<string>,
    intervalMs: number = 5000
  ): Promise<void> {
    this.isRunning = true;

    while (this.isRunning) {
      try {
        const observation = await getObservation();
        await this.processObservation(observation);
      } catch (error) {
        this.emit("error", { message: "Failed to get observation", error });
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  }

  stop(): void {
    this.isRunning = false;
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
  }

  getMetrics(): MonitoringMetrics {
    return { ...this.metrics };
  }

  resetConversation(): void {
    this.conversationHistory = [{ role: "system", content: this.systemPrompt }];
  }
}

// Usage
async function main() {
  const monitor = new ContinuousMonitoringLoop(`
    You are an intelligent system monitor. Analyze each observation and:
    1. Identify any anomalies or concerning patterns
    2. Compare with previous observations for trends
    3. Recommend actions if thresholds are exceeded
    Keep responses concise but informative.
  `);

  // Event handlers
  monitor.on("health", (status) => console.log("Health:", status));
  monitor.on("observation", (data) =>
    console.log("\n[IN]:", data.observation)
  );
  monitor.on("analysis", (data) =>
    console.log("[OUT]:", data.response.substring(0, 100) + "...")
  );
  monitor.on("error", (err) => console.error("[ERR]:", err));

  await monitor.initialize(
    "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF"
  );

  // Simulated observation source
  let counter = 0;
  const getObservation = async (): Promise<string> => {
    counter++;
    const cpu = 40 + Math.random() * 50;
    const mem = 50 + Math.random() * 40;
    return `[${counter}] CPU: ${cpu.toFixed(1)}%, Memory: ${mem.toFixed(1)}%`;
  };

  // Run for 60 seconds then stop
  setTimeout(() => {
    monitor.stop();
    console.log("\nFinal metrics:", monitor.getMetrics());
  }, 60000);

  await monitor.startLoop(getObservation, 5000);
}

main().catch(console.error);
```

---

## Known Issues and Workarounds

### 1. Connection Timeouts

**Issue**: Some clients have hardcoded 300-second (5-minute) timeouts that can interrupt long-running generations.

**Symptoms**:
- "client disconnected" messages in LM Studio logs
- Requests terminating after exactly 300 seconds

**Workarounds**:
- Use streaming to get incremental results before timeout
- Implement chunked requests for long generations
- Configure custom timeout in HTTP client (if supported)

### 2. Socket Hang Up Errors

**Issue**: Node.js HTTP clients may experience intermittent socket termination with "socket hang up" and "ECONNRESET" errors.

**Symptoms**:
- Errors appearing after extended operation (2-3 seconds into request)
- Both streaming and non-streaming requests affected

**Workarounds**:
```typescript
// Implement retry logic with exponential backoff
const retryWithBackoff = async (fn, maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
    }
  }
};
```

### 3. Keep-Alive Connection Drops

**Issue**: LM Studio uses `Keep-Alive: timeout=5` which may cause connections to be dropped after 5 seconds of inactivity.

**Workarounds**:
- Use a new connection for each request (stateless pattern)
- Implement connection pooling with health checks
- Use the LM Studio native SDK which handles connection management

### 4. Model Auto-Unloading

**Issue**: JIT-loaded models have a 60-minute TTL by default and will be unloaded automatically.

**Solutions**:
```typescript
// Option 1: Use noHup when loading via SDK
await client.llm.load("model-path", { noHup: true });

// Option 2: Use CLI loading (no TTL)
// lms load "model-path"

// Option 3: Set extended TTL
// lms load "model-path" --ttl 86400  # 24 hours
```

---

## References

- [LM Studio Documentation](https://lmstudio.ai/docs)
- [OpenAI Compatibility Endpoints](https://lmstudio.ai/docs/developer/openai-compat)
- [LM Studio REST API v0](https://lmstudio.ai/docs/developer/rest/endpoints)
- [Python SDK (lmstudio-python)](https://lmstudio.ai/docs/python)
- [TypeScript SDK (lmstudio-js)](https://lmstudio.ai/docs/typescript)
- [TypeScript SDK GitHub](https://github.com/lmstudio-ai/lmstudio-js)
- [Cancelling Predictions](https://lmstudio.ai/docs/typescript/llm-prediction/cancelling-predictions)
- [Idle TTL and Auto-Evict](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict)
- [Headless Mode](https://lmstudio.ai/docs/developer/core/headless)
- [Server Settings](https://lmstudio.ai/docs/developer/core/server/settings)
- [Serve on Local Network](https://lmstudio.ai/docs/developer/core/server/serve-on-network)
- [Context Window Management](https://lmstudio.ai/docs/typescript/api-reference/llm-prediction-config-input)
- [Model Loading Options](https://lmstudio.ai/docs/typescript/manage-models/loading)
