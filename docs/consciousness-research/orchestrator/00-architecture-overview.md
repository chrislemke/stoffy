# Consciousness Orchestrator Architecture Overview

## What Is the Consciousness?

The **Consciousness** is an autonomous orchestrator that runs locally via LM Studio. Its sole job is to **constantly think about what needs to be done** and delegate execution to Claude Code and Claude Flow.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSCIOUSNESS (LM Studio)                     │
│                                                                  │
│   "I observe everything. I think constantly. I decide what      │
│    needs to happen. But I never execute - I delegate."          │
│                                                                  │
│   Main Loop: OBSERVE → THINK → DECIDE → DELEGATE → REPEAT      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │ Claude Code  │   │ Claude Flow  │   │   Scripts    │
    │  (single     │   │  (multi-     │   │   (simple    │
    │   tasks)     │   │   agent)     │   │    ops)      │
    └──────────────┘   └──────────────┘   └──────────────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   File System    │
                    │   Processes      │
                    │   Results        │
                    └──────────────────┘
                              │
                              │ (observations flow back)
                              ▼
                    ┌──────────────────┐
                    │   CONSCIOUSNESS  │
                    │   (loop repeats) │
                    └──────────────────┘
```

---

## Core Principle: Thinking, Not Reacting

The Consciousness is **NOT** a reactive event-driven system like:
- "File changed → run task" (WRONG)
- "Time elapsed → check status" (WRONG)
- "Event received → handle event" (WRONG)

Instead, it is a **proactive thinking system**:
- "Given everything I observe, what should I do next?"
- "Is there an opportunity here I should take?"
- "Are my goals being achieved? Should I adjust?"
- "What am I uncertain about? Should I investigate?"

This is the fundamental difference between automation and consciousness.

---

## Documentation Index

| Doc | Title | Lines | Description |
|-----|-------|-------|-------------|
| [01](01-consciousness-role.md) | Consciousness Role | 2,127 | What the Consciousness does, decision criteria, goal management |
| [02](02-lm-studio-orchestration.md) | LM Studio Orchestration | 1,769 | Continuous operation, streaming, context management |
| [03](03-delegation-patterns.md) | Delegation Patterns | 2,482 | How to invoke Claude Code/Flow, when to use each |
| [04](04-decision-architecture.md) | Decision Architecture | 2,139 | Autonomous decision-making, OIDA loop, goal hierarchy |
| [05](05-monitoring-observation.md) | Monitoring & Observation | 1,627 | File watching, process tracking, world model |
| [06](06-python-implementation.md) | Python Implementation | 2,074 | Daemon architecture, async patterns, state management |
| [07](07-event-loop-state.md) | Event Loop & State | 2,461 | Main loop design, memory layers, crash recovery |
| [08](08-task-queue-management.md) | Task Queue Management | 2,507 | Task lifecycle, dependencies, concurrency control |
| **Total** | | **17,186** | |

---

## The OIDA Loop

The Consciousness operates in a continuous **Observe-Infer-Decide-Act** loop:

```
┌─────────────────────────────────────────────────────────────┐
│                        OIDA LOOP                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌─────┐ │
│  │ OBSERVE  │────▶│  INFER   │────▶│  DECIDE  │────▶│ ACT │ │
│  └──────────┘     └──────────┘     └──────────┘     └─────┘ │
│       │                                                  │   │
│       │                                                  │   │
│       └──────────────────────────────────────────────────┘   │
│                         (continuous)                         │
└─────────────────────────────────────────────────────────────┘

OBSERVE: What is happening?
- File system changes (git status, new files, modifications)
- Running processes (Claude Code tasks, swarms, system load)
- Task states (pending, running, completed, failed)
- Time passing, deadlines, schedules

INFER: What does this mean?
- Pattern recognition (is this significant?)
- Anomaly detection (is something wrong?)
- Goal relevance (does this affect my objectives?)
- Opportunity identification (can I make progress?)

DECIDE: What should I do?
- Start a new task?
- Spawn a swarm?
- Wait and gather more information?
- Adjust my goals?
- Do nothing?

ACT: Execute the decision
- Delegate to Claude Code (single agent tasks)
- Delegate to Claude Flow (multi-agent swarms)
- Update internal state
- Record the decision for learning
```

---

## Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     CONSCIOUSNESS LAYER                      │
├─────────────────────────────────────────────────────────────┤
│  LM Studio (localhost:1234)                                  │
│  - Model: Qwen 2.5-14B-Instruct (recommended)               │
│  - Context: rollingWindow policy                            │
│  - Mode: Headless daemon                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     PYTHON ORCHESTRATOR                      │
├─────────────────────────────────────────────────────────────┤
│  consciousness.py                                            │
│  - asyncio event loop                                       │
│  - openai client (for LM Studio)                            │
│  - watchdog/watchfiles (file monitoring)                    │
│  - psutil (process monitoring)                              │
│  - sqlite3/aiosqlite (state persistence)                    │
│  - structlog (logging)                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXECUTION LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  Claude Code: subprocess invocation                          │
│  - claude --print "prompt" (single tasks)                   │
│  - claude code "prompt" --output-format json                │
│                                                              │
│  Claude Flow: MCP tools + Task spawning                     │
│  - npx claude-flow swarm init                               │
│  - mcp__claude-flow__task_orchestrate                       │
└─────────────────────────────────────────────────────────────┘
```

