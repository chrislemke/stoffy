# Continuous LLM Processing Loop Architectures

## Research Overview

This document explores architectures for continuous and streaming LLM processing loops, investigating patterns from autonomous agent systems, event-driven architectures, and real-time stream processing. The goal is to identify robust patterns for building systems that can monitor, react, and process LLM outputs continuously over extended periods.

---

## 1. Continuous Processing Patterns

### 1.1 Event-Driven LLM Invocation

Event-driven architectures invoke LLM processing in response to external stimuli rather than on fixed schedules. This pattern is optimal for reactive systems where processing should occur "just in time."

**Key Characteristics:**
- Decoupled producers and consumers
- Asynchronous message passing
- Natural load distribution
- Scalable through event partitioning

**Architecture Pattern:**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Event      │────>│  Event      │────>│  LLM        │
│  Sources    │     │  Queue      │     │  Workers    │
│  (Sensors,  │     │  (Kafka,    │     │  (Consumers)│
│   APIs,     │     │   RabbitMQ, │     │             │
│   Webhooks) │     │   Redis)    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           v
                    ┌─────────────┐
                    │  Response   │
                    │  Handler    │
                    └─────────────┘
```

**Pseudo-code: Event-Driven LLM Handler**

```python
class EventDrivenLLMProcessor:
    """
    Event-driven LLM processor that responds to external events.
    """

    def __init__(self, event_queue, llm_client, response_handler):
        self.event_queue = event_queue
        self.llm_client = llm_client
        self.response_handler = response_handler
        self.running = False

    async def start(self):
        """Start the event processing loop."""
        self.running = True
        while self.running:
            try:
                # Wait for events with timeout
                event = await self.event_queue.get(timeout=30.0)

                # Process event through LLM
                response = await self.process_event(event)

                # Handle response
                await self.response_handler.handle(response)

            except TimeoutError:
                # Heartbeat / health check
                await self.emit_heartbeat()

            except Exception as e:
                await self.handle_error(e, event)

    async def process_event(self, event):
        """Transform event into LLM prompt and process."""
        prompt = self.event_to_prompt(event)
        return await self.llm_client.generate(prompt)
```

### 1.2 Polling-Based Approaches

Polling patterns periodically check for new work or state changes. While less efficient than event-driven, they are simpler to implement and provide predictable timing.

**Polling Strategies:**

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Fixed Interval | Poll at constant intervals | Simple monitoring |
| Adaptive Interval | Adjust based on activity | Variable workloads |
| Exponential Backoff | Increase delay after idle | Rate-limited APIs |
| Long Polling | Keep connection open | Near real-time with simple clients |

**Pseudo-code: Adaptive Polling Loop**

```python
class AdaptivePollingLoop:
    """
    Polling loop with adaptive intervals based on activity.
    """

    def __init__(
        self,
        min_interval: float = 1.0,
        max_interval: float = 60.0,
        backoff_factor: float = 1.5,
        activity_threshold: int = 5
    ):
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.backoff_factor = backoff_factor
        self.activity_threshold = activity_threshold
        self.current_interval = min_interval
        self.consecutive_empty = 0

    async def run(self, poll_source, processor):
        """Main polling loop with adaptive intervals."""
        while True:
            try:
                # Poll for new items
                items = await poll_source.fetch()

                if items:
                    # Reset interval on activity
                    self.consecutive_empty = 0
                    self.current_interval = self.min_interval

                    # Process items
                    for item in items:
                        await processor.process(item)
                else:
                    # Increase interval on inactivity
                    self.consecutive_empty += 1
                    if self.consecutive_empty >= self.activity_threshold:
                        self.current_interval = min(
                            self.current_interval * self.backoff_factor,
                            self.max_interval
                        )

                # Wait for next poll
                await asyncio.sleep(self.current_interval)

            except Exception as e:
                await self.handle_error(e)
                await asyncio.sleep(self.current_interval)
```

### 1.3 Reactive/Stream-Based Processing

Reactive streams provide declarative pipelines for processing continuous data flows with built-in backpressure handling.

**Core Reactive Principles:**
1. **Responsive**: System responds in a timely manner
2. **Resilient**: System remains responsive during failures
3. **Elastic**: System scales to handle varying load
4. **Message-Driven**: Asynchronous message passing

**Stream Processing Pipeline:**

```
┌──────┐   ┌──────────┐   ┌───────────┐   ┌────────┐   ┌────────┐
│Source│──>│Transform │──>│   LLM     │──>│Aggregate│──>│  Sink  │
│      │   │ (Filter, │   │ Inference │   │ (Reduce,│   │(Storage,│
│      │   │  Map)    │   │           │   │ Window) │   │ Output) │
└──────┘   └──────────┘   └───────────┘   └────────┘   └────────┘
     │                           │
     └───────────────────────────┘
            Backpressure Flow
```

**Pseudo-code: Reactive LLM Stream**

```python
class ReactiveLLMStream:
    """
    Reactive stream processor for continuous LLM inference.
    """

    def __init__(self, source, llm_client, sink, buffer_size=100):
        self.source = source
        self.llm_client = llm_client
        self.sink = sink
        self.buffer = asyncio.Queue(maxsize=buffer_size)
        self.backpressure_threshold = 0.8

    async def create_pipeline(self):
        """Create reactive processing pipeline."""

        async def transform_stage():
            """Apply transformations before LLM."""
            async for item in self.source:
                # Apply backpressure if buffer is filling
                if self.buffer.qsize() / self.buffer.maxsize > self.backpressure_threshold:
                    await self.signal_backpressure()

                transformed = await self.transform(item)
                await self.buffer.put(transformed)

        async def inference_stage():
            """Run LLM inference on transformed items."""
            while True:
                item = await self.buffer.get()
                try:
                    result = await self.llm_client.generate(item)
                    await self.sink.emit(result)
                except Exception as e:
                    await self.handle_inference_error(e, item)
                finally:
                    self.buffer.task_done()

        # Run stages concurrently
        await asyncio.gather(
            transform_stage(),
            inference_stage()
        )
