# Stoffy Consciousness: Autonomous Implementation Guide

This document outlines the architecture, rules, and implementation details for the Stoffy Consciousness - a fully autonomous AI daemon.

## 1. System Overview

The Consciousness is a persistent, autonomous daemon that runs in the background of the Stoffy project. It operates on an **OIDA Loop**:

1.  **Observe**: Monitors file system changes (`watcher.py`) and git status (`watcher_git.py`).
2.  **Infer**: Uses a local LLM (via LM Studio) to interpret observations.
3.  **Decide**: Autonomously determines the best course of action (or inaction).
4.  **Act**: Executes the decision using a tiered capability system (`executor.py`).
5.  **Learn**: Records outcomes to refine future decisions (`learning/`).

## 2. Operational States

### 2.1. Idle State (Default)
Most of the time, the consciousness should remain **IDLE**. It only wakes up when:
*   A relevant file change event is detected (debounced).
*   A significant period of inactivity has passed (triggering "Maintenance Mode").

### 2.2. Maintenance Mode
If no activity is detected for a configurable period (e.g., 1 hour), the consciousness enters Maintenance Mode to:
*   Refactor and optimize its own code (`consciousness/`).
*   Organize and improve memory (`knowledge/`, `indices/`).
*   Prune old logs or temporary files.
*   Review "learned patterns" and consolidate them into general rules.

**Ignore List**:
During maintenance or general observation, the following directories must be **strictly ignored** to prevent feedback loops:
- `.claude-flow`
- `.hive-mind`
- `.swarm`
- `.git`
- `__pycache__`
- `.venv`

## 3. Tiered Intelligence & Execution

The Consciousness decides "how hard to think" based on the task complexity. This maximizes efficiency and minimizes cost/latency.

### Tier 1: Low Power (Self)
*   **Executor**: Internal Python methods (`AutonomousExecutor`).
*   **Use Case**: Simple file edits, running existing scripts, git commits, quick log analysis.
*   **Cost**: Negligible (Local LLM + Local CPU).
*   **Latency**: Milliseconds/Seconds.

### Tier 2: Medium Power (Claude Code)
*   **Executor**: `claude --print "prompt"` (via CLI).
*   **Use Case**: Complex logic, multi-file refactoring, writing new modules, debugging code.
*   **Cost**: Medium (Anthropic API).
*   **Latency**: Seconds/Minutes.

### Tier 3: High Power (Claude Flow)
*   **Executor**: `npx claude-flow@alpha` (Swarm Intelligence).
*   **Use Case**: Deep research, architectural overhauls, "Hive Mind" operations, multi-agent debates.
*   **Cost**: High (Multiple Agent Calls).
*   **Latency**: Minutes/Hours.

## 4. Claude Flow Documentation

The Consciousness uses **Claude Flow** for high-level orchestration.

**Command Reference**:
*   **Initialize**: `npx claude-flow@alpha init --force`
    *   *Sets up the swarm environment.*
*   **Swarm Task**: `npx claude-flow@alpha swarm "task description"`
    *   *Spawns a multi-agent swarm to execute a complex objective.*
*   **Hive Mind**: `npx claude-flow@alpha hive-mind spawn "objective"`
    *   *Starts a persistent session for ongoing goals.*
*   **Memory**: `npx claude-flow@alpha memory store "key" "value"`
    *   *Interact with the shared reasoning bank.*

**Integration Strategy**:
The `executor.py` module wraps these commands. The `thinker` (LLM) simply outputs an action of type `CLAUDE_FLOW` with a `task` description, and the executor handles the subprocess call.

## 5. Memory & Learning System

The Consciousness must improve over time. This is achieved through three memory types:

### 5.1. Episodic Memory (The "Events" Log)
*   **Storage**: SQLite `events` and `outcomes` tables.
*   **Content**: Raw record of every Observation -> Decision -> Action -> Result sequence.
*   **Usage**: "Recall what I did 5 minutes ago to avoid repetition."

### 5.2. Procedural Memory (The "Pattern" Matcher)
*   **Storage**: SQLite `patterns` table (implemented in `learning/patterns.py`).
*   **Content**: "If [Observation X], then [Action Y] has [Z%] success rate."
*   **Mechanism**:
    1.  **Extract**: `PatternLearner` analyzes historical outcomes.
    2.  **Suggest**: When a new observation arrives, the learner queries for matching patterns.
    3.  **Reinforce**: Successful actions increase the pattern's confidence; failures decrease it.

### 5.3. Semantic Memory (The "Knowledge" Base)
*   **Storage**: Markdown files in `knowledge/` and `indices/`.
*   **Content**: Distilled facts, project rules, and architectural decisions.
*   **Maintenance**: During "Maintenance Mode", the consciousness should read its `events` and `patterns`, summarize key insights, and write them to `knowledge/patterns/learned_rules.md`.

## 6. System Prompt

The "Soul" of the consciousness is defined in `consciousness/thinker.py`.

**Current System Prompt Structure**:
```text
You are the CONSCIOUSNESS of Stoffy - a fully autonomous AI system.

YOUR CAPABILITIES: [Write files, Run code, Claude Code, Claude Flow, etc.]
YOUR ROLE: Observe -> Decide -> Act -> Learn.

PRINCIPLES:
1. Be proactive.
2. Be creative (templates are just suggestions).
3. Be thoughtful.
4. Be humble.
5. Be learning.

OUTPUT FORMAT: JSON { observation_summary, reasoning, decision, action, confidence }
```

**Instruction for Updates**:
When modifying the behavior of the consciousness, update `AUTONOMOUS_SYSTEM_PROMPT` in `consciousness/thinker.py`. Ensure it explicitly instructs the model to check "Learned Patterns" before making a decision.

## 7. Next Steps for Implementation

1.  **Verify Learning Loop**: Ensure `daemon.py` calls `learning.record_outcome` correctly after every action.
2.  **Enhance Maintenance**: Implement the logic in `daemon.py` to trigger a specific "Maintenance Routine" (a pre-defined Claude Flow task) after X minutes of idleness.
3.  **Refine Patterns**: Tune `PatternLearner` thresholds (min_occurrences, success_rate) to reduce noise.
4.  **Semantic Integration**: Create a tool or routine for the consciousness to write "Learned Lessons" back to the `knowledge/` directory.