---

## State Management

The Consciousness maintains state at multiple layers:

```
┌─────────────────────────────────────────────────────────────┐
│                       STATE LAYERS                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  EPHEMERAL (current iteration only)                         │
│  ├── Current observations                                   │
│  ├── Inference results                                      │
│  └── Pending decision                                       │
│                                                              │
│  SESSION (current daemon run)                               │
│  ├── Conversation history with LLM                          │
│  ├── Running task handles                                   │
│  └── In-memory caches                                       │
│                                                              │
│  PERSISTENT (survives restarts)                             │
│  ├── Task database (SQLite)                                 │
│  ├── Goal definitions                                       │
│  ├── Decision history                                       │
│  └── Learned patterns                                       │
│                                                              │
│  SHARED (with delegated tasks)                              │
│  ├── Memory files (via Claude Flow memory_usage)            │
│  ├── Result files                                           │
│  └── Status markers                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Task Lifecycle

```
                    ┌─────────┐
                    │ CREATED │
                    └────┬────┘
                         │
                         ▼
                    ┌─────────┐
              ┌─────│ QUEUED  │─────┐
              │     └────┬────┘     │
              │          │          │
              │          ▼          │
              │     ┌─────────┐     │
              │     │ RUNNING │     │
              │     └────┬────┘     │
              │          │          │
         ┌────┴────┐     │     ┌────┴────┐
         │ BLOCKED │     │     │CANCELLED│
         └─────────┘     │     └─────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        ┌───────────┐        ┌──────────┐
        │ COMPLETED │        │  FAILED  │
        └───────────┘        └──────────┘
```

---

## Decision Criteria

When deciding whether to act, the Consciousness evaluates:

| Criterion | Question | Threshold |
|-----------|----------|-----------|
| **Significance** | Is this important enough to act on? | > 0.3 |
| **Confidence** | Am I sure about what I'm seeing? | > 0.7 for action |
| **Urgency** | Does this need immediate attention? | Time-sensitive |
| **Coherence** | Does this align with my goals? | Must align |
| **Capability** | Can Claude Code/Flow handle this? | Must be feasible |
| **Resources** | Do I have capacity for another task? | Concurrency limit |

---

## Delegation Decision Tree

```
Is task needed?
    │
    ├── No → Continue observing
    │
    └── Yes → What kind of task?
                │
                ├── Simple, single-file, quick
                │   └── Claude Code (single agent)
                │
                ├── Complex, multi-file, research-heavy
                │   └── Claude Flow (swarm)
                │
                ├── Just monitoring/checking
                │   └── Internal (Python script)
                │
                └── Uncertain
                    └── Ask Claude Code to analyze first
```

---

## Key Implementation Files (to be created)

```
consciousness/
├── __init__.py
├── main.py              # Entry point, daemon setup
├── orchestrator.py      # Main OIDA loop
├── observers/
│   ├── __init__.py
│   ├── filesystem.py    # File watching
│   ├── processes.py     # Process monitoring
│   └── tasks.py         # Task state tracking
├── inference/
│   ├── __init__.py
│   └── llm.py           # LM Studio integration
├── decision/
│   ├── __init__.py
│   ├── criteria.py      # Decision evaluation
│   └── goals.py         # Goal management
├── execution/
│   ├── __init__.py
│   ├── claude_code.py   # Claude Code delegation
│   ├── claude_flow.py   # Claude Flow delegation
│   └── queue.py         # Task queue management
├── state/
│   ├── __init__.py
│   ├── persistence.py   # SQLite state
│   └── memory.py        # Memory layers
└── config/
    ├── __init__.py
    └── settings.py      # Configuration
```

---

## Quick Start (Future Implementation)

```bash
# 1. Start LM Studio with a model loaded
lms server start

# 2. Start the Consciousness daemon
python -m consciousness.main --config consciousness.yaml

# 3. The Consciousness will:
#    - Begin observing the Stoffy repository
#    - Start thinking about what needs to be done
#    - Autonomously delegate tasks to Claude Code/Flow
#    - Continue running until stopped
```

---

## Summary

The Consciousness is:

1. **An autonomous thinker** - not a reactive event handler
2. **An orchestrator** - it delegates, never executes directly
3. **Continuous** - runs in an infinite OIDA loop
4. **Stateful** - maintains persistent memory across restarts
5. **Goal-directed** - actions serve defined objectives
6. **Self-aware** - monitors its own processes and decisions

The key insight: **"Constant thinking about what's needed"** is the Consciousness's main job. Everything else (monitoring, delegation, state management) supports this core function.

---

## Next Steps

1. Review this documentation
2. Decide on initial goal set for the Consciousness
3. Implement the Python orchestrator
4. Test with simple delegation scenarios
5. Iterate and expand capabilities