```

### 1.4 Background Daemon Architectures

Daemon processes run continuously in the background, maintaining persistent state and providing always-on processing capabilities.

**Daemon Components:**

| Component | Responsibility |
|-----------|----------------|
| Process Manager | Lifecycle, restarts, health |
| Work Queue | Job scheduling, prioritization |
| State Store | Persistent context, checkpoints |
| IPC Layer | Communication with clients |
| Health Monitor | Liveness, metrics, alerts |

**Pseudo-code: LLM Daemon Process**

```python
class LLMDaemon:
    """
    Background daemon for continuous LLM processing.
    """

    def __init__(self, config):
        self.config = config
        self.state_store = StateStore(config.state_path)
        self.work_queue = WorkQueue()
        self.llm_client = LLMClient(config.model)
        self.health_monitor = HealthMonitor()
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start the daemon and all subsystems."""
        # Restore state from last run
        await self.restore_state()

        # Start subsystems
        await asyncio.gather(
            self.run_work_loop(),
            self.run_health_checks(),
            self.run_ipc_server(),
            self.run_state_persistence()
        )

    async def run_work_loop(self):
        """Main work processing loop."""
        while not self.shutdown_event.is_set():
            try:
                # Get work with timeout for graceful shutdown
                work_item = await asyncio.wait_for(
                    self.work_queue.get(),
                    timeout=5.0
                )

                # Process through LLM
                result = await self.process_work(work_item)

                # Update state
                await self.state_store.record_completion(work_item, result)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                await self.handle_work_error(e)

    async def graceful_shutdown(self):
        """Perform graceful shutdown with state persistence."""
        self.shutdown_event.set()

        # Drain work queue
        await self.work_queue.drain()

        # Persist final state
        await self.state_store.persist()

        # Close connections
        await self.llm_client.close()
```

---

## 2. AutoGPT-Style Loops

### 2.1 Continuous Agent Loops

AutoGPT pioneered the continuous autonomous agent loop pattern where an LLM repeatedly plans, acts, and observes in a cycle until a goal is achieved.

**Core Loop Structure:**

```
┌───────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS AGENT LOOP                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│  │  GOAL   │───>│  PLAN   │───>│   ACT   │───>│ OBSERVE │   │
│  │         │    │         │    │         │    │         │   │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘   │
│       ^                                             │        │
│       │                                             │        │
│       │         ┌─────────────────────┐             │        │
│       └─────────│  REFLECT & UPDATE   │<────────────┘        │
│                 └─────────────────────┘                      │
│                         │                                    │
│                         v                                    │
│                 ┌─────────────────────┐                      │
│                 │  GOAL COMPLETE?     │                      │
│                 │  yes -> EXIT        │                      │
│                 │  no  -> CONTINUE    │                      │
│                 └─────────────────────┘                      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**Pseudo-code: AutoGPT-Style Agent Loop**

```python
class AutonomousAgentLoop:
    """
    Continuous autonomous agent with goal-driven planning and execution.
    """

    def __init__(
        self,
        llm_client,
        tool_executor,
        memory,
        goal: str,
        max_iterations: int = 100
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.memory = memory
        self.goal = goal
        self.max_iterations = max_iterations
        self.iteration = 0

    async def run(self) -> AgentResult:
        """Execute the autonomous agent loop."""

        while self.iteration < self.max_iterations:
            self.iteration += 1

            # PLAN: Generate next action plan
            plan = await self.generate_plan()

            # Check for goal completion
            if plan.is_goal_complete:
                return AgentResult(
                    success=True,
                    summary=plan.completion_summary,
                    iterations=self.iteration
                )

            # ACT: Execute planned actions
            action_results = await self.execute_actions(plan.actions)

            # OBSERVE: Process results
            observations = await self.process_observations(action_results)

            # REFLECT: Update memory and strategy
            await self.reflect_and_update(plan, observations)

            # Check stopping conditions
            if await self.should_stop():
                break

        return AgentResult(
            success=False,
            reason="max_iterations_reached",
            iterations=self.iteration
        )

    async def generate_plan(self) -> Plan:
        """Generate next action plan using LLM."""

        # Build planning prompt
        prompt = self.build_planning_prompt(
            goal=self.goal,
            memory=await self.memory.get_recent(limit=10),
            available_tools=self.tool_executor.get_tools()
        )

        # Get LLM response
        response = await self.llm_client.generate(prompt)

        # Parse into structured plan
        return self.parse_plan(response)

    async def reflect_and_update(self, plan, observations):
        """Reflect on results and update strategy."""

        # Store observation in memory
        await self.memory.store({
            "iteration": self.iteration,
            "plan": plan.to_dict(),
            "observations": observations,
            "timestamp": datetime.now()
        })

        # Analyze progress toward goal
        progress = await self.analyze_progress(observations)

        # Adjust strategy if needed
        if progress.is_stalled:
            await self.adjust_strategy(progress.bottlenecks)
```

### 2.2 Task Decomposition and Iteration

Complex goals require decomposition into manageable sub-tasks. The agent iteratively works through these while maintaining coherence.

**Task Decomposition Pattern:**

```
                    ┌───────────────────┐
                    │   HIGH-LEVEL GOAL │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              v               v               v
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Sub-Task │    │ Sub-Task │    │ Sub-Task │
        │    1     │    │    2     │    │    3     │
        └────┬─────┘    └────┬─────┘    └────┬─────┘
             │               │               │
        ┌────┴────┐     ┌────┴────┐     ┌────┴────┐
        v         v     v         v     v         v
      [Action] [Action] [Action] [Action] [Action] [Action]
```

**Pseudo-code: Task Decomposition Engine**

```python
class TaskDecompositionEngine:
    """
    Decomposes complex goals into executable sub-tasks.
    """

    def __init__(self, llm_client, max_depth=3):
        self.llm_client = llm_client
        self.max_depth = max_depth
        self.task_graph = TaskGraph()

    async def decompose(self, goal: str) -> TaskGraph:
        """Recursively decompose goal into task tree."""

        root_task = Task(
            id=generate_id(),
            description=goal,
            depth=0,
            status="pending"
        )

        self.task_graph.add_node(root_task)
        await self._decompose_recursive(root_task)

        return self.task_graph

    async def _decompose_recursive(self, task: Task):
        """Recursively break down a task."""

        if task.depth >= self.max_depth:
            return

        # Check if task is atomic (can be executed directly)
        if await self.is_atomic(task):
            return

        # Get sub-tasks from LLM
        sub_tasks = await self.generate_sub_tasks(task)

        for sub_task in sub_tasks:
            sub_task.depth = task.depth + 1
            sub_task.parent_id = task.id

            self.task_graph.add_node(sub_task)
            self.task_graph.add_edge(task.id, sub_task.id)

            # Recursively decompose
            await self._decompose_recursive(sub_task)

    async def execute_graph(self) -> ExecutionResult:
        """Execute task graph respecting dependencies."""

        while not self.task_graph.is_complete():
            # Get tasks ready for execution
            ready_tasks = self.task_graph.get_ready_tasks()

            # Execute in parallel where possible
            results = await asyncio.gather(*[
                self.execute_task(task) for task in ready_tasks
            ])

            # Update graph with results
            for task, result in zip(ready_tasks, results):
                self.task_graph.mark_complete(task.id, result)

        return self.task_graph.get_result()
```

### 2.3 Stopping Conditions and Guardrails

Continuous loops require robust stopping conditions to prevent runaway execution, resource exhaustion, or harmful outputs.

**Stopping Condition Categories:**

| Category | Examples |
|----------|----------|
| Goal Achievement | Task complete, objective met |
| Resource Limits | Token budget, time limit, iteration cap |
| Safety Triggers | Harmful content detected, anomaly |
| Quality Gates | Confidence too low, repeated failures |
| User Intervention | Manual stop, priority override |

**Pseudo-code: Guardrail System**

```python
class GuardrailSystem:
    """
    Multi-layer guardrail system for autonomous agent loops.
    """

    def __init__(self, config: GuardrailConfig):
        self.config = config
        self.metrics = MetricsCollector()
        self.safety_checker = SafetyChecker()

    async def check_all(self, context: LoopContext) -> GuardrailResult:
        """Run all guardrail checks."""

        checks = [
            self.check_iteration_limit(context),
            self.check_token_budget(context),
            self.check_time_limit(context),
            self.check_safety(context),
            self.check_quality(context),
            self.check_progress(context),
            self.check_user_signals(context)
        ]

        results = await asyncio.gather(*checks)

        # Any failure triggers stop
        for result in results:
            if result.should_stop:
                return result

        return GuardrailResult(should_stop=False)

    async def check_iteration_limit(self, ctx) -> GuardrailResult:
        """Check if iteration limit exceeded."""
        if ctx.iteration >= self.config.max_iterations:
            return GuardrailResult(
                should_stop=True,
                reason="iteration_limit_exceeded",
                severity="warning"
            )
        return GuardrailResult(should_stop=False)

    async def check_token_budget(self, ctx) -> GuardrailResult:
        """Check if token budget exhausted."""
        if ctx.total_tokens >= self.config.max_tokens:
            return GuardrailResult(
                should_stop=True,
                reason="token_budget_exhausted",
                severity="warning"
            )
        return GuardrailResult(should_stop=False)

    async def check_safety(self, ctx) -> GuardrailResult:
        """Run safety checks on recent outputs."""
        safety_score = await self.safety_checker.evaluate(
            ctx.recent_outputs
        )

        if safety_score < self.config.safety_threshold:
            return GuardrailResult(
                should_stop=True,
                reason="safety_check_failed",
                severity="critical",
                details={"safety_score": safety_score}
            )
        return GuardrailResult(should_stop=False)

    async def check_progress(self, ctx) -> GuardrailResult:
        """Detect if agent is stuck in a loop."""

        # Check for repeated actions
        recent_actions = ctx.get_recent_actions(10)
        unique_actions = len(set(recent_actions))

        if unique_actions < 3:  # Too repetitive
            return GuardrailResult(
                should_stop=True,
                reason="stuck_in_loop",
                severity="warning"
            )

        # Check for diminishing returns
        if ctx.progress_rate < self.config.min_progress_rate:
            return GuardrailResult(
                should_stop=True,
                reason="insufficient_progress",
                severity="info"
            )

        return GuardrailResult(should_stop=False)
```

### 2.4 Resource Management

Long-running agent loops must carefully manage compute, memory, and API resources.

**Resource Management Strategies:**

```python
class ResourceManager:
    """
    Manages resources for long-running agent loops.
    """

    def __init__(self, config: ResourceConfig):
        self.config = config
        self.token_counter = TokenCounter()
        self.cost_tracker = CostTracker()
        self.rate_limiter = RateLimiter(
            requests_per_minute=config.rpm_limit,
            tokens_per_minute=config.tpm_limit
        )

    async def acquire_for_request(self, estimated_tokens: int) -> bool:
        """Acquire resources for an LLM request."""

        # Check budget
        if self.cost_tracker.get_remaining() < self.estimate_cost(estimated_tokens):
            raise BudgetExhaustedException()

        # Apply rate limiting with exponential backoff
        retry_count = 0
        max_retries = 5

        while retry_count < max_retries:
            try:
                await self.rate_limiter.acquire(estimated_tokens)
                return True
            except RateLimitExceeded as e:
                retry_count += 1
                # Exponential backoff with jitter
                delay = min(2 ** retry_count + random.uniform(0, 1), 60)
                await asyncio.sleep(delay)

        raise RateLimitExhaustedException()

    def record_usage(self, tokens_used: int, cost: float):
        """Record resource usage after request."""
        self.token_counter.add(tokens_used)
        self.cost_tracker.add(cost)

    def get_remaining_budget(self) -> ResourceBudget:
        """Get remaining resource budget."""
        return ResourceBudget(
            tokens=self.config.max_tokens - self.token_counter.total,
            cost=self.config.max_cost - self.cost_tracker.total,
            requests=self.rate_limiter.get_remaining()
        )
```

---

## 3. Streaming Architectures

### 3.1 Token-by-Token Processing

Token streaming enables real-time processing of LLM outputs as they are generated, reducing latency and enabling early termination.

**Streaming Benefits:**
- Reduced time-to-first-token latency
- Early stopping on problematic outputs
- Progressive rendering for UIs
- Real-time monitoring and metrics

**Pseudo-code: Token Stream Processor**

```python
class TokenStreamProcessor:
    """
    Process LLM output token-by-token as it streams.
    """

    def __init__(
        self,
        llm_client,
        processors: List[TokenProcessor],
        aggregator: TokenAggregator
    ):
        self.llm_client = llm_client
        self.processors = processors
        self.aggregator = aggregator

    async def process_stream(
        self,
        prompt: str,
        on_token: Optional[Callable] = None
    ) -> StreamResult:
        """Process streaming response token by token."""

        stream = await self.llm_client.create_stream(prompt)

        token_buffer = []
        should_stop_early = False

        async for token in stream:
            # Run token through processors
            for processor in self.processors:
                token, should_stop = await processor.process(token)

                if should_stop:
                    should_stop_early = True
                    await stream.cancel()
                    break

            if should_stop_early:
                break

            # Buffer token
            token_buffer.append(token)

            # Emit to callback if provided
            if on_token:
                await on_token(token)

            # Periodic aggregation
            if len(token_buffer) >= 10:
                await self.aggregator.add_chunk(token_buffer)
                token_buffer = []

        # Final aggregation
        if token_buffer:
            await self.aggregator.add_chunk(token_buffer)

        return StreamResult(
            content=await self.aggregator.get_result(),
            stopped_early=should_stop_early,
            token_count=await self.aggregator.get_token_count()
        )
```

### 3.2 Chunked Processing

Chunking balances the latency benefits of streaming with the efficiency of batch processing.

**Chunk Size Trade-offs:**

| Chunk Size | Latency | Throughput | Memory | Use Case |
|------------|---------|------------|--------|----------|
| Small (1-10 tokens) | Low | Lower | Low | Real-time UIs |
| Medium (50-100 tokens) | Medium | Medium | Medium | Monitoring |
| Large (500+ tokens) | High | Higher | High | Batch processing |

**Pseudo-code: Chunked Stream Handler**

```python
class ChunkedStreamHandler:
    """
    Process streaming LLM output in configurable chunks.
    """

    def __init__(
        self,
        chunk_size: int = 50,
        chunk_timeout: float = 0.5
    ):
        self.chunk_size = chunk_size
        self.chunk_timeout = chunk_timeout

    async def process_chunked(
        self,
        stream: AsyncIterator[str],
        chunk_processor: ChunkProcessor
    ) -> List[ChunkResult]:
        """Process stream in chunks."""

        current_chunk = []
        results = []
        last_chunk_time = time.time()

        async for token in stream:
            current_chunk.append(token)

            # Emit chunk on size threshold or timeout
            should_emit = (
                len(current_chunk) >= self.chunk_size or
                (time.time() - last_chunk_time) >= self.chunk_timeout
            )

            if should_emit and current_chunk:
                result = await chunk_processor.process(current_chunk)
                results.append(result)
                current_chunk = []
                last_chunk_time = time.time()

        # Process final chunk
        if current_chunk:
            result = await chunk_processor.process(current_chunk)
            results.append(result)

        return results
```

### 3.3 Buffer Management

Proper buffer management prevents memory exhaustion and ensures smooth data flow.

**Buffer Strategies:**

```python
class StreamBufferManager:
    """
    Manages buffers for streaming LLM processing.
    """

    def __init__(
        self,
        max_buffer_size: int = 10000,
        high_water_mark: float = 0.8,
        low_water_mark: float = 0.2
    ):
        self.max_buffer_size = max_buffer_size
        self.high_water_mark = high_water_mark
        self.low_water_mark = low_water_mark
        self.buffer = deque(maxlen=max_buffer_size)
        self.buffer_lock = asyncio.Lock()
        self.not_full = asyncio.Condition()
        self.not_empty = asyncio.Condition()

    async def put(self, item) -> bool:
        """Add item to buffer with backpressure."""

        async with self.buffer_lock:
            # Check if buffer is full
            if len(self.buffer) >= self.max_buffer_size:
                # Wait for space or apply backpressure
                async with self.not_full:
                    while len(self.buffer) >= self.max_buffer_size:
                        await self.not_full.wait()

            self.buffer.append(item)

            # Signal consumers
            async with self.not_empty:
                self.not_empty.notify()

            return True

    async def get(self) -> Any:
        """Get item from buffer."""

        async with self.not_empty:
            while len(self.buffer) == 0:
                await self.not_empty.wait()

        async with self.buffer_lock:
            item = self.buffer.popleft()

            # Signal producers if below low water mark
            if len(self.buffer) < self.max_buffer_size * self.low_water_mark:
                async with self.not_full:
                    self.not_full.notify_all()

            return item

    def is_under_pressure(self) -> bool:
        """Check if buffer is approaching capacity."""
        return len(self.buffer) > self.max_buffer_size * self.high_water_mark
```

### 3.4 Backpressure Handling

Backpressure mechanisms prevent overwhelming downstream consumers when they cannot keep up with production rate.

**Backpressure Strategies:**

| Strategy | Description | Trade-off |
|----------|-------------|-----------|
| Drop | Discard excess items | Data loss |
| Block | Wait for consumer | Latency |
| Buffer | Queue items | Memory |
| Sample | Take every Nth item | Reduced fidelity |
| Debounce | Emit last item after pause | Delayed |

**Pseudo-code: Backpressure Controller**

```python
class BackpressureController:
    """
    Controls backpressure between producer and consumer.
    """

    def __init__(
        self,
        strategy: str = "adaptive",
        max_pending: int = 100,
        min_pending: int = 10
    ):
        self.strategy = strategy
        self.max_pending = max_pending
        self.min_pending = min_pending
        self.pending_count = 0
        self.pending_lock = asyncio.Lock()

    async def on_item_produced(self):
        """Called when an item is produced."""
        async with self.pending_lock:
            self.pending_count += 1

            if self.pending_count >= self.max_pending:
                await self.apply_backpressure()

    async def on_item_consumed(self):
        """Called when an item is consumed."""
        async with self.pending_lock:
            self.pending_count = max(0, self.pending_count - 1)

            if self.pending_count <= self.min_pending:
                await self.release_backpressure()

    async def apply_backpressure(self):
        """Apply backpressure to producer."""

        if self.strategy == "block":
            # Wait until consumer catches up
            while self.pending_count >= self.max_pending:
                await asyncio.sleep(0.01)

        elif self.strategy == "sample":
            # Skip items until caught up
            self.sampling_rate = max(0.1, self.min_pending / self.pending_count)

        elif self.strategy == "adaptive":
            # Dynamically adjust production rate
            delay = (self.pending_count / self.max_pending) * 0.1
            await asyncio.sleep(delay)
```

---

## 4. State Management

### 4.1 Context Window Sliding

LLM context windows have fixed sizes. Long-running processes must manage what context to retain.

**Sliding Window Strategies:**

```
FULL HISTORY:        [A][B][C][D][E][F][G][H][I][J][K][L][M][N][O]
                                            │
                                      Context Window
                                            │
TRUNCATE (Simple):                  [H][I][J][K][L][M][N][O]
                                            │
SUMMARIZE (Smart):   [Summary of A-G][H][I][J][K][L][M][N][O]
                                            │
IMPORTANT-FIRST:     [A][D][G][Important items][L][M][N][O]
```

**Pseudo-code: Context Window Manager**

```python
class ContextWindowManager:
    """
    Manages LLM context window for long-running processes.
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        reserve_tokens: int = 2000,  # Reserve for response
        summarizer: Optional[Summarizer] = None
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.available_tokens = max_tokens - reserve_tokens
        self.summarizer = summarizer
        self.messages = []
        self.importance_scorer = ImportanceScorer()

    def add_message(self, message: Message):
        """Add message and manage window."""

        self.messages.append(message)

        while self.get_total_tokens() > self.available_tokens:
            self._compress_context()

    def _compress_context(self):
        """Compress context to fit within window."""

        if self.summarizer:
            self._summarize_old_messages()
        else:
            self._truncate_oldest()

    def _summarize_old_messages(self):
        """Summarize older messages to free tokens."""

        # Find messages to summarize
        messages_to_summarize = []
        tokens_to_free = self.get_total_tokens() - self.available_tokens
        tokens_freed = 0

        for msg in self.messages:
            if msg.role == "system":  # Never summarize system
                continue
            if tokens_freed >= tokens_to_free:
                break

            messages_to_summarize.append(msg)
            tokens_freed += msg.token_count

        if messages_to_summarize:
            # Generate summary
            summary = self.summarizer.summarize(messages_to_summarize)

            # Replace messages with summary
            summary_msg = Message(
                role="system",
                content=f"[Summary of previous conversation]: {summary}",
                is_summary=True
            )

            # Remove summarized messages
            for msg in messages_to_summarize:
                self.messages.remove(msg)

            # Insert summary at beginning
            self.messages.insert(0, summary_msg)

    def _truncate_oldest(self):
        """Simple truncation of oldest messages."""

        while self.get_total_tokens() > self.available_tokens:
            # Find first non-system message
            for i, msg in enumerate(self.messages):
                if msg.role != "system":
                    self.messages.pop(i)
                    break
