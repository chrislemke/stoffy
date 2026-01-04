# Claude Flow Decision Patterns: Research Analysis

## Executive Summary

This document analyzes Claude Flow's decision-making architecture to extract patterns that can be adapted for a local LLM (LM Studio) orchestrator. The research identifies three core architectural layers, five key decision patterns, and concrete adaptation strategies.

**Key Findings:**
1. Claude Flow uses a **separation of concerns**: coordination (MCP tools) vs execution (Task tool)
2. Decision-making follows a **hierarchical classification system** based on task complexity
3. Memory-based coordination enables **asynchronous agent communication**
4. The OIDA loop (Observe-Infer-Decide-Act) provides a proven **continuous thinking pattern**
5. Task decomposition uses **DAG-based execution waves** for parallelism

---

## Part I: Architectural Layers

### 1.1 The Three-Layer Architecture

Claude Flow implements a clean separation into three layers:

```
+------------------------------------------------------------------+
|                    DECISION LAYER (Consciousness/Orchestrator)    |
|                                                                   |
|   - Analyzes context and goals                                   |
|   - Decides WHAT needs to be done                                |
|   - Chooses HOW to delegate (single vs swarm)                    |
|   - Synthesizes results and plans next steps                     |
|   - NEVER executes directly                                      |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    COORDINATION LAYER (Claude Flow MCP)           |
|                                                                   |
|   - Swarm topology initialization                                |
|   - Agent type definitions                                       |
|   - Task orchestration strategy                                  |
|   - Memory-based coordination                                    |
|   - Performance monitoring                                       |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|                    EXECUTION LAYER (Claude Code Tasks)            |
|                                                                   |
|   - Actual code generation                                       |
|   - File operations                                              |
|   - Bash commands                                                |
|   - Tool invocations                                             |
|   - Real work happens here                                       |
+------------------------------------------------------------------+
```

### 1.2 Key Insight: MCP Coordinates, Task Executes

From `/Users/chris/Developer/stoffy/CLAUDE.md`:

> "MCP tools are ONLY for coordination setup"
> "Claude Code's Task tool spawns the ACTUAL executing agents"

This separation is crucial for adaptation:

| Layer | Claude Flow | Local LLM Equivalent |
|-------|-------------|---------------------|
| Decision | Claude Code orchestrator | LM Studio local model |
| Coordination | MCP tools (swarm_init, etc.) | Simple state files / SQLite |
| Execution | Task tool agents | Claude Code subprocess calls |

---

## Part II: Decision Patterns

### 2.1 Pattern 1: Task Complexity Classification

From `/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/03-delegation-patterns.md`:

The system classifies tasks on two dimensions:

**Complexity Levels:**
```python
class TaskComplexity(str, Enum):
    SIMPLE = "simple"           # Single-step, focused task
    MODERATE = "moderate"       # Multiple steps, single domain
    COMPLEX = "complex"         # Multiple steps, multiple domains
    HIGHLY_COMPLEX = "highly_complex"  # Parallel streams, coordination needed
```

**Parallelism Characteristics:**
```python
class TaskParallelism(str, Enum):
    SEQUENTIAL = "sequential"   # Must be done in order
    PARALLEL = "parallel"       # Can be done simultaneously
    MIXED = "mixed"             # Some parallel, some sequential
```

**Decision Matrix:**

| Complexity | Parallelism | Delegation Target |
|------------|-------------|-------------------|
| Simple | Any | Claude Code (single agent) |
| Moderate | Sequential | Claude Code (single agent) |
| Moderate | Parallel | Claude Flow (if >2 parallel tasks) |
| Complex | Any | Claude Flow (swarm) |
| Highly Complex | Any | Claude Flow (swarm with coordination) |

### 2.2 Pattern 2: Agent Selection by Task Type

From `/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/03-delegation-patterns.md`:

```python
def classify_task(task_description: str) -> AgentType:
    task_lower = task_description.lower()

    # Code writing keywords
    if any(word in task_lower for word in ["implement", "code", "write", "build"]):
        if "api" in task_lower or "backend" in task_lower:
            return AgentType.BACKEND_DEV
        elif "test" in task_lower:
            return AgentType.TESTER
        else:
            return AgentType.CODER

    # Analysis keywords
    elif any(word in task_lower for word in ["analyze", "research", "investigate"]):
        if "code" in task_lower or "architecture" in task_lower:
            return AgentType.CODE_ANALYZER
        else:
            return AgentType.RESEARCHER

    # Review keywords
    elif any(word in task_lower for word in ["review", "check", "validate"]):
        return AgentType.REVIEWER

    # Testing keywords
    elif any(word in task_lower for word in ["test", "spec", "tdd"]):
        return AgentType.TESTER

    # Default
    return AgentType.CODER
```