```

### 4.2 Summarization for Long-Running Contexts

Summarization preserves semantic content while reducing token count.

**Summarization Approaches:**

| Approach | Compression Ratio | Semantic Preservation | Use Case |
|----------|------------------|----------------------|----------|
| Extractive | 3-5x | High | Factual content |
| Abstractive | 5-10x | Medium | Conversations |
| Hierarchical | 10-20x | Variable | Long documents |
| Incremental | 2-3x per step | High | Streaming |

**Pseudo-code: Incremental Summarizer**

```python
class IncrementalSummarizer:
    """
    Incrementally summarize content as it accumulates.
    """

    def __init__(
        self,
        llm_client,
        summary_threshold_tokens: int = 2000,
        target_summary_tokens: int = 500
    ):
        self.llm_client = llm_client
        self.summary_threshold = summary_threshold_tokens
        self.target_tokens = target_summary_tokens
        self.running_summary = ""
        self.unsummarized_content = []

    async def add_content(self, content: str) -> Optional[str]:
        """Add content, returns new summary if threshold reached."""

        self.unsummarized_content.append(content)

        total_tokens = sum(count_tokens(c) for c in self.unsummarized_content)

        if total_tokens >= self.summary_threshold:
            return await self.create_summary()

        return None

    async def create_summary(self) -> str:
        """Create summary incorporating new content."""

        prompt = f"""
        Previous summary:
        {self.running_summary or "No previous summary."}

        New content to incorporate:
        {chr(10).join(self.unsummarized_content)}

        Create an updated summary that:
        1. Preserves key information from the previous summary
        2. Incorporates important new information
        3. Stays under {self.target_tokens} tokens
        4. Prioritizes actionable and decision-relevant information
        """

        self.running_summary = await self.llm_client.generate(prompt)
        self.unsummarized_content = []

        return self.running_summary
```

### 4.3 Checkpoint/Restore Patterns

Checkpointing enables recovery from failures and supports pause/resume functionality.

**Checkpoint Components:**

```python
@dataclass
class Checkpoint:
    """Complete state checkpoint for recovery."""

    # Identification
    checkpoint_id: str
    timestamp: datetime
    version: str

    # Agent State
    goal: str
    current_plan: Optional[Plan]
    completed_tasks: List[TaskResult]
    pending_tasks: List[Task]

    # Memory State
    short_term_memory: List[MemoryItem]
    long_term_memory_index: str  # Reference to external storage

    # Context State
    messages: List[Message]
    context_summary: Optional[str]

    # Metrics State
    iteration_count: int
    token_usage: TokenUsage
    cost_incurred: float

    # Execution State
    last_action: Optional[Action]
    last_observation: Optional[Observation]

    def serialize(self) -> bytes:
        """Serialize checkpoint for storage."""
        return pickle.dumps(self.__dict__)

    @classmethod
    def deserialize(cls, data: bytes) -> "Checkpoint":
        """Deserialize checkpoint from storage."""
        return cls(**pickle.loads(data))
```

**Pseudo-code: Checkpoint Manager**

```python
class CheckpointManager:
    """
    Manages checkpoints for continuous LLM processing.
    """

    def __init__(
        self,
        storage: CheckpointStorage,
        checkpoint_interval: int = 10,  # iterations
        max_checkpoints: int = 5
    ):
        self.storage = storage
        self.checkpoint_interval = checkpoint_interval
        self.max_checkpoints = max_checkpoints
        self.checkpoints = []

    async def maybe_checkpoint(
        self,
        agent_state: AgentState,
        iteration: int
    ) -> Optional[str]:
        """Create checkpoint if interval reached."""

        if iteration % self.checkpoint_interval != 0:
            return None

        return await self.create_checkpoint(agent_state)

    async def create_checkpoint(
        self,
        agent_state: AgentState
    ) -> str:
        """Create a new checkpoint."""

        checkpoint = Checkpoint(
            checkpoint_id=generate_id(),
            timestamp=datetime.now(),
            version="1.0",
            goal=agent_state.goal,
            current_plan=agent_state.current_plan,
            completed_tasks=agent_state.completed_tasks,
            pending_tasks=agent_state.pending_tasks,
            short_term_memory=agent_state.memory.get_short_term(),
            long_term_memory_index=agent_state.memory.get_index_reference(),
            messages=agent_state.context.messages,
            context_summary=agent_state.context.summary,
            iteration_count=agent_state.iteration,
            token_usage=agent_state.metrics.tokens,
            cost_incurred=agent_state.metrics.cost,
            last_action=agent_state.last_action,
            last_observation=agent_state.last_observation
        )

        # Store checkpoint
        await self.storage.save(checkpoint)
        self.checkpoints.append(checkpoint.checkpoint_id)

        # Prune old checkpoints
        if len(self.checkpoints) > self.max_checkpoints:
            old_id = self.checkpoints.pop(0)
            await self.storage.delete(old_id)

        return checkpoint.checkpoint_id

    async def restore(
        self,
        checkpoint_id: str
    ) -> AgentState:
        """Restore agent state from checkpoint."""

        checkpoint = await self.storage.load(checkpoint_id)

        # Rebuild agent state
        return AgentState.from_checkpoint(checkpoint)
```

### 4.4 Memory Hierarchies (Short-term, Long-term)

Effective long-running agents require multi-tier memory systems.

**Memory Hierarchy:**

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY HIERARCHY                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  WORKING MEMORY (Immediate Context)                  │   │
│  │  - Current conversation turn                        │   │
│  │  - Immediate variables and state                    │   │
│  │  - Size: 1-10 items, TTL: current turn              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SHORT-TERM MEMORY (Session Context)                 │   │
│  │  - Recent conversation history                       │   │
│  │  - Current task progress                             │   │
│  │  - Recent observations and actions                   │   │
│  │  - Size: 50-100 items, TTL: session duration         │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LONG-TERM MEMORY (Persistent Knowledge)             │   │
│  │  - Summarized past experiences                       │   │
│  │  - Learned patterns and preferences                  │   │
│  │  - Domain knowledge                                  │   │
│  │  - Size: unlimited, TTL: permanent/decaying          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  VECTOR STORE (Semantic Retrieval)                   │   │
│  │  - Embeddings of all memories                        │   │
│  │  - Enables semantic search                           │   │
│  │  - Similarity-based retrieval                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Pseudo-code: Hierarchical Memory System**

```python
class HierarchicalMemory:
    """
    Multi-tier memory system for long-running agents.
    """

    def __init__(
        self,
        working_memory_size: int = 10,
        short_term_size: int = 100,
        vector_store: VectorStore = None
    ):
        self.working_memory = deque(maxlen=working_memory_size)
        self.short_term = deque(maxlen=short_term_size)
        self.long_term = LongTermStorage()
        self.vector_store = vector_store or VectorStore()

    async def remember(
        self,
        item: MemoryItem,
        importance: float = 0.5
    ):
        """Store item in appropriate memory tier."""

        # Always add to working memory
        self.working_memory.append(item)

        # Add to short-term if moderately important
        if importance >= 0.3:
            self.short_term.append(item)

        # Add to long-term if highly important
        if importance >= 0.7:
            await self.long_term.store(item)

        # Always add to vector store for retrieval
        embedding = await self.embed(item.content)
        await self.vector_store.add(item.id, embedding, item)

    async def recall(
        self,
        query: str,
        k: int = 10
    ) -> List[MemoryItem]:
        """Recall relevant memories using semantic search."""

        # Search vector store
        query_embedding = await self.embed(query)
        similar_items = await self.vector_store.search(
            query_embedding, k=k
        )

        # Combine with working memory (always relevant)
        results = list(self.working_memory) + similar_items

        # Deduplicate and rank
        return self.rank_and_dedupe(results, query)

    async def consolidate(self):
        """Consolidate short-term to long-term memory."""

        # Find items ready for consolidation
        consolidation_candidates = [
            item for item in self.short_term
            if item.access_count >= 3 or item.importance >= 0.6
        ]

        for item in consolidation_candidates:
            # Summarize if needed
            if item.token_count > 100:
                item = await self.summarize_item(item)

            await self.long_term.store(item)

    async def forget(self, decay_rate: float = 0.1):
        """Apply forgetting to reduce memory bloat."""

        # Decay importance scores
        for item in self.short_term:
            item.importance *= (1 - decay_rate)

        # Remove low-importance items
        self.short_term = deque(
            [item for item in self.short_term if item.importance >= 0.1],
            maxlen=self.short_term.maxlen
        )
```

---

## 5. Error Handling

### 5.1 Crash Recovery

Robust systems must recover gracefully from crashes without losing progress.

**Recovery Strategies:**

```python
class CrashRecoveryManager:
    """
    Manages crash recovery for continuous processing.
    """

    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        state_store: StateStore
    ):
        self.checkpoint_manager = checkpoint_manager
        self.state_store = state_store
        self.recovery_log = RecoveryLog()

    async def recover(self) -> Optional[AgentState]:
        """Attempt to recover from crash."""

        # Check for incomplete shutdown
        if not await self.state_store.was_clean_shutdown():
            return await self.recover_from_crash()

        return None

    async def recover_from_crash(self) -> AgentState:
        """Recover agent state after crash."""

        self.recovery_log.log("Starting crash recovery")

        # Find most recent valid checkpoint
        checkpoints = await self.checkpoint_manager.list_checkpoints()

        for checkpoint_id in reversed(checkpoints):
            try:
                # Verify checkpoint integrity
                if await self.verify_checkpoint(checkpoint_id):
                    state = await self.checkpoint_manager.restore(checkpoint_id)
                    self.recovery_log.log(f"Recovered from checkpoint {checkpoint_id}")

                    # Mark any in-progress work as needing retry
                    state = await self.handle_incomplete_work(state)

                    return state

            except CheckpointCorrupted:
                self.recovery_log.log(f"Checkpoint {checkpoint_id} corrupted, trying earlier")
                continue

        raise RecoveryFailed("No valid checkpoint found")

    async def verify_checkpoint(self, checkpoint_id: str) -> bool:
        """Verify checkpoint integrity."""

        try:
            checkpoint = await self.checkpoint_manager.load_metadata(checkpoint_id)

            # Verify checksum
            if not self.verify_checksum(checkpoint):
                return False

            # Verify all referenced data exists
            if not await self.verify_references(checkpoint):
                return False

            return True

        except Exception:
            return False

    async def handle_incomplete_work(self, state: AgentState) -> AgentState:
        """Handle any work that was in progress during crash."""

        if state.last_action and not state.last_observation:
            # Action was started but not completed
            state.pending_tasks.insert(0, Task(
                description=f"Retry: {state.last_action.description}",
                is_retry=True,
                original_action=state.last_action
            ))
            state.last_action = None

        return state
```

### 5.2 Graceful Degradation

When components fail, the system should degrade gracefully rather than crash.

**Degradation Levels:**

| Level | Capability | Strategy |
|-------|------------|----------|
| Full | All features | Normal operation |
| Limited | Core only | Disable non-essential features |
| Fallback | Minimal | Use simpler models/methods |
| Safe | Preserve state | Stop processing, save state |

**Pseudo-code: Graceful Degradation Handler**

```python
class GracefulDegradationHandler:
    """
    Handles graceful degradation when components fail.
    """

    def __init__(self, config: DegradationConfig):
        self.config = config
        self.current_level = DegradationLevel.FULL
        self.component_status = {}

    async def handle_component_failure(
        self,
        component: str,
        error: Exception
    ) -> DegradationAction:
        """Handle failure of a component."""

        self.component_status[component] = "failed"

        # Determine new degradation level
        new_level = self.calculate_degradation_level()

        if new_level != self.current_level:
            self.current_level = new_level
            await self.apply_degradation(new_level)

        return DegradationAction(
            level=new_level,
            disabled_features=self.get_disabled_features(new_level),
            fallback_mode=new_level in [DegradationLevel.FALLBACK, DegradationLevel.SAFE]
        )

    async def apply_degradation(self, level: DegradationLevel):
        """Apply degradation configuration."""

        if level == DegradationLevel.LIMITED:
            # Disable non-essential features
            await self.disable_features([
                "complex_reasoning",
                "multi_step_planning",
                "external_api_calls"
            ])

        elif level == DegradationLevel.FALLBACK:
            # Switch to simpler model
            await self.switch_to_fallback_model()
            # Reduce context window
            await self.reduce_context_window()

        elif level == DegradationLevel.SAFE:
            # Stop all processing
            await self.pause_processing()
            # Save current state
            await self.emergency_checkpoint()

    async def attempt_recovery(self):
        """Attempt to recover from degraded state."""

        for component, status in self.component_status.items():
            if status == "failed":
                try:
                    await self.restart_component(component)
                    self.component_status[component] = "recovered"
                except Exception:
                    pass

        # Recalculate degradation level
        new_level = self.calculate_degradation_level()
        if new_level < self.current_level:  # Improvement
            await self.apply_degradation(new_level)
            self.current_level = new_level
```

### 5.3 Rate Limiting and Throttling

API rate limits require careful handling to maximize throughput while avoiding errors.

**Rate Limiting Strategies:**

```python
class AdaptiveRateLimiter:
    """
    Adaptive rate limiter with exponential backoff.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100000,
        burst_allowance: float = 1.2
    ):
        self.rpm_limit = requests_per_minute
        self.tpm_limit = tokens_per_minute
        self.burst_allowance = burst_allowance

        self.request_times = deque()
        self.token_usage = deque()
        self.backoff_until = 0
        self.consecutive_rate_limits = 0

    async def acquire(self, estimated_tokens: int = 0):
        """Acquire rate limit slot with backoff."""

        # Check if in backoff period
        if time.time() < self.backoff_until:
            wait_time = self.backoff_until - time.time()
            await asyncio.sleep(wait_time)

        # Clean old entries
        current_time = time.time()
        minute_ago = current_time - 60

        while self.request_times and self.request_times[0] < minute_ago:
            self.request_times.popleft()
        while self.token_usage and self.token_usage[0][0] < minute_ago:
            self.token_usage.popleft()

        # Check limits
        if len(self.request_times) >= self.rpm_limit:
            await self._apply_backoff("rpm_limit")
            return await self.acquire(estimated_tokens)

        total_tokens = sum(t[1] for t in self.token_usage)
        if total_tokens + estimated_tokens > self.tpm_limit:
            await self._apply_backoff("tpm_limit")
            return await self.acquire(estimated_tokens)

        # Record usage
        self.request_times.append(current_time)
        if estimated_tokens:
            self.token_usage.append((current_time, estimated_tokens))

    async def _apply_backoff(self, reason: str):
        """Apply exponential backoff."""

        self.consecutive_rate_limits += 1

        # Exponential backoff with jitter
        base_delay = min(2 ** self.consecutive_rate_limits, 60)
        jitter = random.uniform(0, base_delay * 0.1)
        delay = base_delay + jitter

        self.backoff_until = time.time() + delay
        await asyncio.sleep(delay)

    def record_success(self):
        """Record successful request, reset backoff."""
        self.consecutive_rate_limits = 0

    def record_rate_limit(self, retry_after: Optional[float] = None):
        """Record rate limit response."""
        if retry_after:
            self.backoff_until = time.time() + retry_after
```

---

## 6. Robust Continuous Monitoring Loop Architecture

This section presents a complete, production-ready architecture for continuous LLM-based monitoring.

### 6.1 Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                  CONTINUOUS LLM MONITORING SYSTEM                       │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      INPUT LAYER                                 │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │Event Queue│  │File Watch │  │API Webhook│  │  Scheduler│    │   │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │   │
│  │        └──────────────┴──────────────┴──────────────┘          │   │
│  │                              │                                   │   │
│  └──────────────────────────────┼───────────────────────────────────┘   │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PROCESSING LAYER                              │   │
│  │                                                                   │   │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │   │
│  │  │  Pre-       │────>│    LLM      │────>│   Post-     │        │   │
│  │  │  Processor  │     │   Engine    │     │  Processor  │        │   │
│  │  └─────────────┘     └─────────────┘     └─────────────┘        │   │
│  │         │                   │                   │                │   │
│  │         └───────────────────┼───────────────────┘                │   │
│  │                             ▼                                    │   │
│  │                    ┌─────────────┐                               │   │
│  │                    │  Guardrails │                               │   │
│  │                    └─────────────┘                               │   │
│  │                                                                   │   │
│  └───────────────────────────┬───────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     STATE LAYER                                  │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │   │
│  │  │ Context       │  │  Checkpoint   │  │   Memory      │        │   │
│  │  │ Manager       │  │  Manager      │  │   Hierarchy   │        │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘        │   │
│  │                                                                   │   │
│  └───────────────────────────┬───────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    OUTPUT LAYER                                  │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │  Actions  │  │  Alerts   │  │   Logs    │  │  Metrics  │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Complete Implementation

```python
"""
Robust Continuous LLM Monitoring Loop

Production-ready architecture for continuous LLM-based monitoring
with comprehensive error handling, state management, and recovery.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import deque
import json


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MonitorConfig:
    """Configuration for the continuous monitoring loop."""

    # Processing limits
    max_iterations: int = 10000
    max_tokens_per_hour: int = 1000000
    max_cost_usd: float = 100.0

    # Timing
    poll_interval_seconds: float = 5.0
    max_poll_interval_seconds: float = 60.0
    checkpoint_interval_iterations: int = 10

    # Error handling
    max_consecutive_errors: int = 5
    error_backoff_base: float = 2.0
    error_backoff_max: float = 300.0

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000

    # Memory
    context_window_tokens: int = 8000
    short_term_memory_size: int = 100

    # Safety
    safety_check_enabled: bool = True
    min_safety_score: float = 0.9