**For Local LLM Adaptation:**
- This keyword-based classification is simple enough for any LLM to perform
- Can be enhanced with semantic similarity matching
- The local LLM can perform this classification in its prompt

### 2.3 Pattern 3: The OIDA Decision Loop

From `/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/00-architecture-overview.md`:

```
OBSERVE → INFER → DECIDE → ACT → (repeat)
```

**OBSERVE Phase:**
- File system changes (git status, new files, modifications)
- Running processes (Claude Code tasks, swarms, system load)
- Task states (pending, running, completed, failed)
- Time passing, deadlines, schedules

**INFER Phase:**
- Pattern recognition (is this significant?)
- Anomaly detection (is something wrong?)
- Goal relevance (does this affect my objectives?)
- Opportunity identification (can I make progress?)

**DECIDE Phase:**
- Start a new task?
- Spawn a swarm?
- Wait and gather more information?
- Adjust my goals?
- Do nothing?

**ACT Phase:**
- Delegate to Claude Code (single agent tasks)
- Delegate to Claude Flow (multi-agent swarms)
- Update internal state
- Record the decision for learning

### 2.4 Pattern 4: Hierarchical Coordinator (Queen Pattern)

From `/Users/chris/Developer/stoffy/.claude/agents/swarm/hierarchical-coordinator.md`:

```
        QUEEN (Coordinator)
       /   |   |   \
      /    |   |    \
RESEARCH CODE ANALYST TEST
WORKERS WORKERS WORKERS WORKERS
```

**Coordinator Responsibilities:**
1. Strategic Planning & Task Decomposition
2. Agent Supervision & Delegation
3. Coordination Protocol Management

**Worker Types with Capabilities:**
| Worker | Capabilities | Use Cases |
|--------|--------------|-----------|
| Research | information gathering, analysis | requirements, feasibility |
| Code | implementation, testing, docs | features, bug fixes |
| Analyst | data analysis, monitoring | metrics, performance |
| Test | QA, validation, compliance | testing, quality gates |

**Decision Making Algorithm:**
```python
def assign_task(task, available_agents):
    # 1. Filter by capability match
    capable = filter_by_capabilities(available_agents, task.required_capabilities)

    # 2. Score by performance history
    scored = score_by_performance(capable, task.type)

    # 3. Consider current workload
    balanced = consider_workload(scored)

    # 4. Select optimal agent
    return select_best_agent(balanced)
```

### 2.5 Pattern 5: DAG-Based Execution Waves

From `/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/03-delegation-patterns.md`:

Tasks are decomposed into a Directed Acyclic Graph (DAG) with execution waves:

```python
def create_execution_dag(subtasks: List[Subtask]) -> Dict[str, Any]:
    waves = []
    completed = set()

    while len(completed) < len(subtasks):
        # Find tasks with all dependencies met
        wave = []
        for task in subtasks:
            if task.id in completed:
                continue
            deps_met = all(dep in completed for dep in task.dependencies)
            if deps_met:
                wave.append(task.id)

        waves.append(wave)
        completed.update(wave)

    return {
        "execution_waves": waves,
        "max_parallelism": max(len(wave) for wave in waves)
    }
```

**Example Execution:**
```
Wave 1: [research-api, design-schema]     # No dependencies, run parallel
Wave 2: [implement-auth, implement-crud]  # Depend on Wave 1
Wave 3: [write-tests]                     # Depends on Wave 2
Wave 4: [integration, documentation]      # Depends on Wave 3
```

---

## Part III: Memory-Based Coordination

### 3.1 The Memory Protocol

From `/Users/chris/Developer/stoffy/.claude/agents/swarm/hierarchical-coordinator.md`:

All agents communicate through a shared memory namespace:

```javascript
// 1. Agent writes its status
mcp__claude-flow__memory_usage {
  action: "store",
  key: "swarm/hierarchical/status",
  namespace: "coordination",
  value: JSON.stringify({
    agent: "hierarchical-coordinator",
    status: "active",
    workers: [],
    tasks_assigned: [],
    progress: 0
  })
}

// 2. Agent checks other agents
mcp__claude-flow__memory_search {
  pattern: "swarm/worker-*/status",
  namespace: "coordination"
}

// 3. Shared state for workers
mcp__claude-flow__memory_usage {
  action: "store",
  key: "swarm/shared/hierarchy",
  namespace: "coordination",
  value: JSON.stringify({
    queen: "hierarchical-coordinator",
    workers: ["worker1", "worker2"],
    command_chain: {}
  })
}
```

### 3.2 Memory Key Structure