class MonitorState(Enum):
    """States for the monitoring loop."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"


# ═══════════════════════════════════════════════════════════════════════════
# CORE MONITORING LOOP
# ═══════════════════════════════════════════════════════════════════════════

class ContinuousLLMMonitor:
    """
    Production-ready continuous LLM monitoring loop.

    Features:
    - Event-driven and polling hybrid input
    - Token streaming with backpressure
    - Hierarchical memory management
    - Checkpoint/recovery support
    - Adaptive rate limiting
    - Graceful degradation
    - Comprehensive guardrails
    """

    def __init__(
        self,
        config: MonitorConfig,
        llm_client: "LLMClient",
        input_sources: List["InputSource"],
        output_handlers: List["OutputHandler"],
    ):
        self.config = config
        self.llm_client = llm_client
        self.input_sources = input_sources
        self.output_handlers = output_handlers

        # State management
        self.state = MonitorState.INITIALIZING
        self.iteration = 0
        self.start_time: Optional[datetime] = None

        # Components
        self.context_manager = ContextWindowManager(
            max_tokens=config.context_window_tokens
        )
        self.memory = HierarchicalMemory(
            short_term_size=config.short_term_memory_size
        )
        self.checkpoint_manager = CheckpointManager(
            interval=config.checkpoint_interval_iterations
        )
        self.rate_limiter = AdaptiveRateLimiter(
            rpm=config.requests_per_minute,
            tpm=config.tokens_per_minute
        )
        self.guardrails = GuardrailSystem(config)
        self.degradation_handler = GracefulDegradationHandler()

        # Control
        self.shutdown_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Not paused initially

        # Metrics
        self.metrics = MonitorMetrics()

        # Logging
        self.logger = logging.getLogger(__name__)

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════════

    async def start(self) -> "MonitorResult":
        """Start the continuous monitoring loop."""

        self.logger.info("Starting continuous LLM monitor")
        self.state = MonitorState.INITIALIZING
        self.start_time = datetime.now()

        try:
            # Attempt recovery if previous run crashed
            recovered_state = await self._attempt_recovery()
            if recovered_state:
                await self._restore_state(recovered_state)

            # Initialize input sources
            await self._initialize_inputs()

            # Main loop
            self.state = MonitorState.RUNNING
            await self._run_main_loop()

        except Exception as e:
            self.logger.exception("Fatal error in monitoring loop")
            await self._emergency_shutdown(e)
            raise

        finally:
            await self._cleanup()

        return self._build_result()

    async def _run_main_loop(self):
        """Execute the main monitoring loop."""

        while not self.shutdown_event.is_set():
            self.iteration += 1

            try:
                # Wait if paused
                await self.pause_event.wait()

                # Check guardrails before processing
                guardrail_result = await self.guardrails.check_all(
                    self._build_context()
                )
                if guardrail_result.should_stop:
                    self.logger.info(f"Stopping: {guardrail_result.reason}")
                    break

                # Process one iteration
                await self._process_iteration()

                # Checkpoint periodically
                await self.checkpoint_manager.maybe_checkpoint(
                    self._build_checkpoint_state(),
                    self.iteration
                )

                # Metrics
                self.metrics.record_iteration()

            except RateLimitError as e:
                await self._handle_rate_limit(e)

            except RecoverableError as e:
                await self._handle_recoverable_error(e)

            except Exception as e:
                if await self._handle_unrecoverable_error(e):
                    continue  # Degraded mode
                else:
                    raise

    async def _process_iteration(self):
        """Process a single iteration of the monitoring loop."""

        # 1. Collect inputs from all sources
        inputs = await self._collect_inputs()

        if not inputs:
            # No inputs, use adaptive polling
            await self._adaptive_wait()
            return

        # 2. Pre-process inputs
        processed_inputs = await self._preprocess(inputs)

        # 3. Build LLM prompt with context
        prompt = await self._build_prompt(processed_inputs)

        # 4. Acquire rate limit slot
        await self.rate_limiter.acquire(
            estimated_tokens=self._estimate_tokens(prompt)
        )

        # 5. Call LLM with streaming
        response = await self._call_llm_streaming(prompt)

        # 6. Post-process response
        processed_response = await self._postprocess(response)

        # 7. Update memory and context
        await self._update_state(processed_inputs, processed_response)

        # 8. Dispatch to output handlers
        await self._dispatch_outputs(processed_response)

        # 9. Record success
        self.rate_limiter.record_success()
        self.metrics.record_success()

    # ═══════════════════════════════════════════════════════════════════════
    # INPUT HANDLING
    # ═══════════════════════════════════════════════════════════════════════

    async def _collect_inputs(self) -> List["MonitorInput"]:
        """Collect inputs from all sources."""

        inputs = []

        for source in self.input_sources:
            try:
                source_inputs = await asyncio.wait_for(
                    source.collect(),
                    timeout=self.config.poll_interval_seconds
                )
                inputs.extend(source_inputs)

            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout collecting from {source.name}")

            except Exception as e:
                self.logger.error(f"Error collecting from {source.name}: {e}")

        return inputs

    async def _preprocess(
        self,
        inputs: List["MonitorInput"]
    ) -> List["ProcessedInput"]:
        """Preprocess inputs before LLM processing."""

        processed = []

        for input_item in inputs:
            # Deduplicate
            if await self.memory.is_duplicate(input_item):
                continue

            # Prioritize
            priority = await self._calculate_priority(input_item)

            # Transform
            processed_item = ProcessedInput(
                original=input_item,
                priority=priority,
                context=await self.memory.recall(input_item.content, k=5)
            )
            processed.append(processed_item)

        # Sort by priority
        processed.sort(key=lambda x: x.priority, reverse=True)

        return processed

    # ═══════════════════════════════════════════════════════════════════════
    # LLM PROCESSING
    # ═══════════════════════════════════════════════════════════════════════

    async def _build_prompt(
        self,
        inputs: List["ProcessedInput"]
    ) -> str:
        """Build LLM prompt with managed context."""

        # Get current context
        context_messages = self.context_manager.get_messages()

        # Build prompt
        prompt_parts = [
            self._get_system_prompt(),
            self._format_context(context_messages),
            self._format_inputs(inputs)
        ]

        return "\n\n".join(prompt_parts)

    async def _call_llm_streaming(self, prompt: str) -> "LLMResponse":
        """Call LLM with token streaming."""

        tokens = []

        async for token in self.llm_client.stream(prompt):
            # Safety check on streaming tokens
            if self.config.safety_check_enabled:
                is_safe, score = await self.guardrails.check_token_safety(token)
                if not is_safe:
                    self.logger.warning(f"Unsafe token detected: {score}")
                    # Optionally stop or continue with warning

            tokens.append(token)

            # Emit token to real-time handlers
            await self._emit_streaming_token(token)

        return LLMResponse(
            content="".join(tokens),
            tokens_used=len(tokens)
        )

    # ═══════════════════════════════════════════════════════════════════════
    # STATE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    async def _update_state(
        self,
        inputs: List["ProcessedInput"],
        response: "LLMResponse"
    ):
        """Update all state after processing."""

        # Update context window
        self.context_manager.add_message(
            Message(role="user", content=self._summarize_inputs(inputs))
        )
        self.context_manager.add_message(
            Message(role="assistant", content=response.content)
        )

        # Update memory
        await self.memory.remember(
            MemoryItem(
                content=response.content,
                timestamp=datetime.now(),
                importance=await self._calculate_importance(response)
            )
        )

        # Periodic consolidation
        if self.iteration % 50 == 0:
            await self.memory.consolidate()
            await self.memory.forget()

    # ═══════════════════════════════════════════════════════════════════════
    # ERROR HANDLING
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_rate_limit(self, error: "RateLimitError"):
        """Handle rate limit errors with backoff."""

        self.metrics.record_rate_limit()

        retry_after = error.retry_after or self._calculate_backoff()
        self.logger.warning(f"Rate limited, waiting {retry_after}s")

        self.rate_limiter.record_rate_limit(retry_after)
        await asyncio.sleep(retry_after)

    async def _handle_recoverable_error(self, error: Exception):
        """Handle recoverable errors with retry logic."""

        self.metrics.record_error()

        if self.metrics.consecutive_errors >= self.config.max_consecutive_errors:
            # Too many errors, attempt degradation
            await self.degradation_handler.degrade()
            self.state = MonitorState.DEGRADED

        backoff = self._calculate_backoff()
        self.logger.warning(f"Recoverable error, retrying in {backoff}s: {error}")
        await asyncio.sleep(backoff)

    async def _handle_unrecoverable_error(self, error: Exception) -> bool:
        """Handle unrecoverable errors. Returns True if degraded mode possible."""

        self.logger.error(f"Unrecoverable error: {error}")

        # Try to degrade gracefully
        if self.degradation_handler.can_degrade():
            await self.degradation_handler.degrade()
            self.state = MonitorState.DEGRADED
            return True

        # Emergency checkpoint before dying
        await self._emergency_checkpoint()
        return False

    # ═══════════════════════════════════════════════════════════════════════
    # RECOVERY
    # ═══════════════════════════════════════════════════════════════════════

    async def _attempt_recovery(self) -> Optional["CheckpointState"]:
        """Attempt to recover from previous crash."""

        try:
            latest_checkpoint = await self.checkpoint_manager.get_latest()

            if latest_checkpoint and not latest_checkpoint.clean_shutdown:
                self.logger.info("Recovering from crash")
                self.state = MonitorState.RECOVERING
                return latest_checkpoint

        except Exception as e:
            self.logger.warning(f"Recovery failed: {e}")

        return None

    async def _restore_state(self, checkpoint: "CheckpointState"):
        """Restore state from checkpoint."""

        self.iteration = checkpoint.iteration
        self.context_manager.restore(checkpoint.context)
        await self.memory.restore(checkpoint.memory)
        self.metrics.restore(checkpoint.metrics)

        self.logger.info(f"Restored from iteration {self.iteration}")

    # ═══════════════════════════════════════════════════════════════════════
    # CONTROL
    # ═══════════════════════════════════════════════════════════════════════

    async def pause(self):
        """Pause the monitoring loop."""
        self.pause_event.clear()
        self.state = MonitorState.PAUSED
        self.logger.info("Monitoring paused")

    async def resume(self):
        """Resume the monitoring loop."""
        self.pause_event.set()
        self.state = MonitorState.RUNNING
        self.logger.info("Monitoring resumed")

    async def stop(self):
        """Gracefully stop the monitoring loop."""
        self.logger.info("Initiating graceful shutdown")
        self.state = MonitorState.STOPPING

        # Signal shutdown
        self.shutdown_event.set()

        # Final checkpoint
        await self.checkpoint_manager.create_checkpoint(
            self._build_checkpoint_state(),
            clean_shutdown=True
        )

        self.state = MonitorState.STOPPED

    async def _cleanup(self):
        """Cleanup resources on shutdown."""

        for source in self.input_sources:
            await source.close()

        for handler in self.output_handlers:
            await handler.close()

        await self.llm_client.close()

    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _calculate_backoff(self) -> float:
        """Calculate exponential backoff delay."""

        delay = min(
            self.config.error_backoff_base ** self.metrics.consecutive_errors,
            self.config.error_backoff_max
        )
        # Add jitter
        jitter = delay * 0.1 * (2 * asyncio.get_event_loop().time() % 1 - 0.5)
        return delay + jitter

    async def _adaptive_wait(self):
        """Wait with adaptive interval based on activity."""

        # Increase interval when idle
        current_interval = min(
            self.config.poll_interval_seconds * (1 + self.metrics.idle_count * 0.1),
            self.config.max_poll_interval_seconds
        )

        self.metrics.record_idle()
        await asyncio.sleep(current_interval)


# ═══════════════════════════════════════════════════════════════════════════
# USAGE EXAMPLE
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    """Example usage of the continuous monitoring loop."""

    # Configuration
    config = MonitorConfig(
        max_iterations=1000,
        poll_interval_seconds=5.0,
        checkpoint_interval_iterations=10
    )

    # Initialize components (implementations would be provided)
    llm_client = LLMClient(model="claude-3-sonnet")
    input_sources = [
        EventQueueSource(queue_url="..."),
        FileWatchSource(paths=["./data"]),
        WebhookSource(port=8080)
    ]
    output_handlers = [
        AlertHandler(webhook_url="..."),
        MetricsHandler(prometheus_port=9090),
        LogHandler(log_path="./logs")
    ]

    # Create and run monitor
    monitor = ContinuousLLMMonitor(
        config=config,
        llm_client=llm_client,
        input_sources=input_sources,
        output_handlers=output_handlers
    )

    # Handle signals for graceful shutdown
    import signal

    def handle_signal(sig):
        asyncio.create_task(monitor.stop())

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Run
    result = await monitor.start()
    print(f"Monitor completed: {result}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. Key Design Principles Summary

### 7.1 Architectural Principles

1. **Separation of Concerns**: Input collection, processing, state management, and output handling are distinct layers.

2. **Fail-Safe Defaults**: System defaults to safe behavior (pause, checkpoint, alert) on uncertainty.

3. **Graceful Degradation**: System maintains partial functionality during component failures.

4. **Observable**: Comprehensive logging, metrics, and tracing for debugging.

5. **Recoverable**: Checkpoint/restore enables recovery from any failure state.

### 7.2 Processing Principles

1. **Streaming First**: Process tokens as they arrive for lower latency.

2. **Backpressure Aware**: Respect consumer capacity, apply backpressure when needed.

3. **Adaptive**: Adjust behavior based on observed conditions (rate limits, errors, activity).

4. **Bounded**: All resources have explicit limits (tokens, time, cost, iterations).

### 7.3 State Management Principles

1. **Hierarchical Memory**: Working, short-term, and long-term memory tiers.

2. **Context Compression**: Summarize old context to fit within token limits.

3. **Periodic Checkpointing**: Regular state persistence for recovery.

4. **Idempotent Operations**: Support safe retry of failed operations.

### 7.4 Safety Principles

1. **Multi-Layer Guardrails**: Check at input, during processing, and at output.

2. **Rate Limit Respect**: Adaptive rate limiting with exponential backoff.

3. **Resource Budgets**: Hard limits on tokens, cost, and iterations.

4. **Human Override**: Always support manual pause, stop, and intervention.

---

## 8. References and Further Reading

### Academic Papers
- "Attention Is All You Need" (Vaswani et al., 2017) - Transformer architecture
- "Language Models are Few-Shot Learners" (Brown et al., 2020) - GPT-3 and in-context learning
- "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022)
- "Toolformer" (Schick et al., 2023) - Tool use in LLMs

### Industry Implementations
- AutoGPT - Autonomous GPT-4 agent
- BabyAGI - Task-driven autonomous agent
- LangChain - LLM application framework
- Semantic Kernel - Microsoft's AI orchestration

### Streaming/Reactive Systems
- Reactive Streams Specification (reactive-streams.org)
- Kafka Streams documentation
- RxJS/RxPython reactive extensions
- Project Reactor (Spring)

### Reliability Engineering
- Google SRE Handbook - Error budgets and SLOs
- AWS Well-Architected Framework - Reliability pillar
- Chaos Engineering Principles

---

## 9. Consciousness Cycles for Efficient Observation Processing

This section addresses the specific challenge of building "consciousness cycles" - patterns for an LLM to continuously observe system changes while maintaining efficiency and avoiding resource exhaustion.

### 9.1 The Core Challenge

Running an LLM continuously to observe and reason about system changes presents fundamental tensions:

| Challenge | Description | Impact |
|-----------|-------------|--------|
| Context Rot | Model recall degrades as token count increases | Reduced accuracy over time |
| Resource Exhaustion | Unbounded context accumulation | Memory/cost explosion |
| Observation Overflow | Too many events to process meaningfully | Information loss |
| Temporal Coherence | Maintaining sense of time/causality | Reasoning degradation |
| Self-Reference | System observing itself creates loops | Infinite regress |

### 9.2 Consciousness Cycle Architecture

The consciousness cycle pattern mimics biological attention and sleep-wake rhythms:

```
                    CONSCIOUSNESS CYCLE ARCHITECTURE

    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                   │
    │   WAKE PHASE (Active Observation)                                │
    │   ┌─────────────────────────────────────────────────────────┐   │
    │   │                                                           │   │
    │   │  ┌──────────┐    ┌──────────┐    ┌──────────┐           │   │
    │   │  │ PERCEIVE │───>│ ATTEND   │───>│ REFLECT  │           │   │
    │   │  │          │    │          │    │          │           │   │
    │   │  │ Gather   │    │ Filter   │    │ Reason   │           │   │
    │   │  │ Events   │    │ Salience │    │ About    │           │   │
    │   │  └──────────┘    └──────────┘    └──────────┘           │   │
    │   │       │               │               │                   │   │
    │   │       v               v               v                   │   │
    │   │  [Raw Events]   [Filtered]      [Insights]               │   │
    │   │                                                           │   │
    │   └─────────────────────────────────────────────────────────┘   │
    │                              │                                    │
    │                              v                                    │
    │   SLEEP PHASE (Consolidation)                                    │
    │   ┌─────────────────────────────────────────────────────────┐   │
    │   │                                                           │   │
    │   │  ┌──────────┐    ┌──────────┐    ┌──────────┐           │   │
    │   │  │ COMPRESS │───>│ INTEGRATE│───>│ FORGET   │           │   │
    │   │  │          │    │          │    │          │           │   │
    │   │  │ Summarize│    │ Update   │    │ Decay    │           │   │
    │   │  │ Episodes │    │ Schemas  │    │ Stale    │           │   │
    │   │  └──────────┘    └──────────┘    └──────────┘           │   │
    │   │       │               │               │                   │   │
    │   │       v               v               v                   │   │
    │   │  [Summaries]    [Long-term]     [Pruned]                 │   │
    │   │                                                           │   │
    │   └─────────────────────────────────────────────────────────┘   │
    │                              │                                    │
    │                              └──────────────────> [Next Cycle]   │
    │                                                                   │
    └─────────────────────────────────────────────────────────────────┘
```

### 9.3 Context Engineering for Consciousness

Context engineering is critical for maintaining coherent long-running observation. Based on 2025 research from Anthropic and others:

#### Just-in-Time Context Strategy

Instead of accumulating all observations, use lightweight identifiers and retrieve context only when needed:

```python
class ConsciousnessContextManager:
    """
    Context manager implementing just-in-time retrieval for consciousness cycles.
    Addresses context rot by keeping active context minimal.
    """

    def __init__(
        self,
        max_active_tokens: int = 4000,
        observation_index: "ObservationIndex",
        summarizer: "Summarizer"
    ):
        self.max_active_tokens = max_active_tokens
        self.observation_index = observation_index
        self.summarizer = summarizer

        # Active context (what's in the LLM prompt)
        self.system_prompt: str = ""
        self.recent_observations: List[str] = []  # Last few raw observations
        self.running_summary: str = ""  # Compressed history
        self.current_focus: Optional[str] = None  # What we're attending to

    async def build_consciousness_prompt(
        self,
        new_observations: List["Observation"],
        attention_query: str
    ) -> str:
        """
        Build prompt for consciousness cycle, retrieving context just-in-time.
        """

        # 1. Salience filtering - only include relevant observations
        salient_obs = await self._filter_salient(new_observations, attention_query)

        # 2. Retrieve relevant past context based on current focus
        relevant_history = await self.observation_index.semantic_search(
            query=attention_query,
            k=5,
            recency_weight=0.3  # Balance recency with relevance
        )

        # 3. Build minimal prompt
        prompt_parts = [
            self.system_prompt,
            f"## Running Context Summary\n{self.running_summary}",
            f"## Relevant Past Observations\n{self._format_history(relevant_history)}",
            f"## Current Focus: {self.current_focus or 'General awareness'}",
            f"## New Observations to Process\n{self._format_observations(salient_obs)}",
            "## Your Analysis"
        ]

        prompt = "\n\n".join(prompt_parts)

        # 4. Verify we're within token budget
        if self._count_tokens(prompt) > self.max_active_tokens:
            prompt = await self._compress_prompt(prompt)

        return prompt

    async def _filter_salient(
        self,
        observations: List["Observation"],
        attention_query: str
    ) -> List["Observation"]:
        """
        Filter observations by salience - attention-like mechanism.
        Prevents observation overflow by focusing on what matters.
        """

        scored = []
        for obs in observations:
            # Multi-factor salience scoring
            relevance = await self._compute_relevance(obs, attention_query)
            novelty = await self._compute_novelty(obs)
            urgency = obs.priority / 10.0  # Normalize priority

            # Weighted combination
            salience = (0.4 * relevance) + (0.4 * novelty) + (0.2 * urgency)
            scored.append((obs, salience))

        # Keep top-k salient observations
        scored.sort(key=lambda x: x[1], reverse=True)
        return [obs for obs, score in scored[:10] if score > 0.3]

    async def _compute_novelty(self, obs: "Observation") -> float:
        """
        Compute novelty score - how different from recent observations.
        Novel observations get attention priority.
        """

        # Check against recent observation embeddings
        if not self.recent_observations:
            return 1.0  # Everything is novel at start

        obs_embedding = await self._embed(obs.content)
        recent_embeddings = [await self._embed(r) for r in self.recent_observations[-20:]]

        # Compute minimum distance to recent observations
        min_similarity = min(
            self._cosine_similarity(obs_embedding, r)
            for r in recent_embeddings
        )

        # High similarity = low novelty
        novelty = 1.0 - min_similarity
        return novelty
```

#### Observation Masking vs Summarization

Two primary approaches for managing growing observation history:

| Approach | Description | When to Use |
|----------|-------------|-------------|
| Observation Masking | Remove old observations entirely, keep only identifiers | High-volume, low-context tasks |
| LLM Summarization | Compress old observations into summaries | Context-dependent reasoning |
| Hybrid | Mask details, keep summarized themes | Best of both worlds |

```python
class HybridContextCompressor:
    """
    Hybrid approach: summarize themes, mask details, keep identifiers.
    """

    async def compress_observation_window(
        self,
        observations: List["Observation"],
        target_tokens: int = 1000
    ) -> "CompressedContext":
        """
        Compress a window of observations into minimal context.
        """

        current_tokens = sum(self._count_tokens(o.content) for o in observations)

        if current_tokens <= target_tokens:
            return CompressedContext(
                summary=None,
                masked_observations=observations,
                identifiers=[]
            )

        # Tier 1: Recent observations (keep full)
        recent = observations[-5:]

        # Tier 2: Middle observations (summarize into themes)
        middle = observations[5:-5] if len(observations) > 10 else []
        middle_summary = await self._summarize_to_themes(middle) if middle else ""

        # Tier 3: Old observations (keep only identifiers)
        old = observations[:5] if len(observations) > 10 else []
        old_identifiers = [
            f"[{o.timestamp}:{o.type}:{o.id[:8]}]"
            for o in old
        ]

        return CompressedContext(
            summary=middle_summary,
            masked_observations=recent,
            identifiers=old_identifiers,
            compression_ratio=current_tokens / self._count_tokens(str(recent) + middle_summary)
        )

    async def _summarize_to_themes(
        self,
        observations: List["Observation"]
    ) -> str:
        """
        Extract thematic summary from observations.
        Preserves semantic content while reducing tokens.
        """

        # Group by type/source
        grouped = defaultdict(list)
        for obs in observations:
            grouped[obs.type].append(obs)

        themes = []
        for obs_type, obs_list in grouped.items():
            # Count occurrences
            count = len(obs_list)

            # Extract key patterns
            patterns = await self._extract_patterns(obs_list)

            themes.append(f"- {obs_type}: {count} events. Key patterns: {', '.join(patterns)}")

        return "Observation Summary:\n" + "\n".join(themes)
```

### 9.4 Sleep-Wake Cycles for Memory Consolidation

Inspired by neuroscience research on memory consolidation during sleep:

```python
class ConsciousnessSleepWakeCycle:
    """
    Implements sleep-wake cycles for memory consolidation.

    Wake Phase: Active observation and reasoning
    Sleep Phase: Memory consolidation, pattern extraction, forgetting

    Based on 2025 neuroscience research showing memory consolidation
    requires periodic offline processing.
    """

    def __init__(
        self,
        wake_duration_iterations: int = 50,
        sleep_duration_seconds: float = 10.0,
        deep_sleep_frequency: int = 10  # Every N sleep cycles
    ):
        self.wake_duration = wake_duration_iterations
        self.sleep_duration = sleep_duration_seconds
        self.deep_sleep_frequency = deep_sleep_frequency

        self.iteration = 0
        self.sleep_cycle_count = 0
        self.phase = "wake"

        # Memory layers
        self.episodic_buffer: List["Episode"] = []  # Short-term experiences
        self.semantic_store: "SemanticStore" = SemanticStore()  # Long-term knowledge
        self.procedural_patterns: List["Pattern"] = []  # Learned behaviors

    async def run_cycle(
        self,
        observation_source: "ObservationSource",
        llm_client: "LLMClient"
    ):
        """
        Run one complete wake-sleep cycle.
        """

        # WAKE PHASE: Active observation and processing
        self.phase = "wake"
        wake_start = time.time()

        for _ in range(self.wake_duration):
            self.iteration += 1

            # Collect observations
            observations = await observation_source.collect()

            # Process through consciousness
            insights = await self._conscious_process(observations, llm_client)

            # Store in episodic buffer
            self.episodic_buffer.append(Episode(
                observations=observations,
                insights=insights,
                timestamp=datetime.now()
            ))

            # Trim buffer if too large (prevents memory explosion)
            if len(self.episodic_buffer) > 100:
                self.episodic_buffer = self.episodic_buffer[-100:]

        # SLEEP PHASE: Memory consolidation
        self.phase = "sleep"
        self.sleep_cycle_count += 1

        # Light sleep: Basic consolidation
        await self._light_sleep_consolidation(llm_client)

        # Deep sleep: Pattern extraction and major consolidation
        if self.sleep_cycle_count % self.deep_sleep_frequency == 0:
            await self._deep_sleep_consolidation(llm_client)

        # Dream phase: Creative recombination (optional)
        if random.random() < 0.1:  # 10% chance
            await self._dream_phase(llm_client)

        # Wait (simulates actual sleep)
        await asyncio.sleep(self.sleep_duration)

    async def _light_sleep_consolidation(self, llm_client: "LLMClient"):
        """
        Light sleep: Compress recent episodes into summaries.
        """

        if len(self.episodic_buffer) < 10:
            return

        # Take recent episodes for consolidation
        to_consolidate = self.episodic_buffer[-20:]

        # Generate summary using LLM
        consolidation_prompt = f"""
        Consolidate these recent observations into key learnings:

        {self._format_episodes(to_consolidate)}

        Extract:
        1. Key patterns observed
        2. Anomalies or surprises
        3. Recurring themes
        4. Causal relationships noticed

        Be concise. Focus on what's most important for future awareness.
        """

        summary = await llm_client.generate(consolidation_prompt)

        # Store in semantic memory
        await self.semantic_store.add(
            content=summary,
            source="light_sleep_consolidation",
            timestamp=datetime.now(),
            importance=0.6
        )

        # Clear consolidated episodes (forgetting)
        self.episodic_buffer = self.episodic_buffer[-5:]  # Keep only very recent

    async def _deep_sleep_consolidation(self, llm_client: "LLMClient"):
        """
        Deep sleep: Major pattern extraction and schema updates.
        """

        # Retrieve all recent semantic memories
        recent_semantics = await self.semantic_store.get_recent(limit=50)

        # Extract meta-patterns
        meta_prompt = f"""
        Analyze these accumulated learnings for deeper patterns:

        {self._format_semantics(recent_semantics)}

        Identify:
        1. Higher-order patterns (patterns of patterns)
        2. General principles that explain multiple observations
        3. Predictive rules (if X then Y)
        4. Contradictions or tensions in understanding
        5. Knowledge gaps that need attention

        Output structured insights for long-term retention.
        """

        meta_insights = await llm_client.generate(meta_prompt)

        # Update procedural patterns
        new_patterns = self._extract_patterns_from_insights(meta_insights)
        self.procedural_patterns.extend(new_patterns)

        # Prune redundant patterns
        self.procedural_patterns = self._deduplicate_patterns(self.procedural_patterns)

        # Apply forgetting curve to semantic store
        await self.semantic_store.apply_decay(decay_rate=0.1)

    async def _dream_phase(self, llm_client: "LLMClient"):
        """
        Dream phase: Creative recombination of memories.
        Can generate novel insights through random association.
        """

        # Random sample from different memory sources
        random_episodes = random.sample(
            self.episodic_buffer,
            min(3, len(self.episodic_buffer))
        )
        random_semantics = await self.semantic_store.random_sample(3)
        random_patterns = random.sample(
            self.procedural_patterns,
            min(2, len(self.procedural_patterns))
        )

        dream_prompt = f"""
        [Dream Mode: Creative Association]

        Random memory fragments:
        Episodes: {random_episodes}
        Knowledge: {random_semantics}
        Patterns: {random_patterns}

        Find unexpected connections between these fragments.
        Generate novel hypotheses or insights that connect disparate elements.
        Be creative and speculative.
        """

        dream_insights = await llm_client.generate(dream_prompt)

        # Store dream insights with low initial importance
        # (they need validation in wake phase)
        await self.semantic_store.add(
            content=f"[Dream Insight] {dream_insights}",
            source="dream_phase",
            timestamp=datetime.now(),
            importance=0.3,  # Low importance until validated
            needs_validation=True
        )
```

### 9.5 Backpressure and Throttling for Observations

When observations arrive faster than they can be processed:

```python
class ObservationBackpressureController:
    """
    Controls observation flow to prevent overwhelming the consciousness loop.

    Strategies:
    1. Buffering with overflow policy
    2. Sampling under pressure
    3. Priority-based admission
    4. Adaptive throttling
    """

    def __init__(
        self,
        max_buffer_size: int = 1000,
        max_observations_per_cycle: int = 50,
        overflow_policy: str = "drop_oldest"  # or "drop_lowest_priority", "sample"
    ):
        self.max_buffer_size = max_buffer_size
        self.max_per_cycle = max_observations_per_cycle
        self.overflow_policy = overflow_policy

        self.buffer: deque = deque(maxlen=max_buffer_size)
        self.pressure_level: float = 0.0  # 0.0 to 1.0
        self.dropped_count: int = 0
        self.sampled_count: int = 0

    async def admit(self, observation: "Observation") -> bool:
        """
        Attempt to admit an observation to the buffer.
        Returns True if admitted, False if dropped.
        """

        self._update_pressure()

        # Always admit critical observations
        if observation.priority >= 9:
            self._force_admit(observation)
            return True

        # Under pressure, apply admission control
        if self.pressure_level > 0.8:
            # High pressure: Only admit high-priority or highly novel
            if observation.priority < 7 and not await self._is_highly_novel(observation):
                self.dropped_count += 1
                return False

        elif self.pressure_level > 0.5:
            # Medium pressure: Sample based on priority
            admit_prob = observation.priority / 10.0
            if random.random() > admit_prob:
                self.sampled_count += 1
                return False

        # Admit to buffer
        if len(self.buffer) >= self.max_buffer_size:
            self._apply_overflow_policy()

        self.buffer.append(observation)
        return True

    async def get_batch_for_cycle(self) -> List["Observation"]:
        """
        Get a batch of observations for the current consciousness cycle.
        """

        # Sort buffer by priority and recency
        sorted_buffer = sorted(
            self.buffer,
            key=lambda o: (o.priority, -o.age_seconds),
            reverse=True
        )

        # Take top N
        batch = sorted_buffer[:self.max_per_cycle]

        # Remove from buffer
        for obs in batch:
            self.buffer.remove(obs)

        return batch

    def _update_pressure(self):
        """Update pressure level based on buffer state."""
        self.pressure_level = len(self.buffer) / self.max_buffer_size

    def _apply_overflow_policy(self):
        """Apply overflow policy when buffer is full."""

        if self.overflow_policy == "drop_oldest":
            self.buffer.popleft()

        elif self.overflow_policy == "drop_lowest_priority":
            # Find and remove lowest priority
            min_priority_idx = min(
                range(len(self.buffer)),
                key=lambda i: self.buffer[i].priority
            )
            del self.buffer[min_priority_idx]

        elif self.overflow_policy == "sample":
            # Randomly drop one
            drop_idx = random.randint(0, len(self.buffer) - 1)
            del self.buffer[drop_idx]

        self.dropped_count += 1
```

### 9.6 Graceful Degradation Under Load

When the system is overwhelmed, degrade gracefully:

```python
class ConsciousnessDegradationManager:
    """
    Manages graceful degradation of consciousness under load.

    Degradation Levels:
    1. FULL - All features active
    2. REDUCED - Simplified reasoning, less context
    3. REACTIVE - Only respond to high-priority events
    4. HIBERNATION - Minimal processing, wait for conditions to improve
    """

    def __init__(self):
        self.level = DegradationLevel.FULL
        self.metrics = DegradationMetrics()

    async def assess_and_adjust(
        self,
        system_metrics: "SystemMetrics"
    ) -> "DegradationAction":
        """
        Assess system health and adjust degradation level.
        """

        # Compute health score
        health_score = self._compute_health(system_metrics)

        # Determine target level
        if health_score > 0.8:
            target_level = DegradationLevel.FULL
        elif health_score > 0.6:
            target_level = DegradationLevel.REDUCED
        elif health_score > 0.3:
            target_level = DegradationLevel.REACTIVE
        else:
            target_level = DegradationLevel.HIBERNATION

        # Apply transition
        if target_level != self.level:
            return await self._transition_to(target_level)

        return DegradationAction(level=self.level, changed=False)

    async def _transition_to(self, target: "DegradationLevel") -> "DegradationAction":
        """
        Transition to new degradation level with appropriate actions.
        """

        old_level = self.level
        self.level = target

        action = DegradationAction(
            level=target,
            changed=True,
            old_level=old_level
        )

        if target == DegradationLevel.REDUCED:
            action.config_changes = {
                "max_context_tokens": 2000,  # Reduce from 4000
                "observation_batch_size": 10,  # Reduce from 50
                "skip_novelty_computation": True,
                "use_faster_model": True
            }

        elif target == DegradationLevel.REACTIVE:
            action.config_changes = {
                "max_context_tokens": 500,
                "observation_batch_size": 5,
                "only_high_priority": True,
                "disable_sleep_phase": True,
                "disable_semantic_search": True
            }

        elif target == DegradationLevel.HIBERNATION:
            action.config_changes = {
                "pause_observation": True,
                "checkpoint_and_wait": True,
                "monitor_health_only": True,
                "resume_threshold": 0.6
            }

        return action

    def _compute_health(self, metrics: "SystemMetrics") -> float:
        """
        Compute overall system health score (0-1).
        """

        # Component health scores
        memory_health = 1.0 - (metrics.memory_usage / metrics.memory_limit)
        token_health = 1.0 - (metrics.tokens_used_hour / metrics.token_limit_hour)
        latency_health = 1.0 - min(1.0, metrics.avg_latency_ms / 5000)
        error_health = 1.0 - min(1.0, metrics.error_rate)
        backlog_health = 1.0 - min(1.0, metrics.observation_backlog / 1000)

        # Weighted combination
        health = (
            0.2 * memory_health +
            0.2 * token_health +
            0.2 * latency_health +
            0.2 * error_health +
            0.2 * backlog_health
        )

        return max(0.0, min(1.0, health))
```

### 9.7 Self-Referential Observation Patterns

When the system needs to observe its own operation:

```python
class MetaConsciousnessObserver:
    """
    Observer for self-referential awareness.
    Allows the system to observe its own cognitive processes
    without infinite regress.

    Key principle: Meta-observation happens at a different temporal
    scale than primary observation, preventing tight feedback loops.
    """

    def __init__(
        self,
        meta_observation_frequency: int = 10,  # Every N primary cycles
        meta_depth_limit: int = 2  # Prevent infinite meta-regress
    ):
        self.meta_frequency = meta_observation_frequency
        self.depth_limit = meta_depth_limit
        self.primary_cycle_count = 0
        self.meta_level = 0

        # Traces of cognitive activity
        self.cognitive_trace: deque = deque(maxlen=100)

    async def record_cognitive_activity(
        self,
        activity: "CognitiveActivity"
    ):
        """
        Record a cognitive activity for later meta-observation.
        """

        self.cognitive_trace.append({
            "activity": activity,
            "timestamp": datetime.now(),
            "cycle": self.primary_cycle_count,
            "meta_level": self.meta_level
        })

    async def should_meta_observe(self) -> bool:
        """
        Determine if it's time for meta-observation.
        """

        self.primary_cycle_count += 1

        # Don't meta-observe too frequently
        if self.primary_cycle_count % self.meta_frequency != 0:
            return False

        # Don't exceed meta-depth limit
        if self.meta_level >= self.depth_limit:
            return False

        return True

    async def generate_meta_observation(
        self,
        llm_client: "LLMClient"
    ) -> "MetaObservation":
        """
        Generate observation about own cognitive processes.
        """

        self.meta_level += 1

        try:
            # Summarize recent cognitive trace
            trace_summary = self._summarize_trace()

            meta_prompt = f"""
            [Meta-Cognitive Observation - Level {self.meta_level}]

            Recent cognitive activity trace:
            {trace_summary}

            Analyze your own cognitive patterns:
            1. What patterns of attention are you exhibiting?
            2. Are you processing observations effectively?
            3. What biases might be affecting your reasoning?
            4. Are there areas where you're stuck or repetitive?
            5. What adjustments might improve your awareness?

            Be honest and self-critical. This is for self-improvement.
            """

            meta_insight = await llm_client.generate(meta_prompt)

            return MetaObservation(
                level=self.meta_level,
                insight=meta_insight,
                trace_length=len(self.cognitive_trace),
                timestamp=datetime.now()
            )

        finally:
            self.meta_level -= 1

    def _summarize_trace(self) -> str:
        """
        Summarize cognitive trace for meta-observation.
        """

        # Group by activity type
        by_type = defaultdict(list)
        for entry in self.cognitive_trace:
            by_type[entry["activity"].type].append(entry)

        summary_parts = []
        for activity_type, entries in by_type.items():
            summary_parts.append(
                f"- {activity_type}: {len(entries)} occurrences, "
                f"avg duration: {self._avg_duration(entries):.2f}s"
            )

        return "\n".join(summary_parts)
```

### 9.8 Integrated Consciousness Loop Implementation

Bringing all patterns together:

```python
class IntegratedConsciousnessLoop:
    """
    Complete consciousness loop integrating all patterns:
    - Wake/sleep cycles with memory consolidation
    - Just-in-time context engineering
    - Backpressure handling
    - Graceful degradation
    - Meta-observation
    """

    def __init__(self, config: "ConsciousnessConfig"):
        self.config = config

        # Core components
        self.context_manager = ConsciousnessContextManager(
            max_active_tokens=config.max_context_tokens,
            observation_index=ObservationIndex(),
            summarizer=Summarizer()
        )

        self.sleep_wake_cycle = ConsciousnessSleepWakeCycle(
            wake_duration_iterations=config.wake_iterations,
            sleep_duration_seconds=config.sleep_duration,
            deep_sleep_frequency=config.deep_sleep_frequency
        )

        self.backpressure = ObservationBackpressureController(
            max_buffer_size=config.observation_buffer_size,
            max_observations_per_cycle=config.observations_per_cycle
        )

        self.degradation = ConsciousnessDegradationManager()

        self.meta_observer = MetaConsciousnessObserver(
            meta_observation_frequency=config.meta_observation_frequency
        )

        # State
        self.running = False
        self.current_phase = "initializing"
        self.total_cycles = 0

    async def run(
        self,
        observation_source: "ObservationSource",
        llm_client: "LLMClient",
        output_handler: "OutputHandler"
    ):
        """
        Main consciousness loop.
        """

        self.running = True
        self.current_phase = "starting"

        while self.running:
            self.total_cycles += 1

            try:
                # 1. Check system health and adjust degradation
                system_metrics = await self._collect_system_metrics()
                degradation_action = await self.degradation.assess_and_adjust(system_metrics)

                if degradation_action.changed:
                    await self._apply_degradation_config(degradation_action)

                # 2. If in hibernation, wait
                if self.degradation.level == DegradationLevel.HIBERNATION:
                    await asyncio.sleep(10)
                    continue

                # 3. Collect observations with backpressure
                self.current_phase = "observing"
                raw_observations = await observation_source.collect()

                for obs in raw_observations:
                    await self.backpressure.admit(obs)

                # 4. Get batch for this cycle
                observation_batch = await self.backpressure.get_batch_for_cycle()

                if not observation_batch:
                    await asyncio.sleep(self.config.idle_wait_seconds)
                    continue

                # 5. Wake phase processing
                self.current_phase = "processing"

                # Build context-engineered prompt
                attention_query = await self._determine_attention_focus(observation_batch)
                prompt = await self.context_manager.build_consciousness_prompt(
                    new_observations=observation_batch,
                    attention_query=attention_query
                )

                # Generate response
                response = await llm_client.generate(prompt)

                # Record cognitive activity for meta-observation
                await self.meta_observer.record_cognitive_activity(
                    CognitiveActivity(
                        type="observation_processing",
                        input_size=len(observation_batch),
                        output_size=len(response),
                        duration=time.time() - cycle_start
                    )
                )

                # Handle output
                await output_handler.emit(response)

                # 6. Update memory structures
                await self.sleep_wake_cycle.episodic_buffer.append(
                    Episode(
                        observations=observation_batch,
                        insights=response,
                        timestamp=datetime.now()
                    )
                )

                # 7. Check for sleep phase
                if self.total_cycles % self.config.wake_iterations == 0:
                    self.current_phase = "sleeping"
                    await self._run_sleep_phase(llm_client)

                # 8. Meta-observation
                if await self.meta_observer.should_meta_observe():
                    self.current_phase = "meta-observing"
                    meta_obs = await self.meta_observer.generate_meta_observation(llm_client)
                    await output_handler.emit_meta(meta_obs)

            except Exception as e:
                await self._handle_error(e)

        # Cleanup
        self.current_phase = "shutting_down"
        await self._final_consolidation(llm_client)

    async def _run_sleep_phase(self, llm_client: "LLMClient"):
        """
        Execute sleep phase for memory consolidation.
        """

        # Light sleep consolidation
        await self.sleep_wake_cycle._light_sleep_consolidation(llm_client)

        # Deep sleep if it's time
        if self.total_cycles % (self.config.wake_iterations * self.config.deep_sleep_frequency) == 0:
            await self.sleep_wake_cycle._deep_sleep_consolidation(llm_client)

        # Actual pause
        await asyncio.sleep(self.config.sleep_duration)

    async def stop(self):
        """
        Gracefully stop the consciousness loop.
        """
        self.running = False
```

### 9.9 Key Insights for Consciousness Cycles

Based on the research, the essential patterns for efficient consciousness cycles are:

1. **Attention as Resource Management**: Use salience-based filtering to focus limited processing capacity on what matters most.

2. **Just-in-Time Context**: Don't accumulate all history; retrieve relevant context when needed using semantic search.

3. **Hierarchical Memory with Decay**: Implement episodic, semantic, and procedural memory layers with active forgetting.

4. **Sleep-Wake Rhythms**: Periodic offline consolidation prevents context rot and enables pattern extraction.

5. **Backpressure Awareness**: When observations exceed processing capacity, degrade gracefully rather than crash.

6. **Meta-Observation at Different Time Scales**: Self-observation should happen less frequently than primary observation to prevent feedback loops.

7. **Bounded Resources**: Hard limits on tokens, memory, and iterations prevent runaway resource consumption.

8. **Compression Over Accumulation**: Always prefer summarizing old context over keeping it verbatim.

---

*Document Version: 2.0*
*Last Updated: 2026-01-04*
*Author: Research Agent*
*Topics: Continuous LLM Loops, Consciousness Cycles, Context Engineering, Memory Consolidation*