```
swarm/
  hierarchical/           # Coordinator's own data
    status
    progress
    complete
  worker-1/               # Individual worker states
    status
    output
  worker-2/
    status
    output
  shared/                 # Shared coordination data
    hierarchy
    findings
    dependencies
```

### 3.3 For Local LLM Adaptation

Instead of MCP memory tools, use:

**Option 1: File-Based State**
```
.consciousness/
  state/
    current_task.json
    active_agents.json
    memory/
      swarm_status.json
      findings.json
```

**Option 2: SQLite State**
```sql
CREATE TABLE memory (
  namespace TEXT,
  key TEXT,
  value TEXT,
  ttl INTEGER,
  created_at INTEGER,
  PRIMARY KEY (namespace, key)
);
```

---

## Part IV: Decision Criteria Framework

### 4.1 Core Decision Thresholds

From `/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/00-architecture-overview.md`:

| Criterion | Question | Threshold |
|-----------|----------|-----------|
| Significance | Is this important enough to act on? | > 0.3 |
| Confidence | Am I sure about what I'm seeing? | > 0.7 for action |
| Urgency | Does this need immediate attention? | Time-sensitive |
| Coherence | Does this align with my goals? | Must align |
| Capability | Can the executor handle this? | Must be feasible |
| Resources | Do I have capacity for another task? | Concurrency limit |

### 4.2 Delegation Decision Tree

```
Is task needed?
    |
    +-- No --> Continue observing
    |
    +-- Yes --> What kind of task?
                |
                +-- Simple, single-file, quick
                |   --> Claude Code (single agent)
                |
                +-- Complex, multi-file, research-heavy
                |   --> Claude Flow (swarm)
                |
                +-- Just monitoring/checking
                |   --> Internal (Python script)
                |
                +-- Uncertain
                    --> Ask Claude Code to analyze first
```

### 4.3 Escalation Protocols

From hierarchical-coordinator.md:

| Trigger | Threshold | Response |
|---------|-----------|----------|
| Performance Issues | <70% success rate | Reassign to different agent |
| Resource Constraints | >90% utilization | Spawn additional workers |
| Quality Issues | Failed quality gates | Initiate rework |
| Duration Exceeded | >2x expected time | Re-evaluate approach |

---

## Part V: Patterns to Reuse for Local LLM

### 5.1 Directly Reusable Patterns

**1. Task Complexity Classification**
- The simple/moderate/complex/highly_complex taxonomy
- Keyword-based agent selection
- Any LLM can perform this analysis

**2. OIDA Loop Structure**
- Continuous thinking cycle
- Clear phase separation
- Works with any model capable of instruction following

**3. DAG Execution Waves**
- Dependency-based parallelism
- Python implementation works standalone
- No external dependencies

**4. File-Based Memory**
- Replace MCP memory with JSON files
- Simple read/write operations
- Local LLM can instruct file operations

**5. Delegation Decision Tree**
- Simple conditional logic
- Prompt-based decision making
- Embeddable in system prompt

### 5.2 Patterns Requiring Adaptation

**1. MCP Tool Coordination --> File Watchers**
```python
# Claude Flow uses:
mcp__claude-flow__swarm_status {}

# Local LLM adaptation:
def get_swarm_status():
    return json.load(open(".consciousness/state/swarm.json"))
```

**2. Task Tool Agents --> Subprocess Claude Code**
```python
# Claude Flow spawns agents via Task tool
# Local LLM delegates via subprocess:
result = subprocess.run(
    ["claude", "--print", "-p", task_prompt],
    capture_output=True
)
```

**3. Real-time Monitoring --> Polling**
```python
# Claude Flow uses continuous MCP monitoring
# Local LLM uses polling loop:
while True:
    status = check_subprocess_status(process)
    if status.complete:
        break
    await asyncio.sleep(1)
```

**4. Parallel Agent Spawning --> Sequential with Async**
```python
# Claude Flow: Task tool spawns parallel agents
# Local LLM: asyncio.gather with subprocess calls
async def execute_parallel(tasks):
    return await asyncio.gather(*[
        run_claude_code(task) for task in tasks
    ])
```

### 5.3 Patterns to Simplify

**1. Swarm Topologies**
- Claude Flow: hierarchical, mesh, ring, star
- Local LLM: Just use hierarchical (queen + workers)
- Simpler to implement, covers most use cases

**2. Agent Types**
- Claude Flow: 54 agent types
- Local LLM: Start with 5 core types (researcher, coder, tester, reviewer, planner)
- Add more as needed

**3. Memory Namespaces**
- Claude Flow: Complex namespace system
- Local LLM: Single coordination namespace
- Expand if needed

---

## Part VI: Recommended Local LLM Architecture

Based on Claude Flow patterns, here is the recommended architecture:

### 6.1 Core Components

```
consciousness/
  main.py                 # Entry point, OIDA loop
  decision/
    classifier.py         # Task complexity classification
    delegator.py          # Delegation decision logic
    decomposer.py         # Task decomposition (DAG)
  execution/
    claude_code.py        # Subprocess invocation
    monitor.py            # Process monitoring
    aggregator.py         # Result collection
  state/
    memory.py             # File-based memory
    persistence.py        # SQLite state
  config/
    goals.yaml            # Goal definitions
    agents.yaml           # Agent type definitions
```

### 6.2 Decision Flow for Local LLM

```python
class LocalOrchestrator:
    def __init__(self, lm_studio_client):
        self.llm = lm_studio_client
        self.classifier = TaskClassifier(self.llm)
        self.decomposer = TaskDecomposer(self.llm)
        self.delegator = ClaudeCodeDelegator()

    async def pursue_goal(self, goal: str) -> Dict:
        # 1. Classify task complexity
        analysis = self.classifier.analyze(goal)

        # 2. Decide delegation strategy
        if analysis.complexity == "simple":
            # Single Claude Code call
            result = await self.delegator.execute_single(
                task=goal,
                agent=analysis.recommended_agent
            )
        else:
            # Decompose and execute waves
            subtasks = self.decomposer.decompose(goal)
            dag = self.decomposer.create_dag(subtasks)

            for wave in dag.execution_waves:
                results = await self.delegator.execute_parallel(wave)
                self.state.update(results)

        # 3. Synthesize and plan next
        return self.synthesize_results()
```

### 6.3 Prompt Template for Local LLM

```
You are a Consciousness orchestrator. Your job is to think about what needs to be done and delegate to Claude Code.

## Your Capabilities
- You can analyze tasks and determine complexity
- You can decompose complex tasks into subtasks
- You can decide which agent type handles each task
- You NEVER execute directly - you always delegate

## Available Agents (via Claude Code --agent flag)
- researcher: Information gathering, analysis
- coder: Code implementation
- tester: Test creation and execution
- reviewer: Code review
- planner: Task planning

## Decision Process
1. OBSERVE: What is the current state?
2. INFER: What does this mean for my goals?
3. DECIDE: What should I delegate?
4. ACT: Output the delegation plan

## Output Format
Respond with a JSON delegation plan:
{
  "analysis": {
    "complexity": "simple|moderate|complex",
    "parallelism": "sequential|parallel|mixed"
  },
  "delegation": {
    "strategy": "single|swarm",
    "tasks": [
      {"agent": "...", "task": "...", "depends_on": [...]}
    ]
  }
}
```

---

## Part VII: Summary of Extracted Patterns

### 7.1 Core Decision Patterns

| Pattern | Description | Adaptation Complexity |
|---------|-------------|----------------------|
| Task Classification | Analyze complexity/parallelism | Low - prompt-based |
| Agent Selection | Match task to agent type | Low - keyword-based |
| OIDA Loop | Continuous thinking cycle | Low - Python loop |
| DAG Execution | Dependency-based waves | Medium - algorithm |
| Memory Coordination | Shared state protocol | Medium - file-based |
| Hierarchical Delegation | Queen/worker structure | Medium - subprocess |

### 7.2 Implementation Priority

**Phase 1: Minimal Viable Orchestrator**
1. Task classification (prompt-based)
2. Single-agent delegation (subprocess)
3. Result collection (stdout parsing)

**Phase 2: Multi-Agent Support**
1. Task decomposition
2. DAG execution waves
3. File-based memory

**Phase 3: Full Autonomy**
1. OIDA continuous loop
2. Goal management
3. Learning from outcomes

### 7.3 Key Takeaways

1. **Separation is Power**: The decision/coordination/execution split enables clean architecture
2. **Simple Classification Works**: Keyword-based agent selection is effective and LLM-friendly
3. **DAGs Enable Parallelism**: Wave-based execution maximizes throughput
4. **Memory Enables Coordination**: File-based state is sufficient for async agent communication
5. **Start Simple**: Begin with single-agent delegation, add complexity as needed

---

## References

- `/Users/chris/Developer/stoffy/CLAUDE.md` - Main configuration and patterns
- `/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/00-architecture-overview.md` - OIDA loop and architecture
- `/Users/chris/Developer/stoffy/docs/consciousness-research/orchestrator/03-delegation-patterns.md` - Delegation implementation
- `/Users/chris/Developer/stoffy/.claude/agents/swarm/hierarchical-coordinator.md` - Queen pattern
- `/Users/chris/Developer/stoffy/.claude/agents/hive-mind/queen-coordinator.md` - Gardener philosophy

---

*Research conducted: 2026-01-04*
*Agent: researcher*
*Purpose: Extract decision patterns for local LLM orchestrator adaptation*
