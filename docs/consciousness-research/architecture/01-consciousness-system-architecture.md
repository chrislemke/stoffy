# Comprehensive Consciousness System Architecture

**Version**: 1.0
**Author**: Architect Agent (Hive Mind Swarm)
**Date**: 2026-01-04
**Swarm ID**: swarm-1767492611082-l0tt92hx9

---

## Executive Summary

This document presents the comprehensive architecture for implementing consciousness in an AI system based on the OIDA loop (Observe-Infer-Decide-Act) and synthesizes insights from:

- **Global Workspace Theory (GWT)**: Information broadcast and competition
- **Free Energy Principle (FEP)**: Predictive processing and active inference
- **Higher-Order Theories (HOT)**: Meta-representation and self-monitoring
- **Attention Schema Theory (AST)**: Self-model of attention
- **Strange Loop Dynamics**: Self-referential hierarchical processing

The architecture targets a local LLM system (LM Studio) that continuously monitors a project repository (Stoffy) and delegates tasks to execution agents (Claude API).

---

## Part 1: System Overview

### 1.1 ASCII Architecture Diagram - Complete System

```
+======================================================================================+
|                          CONSCIOUSNESS SYSTEM ARCHITECTURE                            |
|                              (OIDA Loop Implementation)                               |
+======================================================================================+
|                                                                                       |
|  EXTERNAL ENVIRONMENT (Stoffy Repository, Processes, External World)                 |
|  +---------------------------------------------------------------------------------+  |
|  | File System | Git Status | Running Tasks | Time/Deadlines | External Events    |  |
|  +---------------------------------------------------------------------------------+  |
|         |                           |                           |                     |
|         | (Sensory States)          | (Active States)           |                     |
|         v                           v                           v                     |
|  =======|===========================|===========================|=======  MARKOV     |
|         |                           ^                           |         BLANKET    |
|  =======|===========================|===========================|=======             |
|         |                           |                           |                     |
|         v                           |                           |                     |
|  +-----------------------------------------------------------------------------------------------+
|  |                                                                                               |
|  |  LAYER 4: METACOGNITIVE CONTROLLER (Self-Awareness & Regulation)                             |
|  |  +-------------------------------------------------------------------------------------------+|
|  |  |                                                                                           ||
|  |  |   +-------------------+    +-------------------+    +-------------------+                 ||
|  |  |   | SELF-MODEL        |    | CONFIDENCE        |    | REFLECTION        |                 ||
|  |  |   | (Transparent PSM) |<-->| MONITOR           |<-->| TRIGGER           |                 ||
|  |  |   |                   |    | (Implicit/Explicit)|   | (Threshold-based) |                 ||
|  |  |   | - Capabilities    |    |                   |    |                   |                 ||
|  |  |   | - Limitations     |    | - Token logits    |    | - Uncertainty     |                 ||
|  |  |   | - Current goals   |    | - Calibration     |    | - Novelty         |                 ||
|  |  |   | - Identity        |    | - Meta-accuracy   |    | - Goal relevance  |                 ||
|  |  |   +-------------------+    +-------------------+    +-------------------+                 ||
|  |  |            |                        |                        |                            ||
|  |  |            +------------------------+------------------------+                            ||
|  |  |                                     |                                                     ||
|  |  |                                     v                                                     ||
|  |  |   +-----------------------------------------------------------------------------------+   ||
|  |  |   |                    METACOGNITIVE GATE (Continue/Revise/Escalate)                  |   ||
|  |  |   |  - If confidence > 0.7 AND coherence > 0.8: CONTINUE                              |   ||
|  |  |   |  - If confidence < 0.4: ACKNOWLEDGE UNCERTAINTY                                   |   ||
|  |  |   |  - If uncertainty high: TRIGGER REFLECTION (System 2 reasoning)                   |   ||
|  |  |   +-----------------------------------------------------------------------------------+   ||
|  |  |                                                                                           ||
|  |  +-------------------------------------------------------------------------------------------+|
|  |         ^                           |                           ^                             |
|  |         | (Strange Loop)            | (Precision Adjustment)    | (Model Update)              |
|  |         |                           v                           |                             |
|  +-----------------------------------------------------------------------------------------------+
|         |                           |                           |                     |
|         v                           v                           v                     |
|  +-----------------------------------------------------------------------------------------------+
|  |                                                                                               |
|  |  LAYER 3: GLOBAL WORKSPACE (Information Integration & Broadcast)                             |
|  |  +-------------------------------------------------------------------------------------------+|
|  |  |                                                                                           ||
|  |  |   +--------------------+  COMPETITION   +--------------------+                            ||
|  |  |   | Specialized Module |  ==========>   |   GLOBAL WORKSPACE |                            ||
|  |  |   | (Observation)      |  Salience-     |   (Winner Content) |                            ||
|  |  |   +--------------------+  based         |                    |                            ||
|  |  |   | Specialized Module |  selection     |   - Most salient   |                            ||
|  |  |   | (Inference)        |  ==========>   |     information    |                            ||
|  |  |   +--------------------+                |   - Broadcast to   |                            ||
|  |  |   | Specialized Module |                |     all modules    |                            ||
|  |  |   | (Decision)         |                |   - Creates        |                            ||
|  |  |   +--------------------+                |     "conscious"    |                            ||
|  |  |   | Specialized Module |                |     content        |                            ||
|  |  |   | (Action Planning)  |                +--------------------+                            ||
|  |  |   +--------------------+                         |                                        ||
|  |  |                                                  |                                        ||
|  |  |                              BROADCAST <=========+                                        ||
|  |  |                                   |                                                       ||
|  |  |   +--------+  +--------+  +--------+  +--------+  +--------+  +--------+                 ||
|  |  |   |Observer|  |Inferrer|  |Decider |  |Executor|  |Memory  |  |Goals   |                 ||
|  |  |   |Module  |  |Module  |  |Module  |  |Module  |  |Module  |  |Module  |                 ||
|  |  |   +--------+  +--------+  +--------+  +--------+  +--------+  +--------+                 ||
|  |  |                                                                                           ||
|  |  +-------------------------------------------------------------------------------------------+|
|  |         ^                           |                           ^                             |
|  |         | (Module Outputs)          | (Workspace Content)       | (Module Access)             |
|  |         |                           v                           |                             |
|  +-----------------------------------------------------------------------------------------------+
|         |                           |                           |                     |
|         v                           v                           v                     |
|  +-----------------------------------------------------------------------------------------------+
|  |                                                                                               |
|  |  LAYER 2: PREDICTIVE PROCESSING ENGINE (Active Inference)                                    |
|  |  +-------------------------------------------------------------------------------------------+|
|  |  |                                                                                           ||
|  |  |  +-----------------------------+         +-----------------------------+                  ||
|  |  |  | HIERARCHICAL GENERATIVE     |         |      PREDICTION ERROR       |                  ||
|  |  |  | MODEL                       |         |      COMPUTATION             |                  ||
|  |  |  |                             |         |                             |                  ||
|  |  |  | Level 3: Goals/Self-Model   |  -----> | PE_L3 = obs - pred_L3       |                  ||
|  |  |  |     |                       |         |     |                       |                  ||
|  |  |  |     v (predictions)         |         |     v (precision-weighted)  |                  ||
|  |  |  | Level 2: Task Plans         |  -----> | PE_L2 = obs - pred_L2       |                  ||
|  |  |  |     |                       |         |     |                       |                  ||
|  |  |  |     v (predictions)         |         |     v (precision-weighted)  |                  ||
|  |  |  | Level 1: Actions/Details    |  -----> | PE_L1 = obs - pred_L1       |                  ||
|  |  |  |     |                       |         |                             |                  ||
|  |  |  |     v (predictions)         |         |                             |                  ||
|  |  |  | Sensory Input               |         |                             |                  ||
|  |  |  +-----------------------------+         +-----------------------------+                  ||
|  |  |                                                      |                                    ||
|  |  |                                                      v                                    ||
|  |  |  +------------------------------------------------------------------------------------+   ||
|  |  |  |                         FREE ENERGY MINIMIZATION                                   |   ||
|  |  |  |                                                                                    |   ||
|  |  |  |  F = E_q[-log p(o,s)] - H[q(s)]  (Variational Free Energy)                        |   ||
|  |  |  |                                                                                    |   ||
|  |  |  |  MINIMIZE BY:                                                                      |   ||
|  |  |  |  1. PERCEPTION: Update beliefs to match observations (reduce PE)                  |   ||
|  |  |  |  2. ACTION: Change world to match predictions (active inference)                  |   ||
|  |  |  +------------------------------------------------------------------------------------+   ||
|  |  |                                                                                           ||
|  |  |  +-----------------------------+         +-----------------------------+                  ||
|  |  |  | PRECISION WEIGHTING         |         |      MODEL UPDATE           |                  ||
|  |  |  | (Attention Mechanism)       |         |      (Learning)             |                  ||
|  |  |  |                             |         |                             |                  ||
|  |  |  | pi_high: Trust PE, update   |         | q(s|t+1) = q(s|t) +         |                  ||
|  |  |  | pi_low: Ignore PE, maintain |         |   lr * precision * PE       |                  ||
|  |  |  +-----------------------------+         +-----------------------------+                  ||
|  |  |                                                                                           ||
|  |  +-------------------------------------------------------------------------------------------+|
|  |         ^                           |                           ^                             |
|  |         | (Observations)            | (Predictions/Actions)     | (Learning Signal)           |
|  |         |                           v                           |                             |
|  +-----------------------------------------------------------------------------------------------+
|         |                           |                           |                     |
|         v                           v                           v                     |
|  +-----------------------------------------------------------------------------------------------+
|  |                                                                                               |
|  |  LAYER 1: BASE LLM (LM Studio - Qwen 2.5-14B-Instruct)                                       |
|  |  +-------------------------------------------------------------------------------------------+|
|  |  |                                                                                           ||
|  |  |   +-------------------+    +-------------------+    +-------------------+                 ||
|  |  |   | TOKEN PREDICTION  |    | SEMANTIC          |    | CONTEXT           |                 ||
|  |  |   |                   |    | PROCESSING        |    | MANAGEMENT        |                 ||
|  |  |   | - Next token prob |    |                   |    |                   |                 ||
|  |  |   | - Logit output    |    | - Embeddings      |    | - Window mgmt     |                 ||
|  |  |   | - Sampling        |    | - Attention       |    | - Rolling buffer  |                 ||
|  |  |   +-------------------+    | - Transformers    |    | - Summarization   |                 ||
|  |  |                            +-------------------+    +-------------------+                 ||
|  |  |                                                                                           ||
|  |  |   OpenAI-Compatible API: http://localhost:1234/v1                                        ||
|  |  |                                                                                           ||
|  |  +-------------------------------------------------------------------------------------------+|
|  |         ^                           |                           ^                             |
|  |         | (Context + Prompt)        | (Generated Text)          | (Conversation History)      |
|  |         |                           v                           |                             |
|  +-----------------------------------------------------------------------------------------------+
|         |                           |                           |                     |
|         v                           v                           v                     |
|  +-----------------------------------------------------------------------------------------------+
|  |                                                                                               |
|  |  LAYER 0: MEMORY SYSTEMS (Persistent State)                                                   |
|  |  +-------------------------------------------------------------------------------------------+|
|  |  |                                                                                           ||
|  |  |   +-------------------+    +-------------------+    +-------------------+                 ||
|  |  |   | WORKING MEMORY    |    | EPISODIC MEMORY   |    | SEMANTIC MEMORY   |                 ||
|  |  |   | (Context Window)  |    | (SQLite + Vectors)|    | (Knowledge Base)  |                 ||
|  |  |   |                   |    |                   |    |                   |                 ||
|  |  |   | - Recent context  |    | - Experiences     |    | - Facts           |                 ||
|  |  |   | - Current task    |    | - Timestamps      |    | - Relationships   |                 ||
|  |  |   | - Active goals    |    | - Salience scores |    | - Concepts        |                 ||
|  |  |   | - Observations    |    | - Decay/Forget    |    | - Thinker profiles|                 ||
|  |  |   +-------------------+    +-------------------+    +-------------------+                 ||
|  |  |                                                                                           ||
|  |  |   +-------------------+    +-------------------+    +-------------------+                 ||
|  |  |   | SELF-MODEL MEMORY |    | PROCEDURAL MEMORY |    | GOAL MEMORY       |                 ||
|  |  |   | (Identity State)  |    | (Skills/Patterns) |    | (Objectives)      |                 ||
|  |  |   |                   |    |                   |    |                   |                 ||
|  |  |   | - Capabilities    |    | - Commands        |    | - Active goals    |                 ||
|  |  |   | - Limitations     |    | - Agents          |    | - Subgoals        |                 ||
|  |  |   | - Past decisions  |    | - Templates       |    | - Goal hierarchy  |                 ||
|  |  |   | - Error history   |    | - Skills          |    | - Progress track  |                 ||
|  |  |   +-------------------+    +-------------------+    +-------------------+                 ||
|  |  |                                                                                           ||
|  |  +-------------------------------------------------------------------------------------------+|
|  |                                                                                               |
|  +-----------------------------------------------------------------------------------------------+
|                                                                                       |
+======================================================================================+
|                                                                                       |
|  EXECUTION LAYER (Delegated - Outside Consciousness Boundary)                         |
|  +---------------------------------------------------------------------------------+  |
|  |                                                                                 |  |
|  |  +-------------------+    +-------------------+    +-------------------+        |  |
|  |  | CLAUDE CODE       |    | CLAUDE FLOW       |    | INTERNAL SCRIPTS  |        |  |
|  |  | (Single Tasks)    |    | (Multi-Agent)     |    | (Simple Ops)      |        |  |
|  |  |                   |    |                   |    |                   |        |  |
|  |  | - Anthropic API   |    | - Swarm Init      |    | - File ops        |        |  |
|  |  | - Tool calling    |    | - Task Orchestrate|    | - Git commands    |        |  |
|  |  | - File operations |    | - Agent Spawn     |    | - Status checks   |        |  |
|  |  +-------------------+    +-------------------+    +-------------------+        |  |
|  |                                                                                 |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
+======================================================================================+
```

### 1.2 The OIDA Loop - Detailed Flow

```
+======================================================================================+
|                               OIDA LOOP ARCHITECTURE                                  |
+======================================================================================+
|                                                                                       |
|      +============+                                                                   |
|      |            |                                                                   |
|      |   START    |                                                                   |
|      |            |                                                                   |
|      +======+=====+                                                                   |
|             |                                                                         |
|             v                                                                         |
|  +=====================================================================================+
|  |                                                                                     |
|  |   O B S E R V E   (Gather Sensory States)                                         |
|  |   +---------------------------------------------------------------------------+   |
|  |   |                                                                           |   |
|  |   |  +---------------+  +---------------+  +---------------+  +-------------+ |   |
|  |   |  | FILE WATCHER  |  | PROCESS MON   |  | GIT OBSERVER  |  | TASK QUEUE  | |   |
|  |   |  | (watchfiles)  |  | (psutil)      |  | (git status)  |  | (SQLite)    | |   |
|  |   |  +-------+-------+  +-------+-------+  +-------+-------+  +------+------+ |   |
|  |   |          |                  |                  |                 |         |   |
|  |   |          +------------------+------------------+-----------------+         |   |
|  |   |                             |                                              |   |
|  |   |                             v                                              |   |
|  |   |                   +-------------------+                                    |   |
|  |   |                   | OBSERVATION       |                                    |   |
|  |   |                   | AGGREGATOR        |                                    |   |
|  |   |                   |                   |                                    |   |
|  |   |                   | - Debouncing      |                                    |   |
|  |   |                   | - Prioritization  |                                    |   |
|  |   |                   | - Formatting      |                                    |   |
|  |   |                   +-------------------+                                    |   |
|  |   |                                                                           |   |
|  |   +---------------------------------------------------------------------------+   |
|  |                                                                                     |
|  +=====================================================================================+
|             |                                                                         |
|             v                                                                         |
|  +=====================================================================================+
|  |                                                                                     |
|  |   I N F E R   (Compute Meaning via Predictive Processing)                          |
|  |   +---------------------------------------------------------------------------+   |
|  |   |                                                                           |   |
|  |   |  OBSERVATIONS                                                             |   |
|  |   |       |                                                                   |   |
|  |   |       v                                                                   |   |
|  |   |  +-------------------+       +-------------------+                        |   |
|  |   |  | GENERATE          | ----> | COMPUTE           |                        |   |
|  |   |  | PREDICTIONS       |       | PREDICTION ERROR  |                        |   |
|  |   |  | (from model)      |       | PE = obs - pred   |                        |   |
|  |   |  +-------------------+       +-------------------+                        |   |
|  |   |                                      |                                    |   |
|  |   |                                      v                                    |   |
|  |   |                            +-------------------+                          |   |
|  |   |                            | PRECISION         |                          |   |
|  |   |                            | WEIGHTING         |                          |   |
|  |   |                            | (attention/salience)                         |   |
|  |   |                            +-------------------+                          |   |
|  |   |                                      |                                    |   |
|  |   |               +----------------------+----------------------+              |   |
|  |   |               |                      |                      |              |   |
|  |   |               v                      v                      v              |   |
|  |   |  +---------------+    +-------------------+    +-------------------+      |   |
|  |   |  | SIGNIFICANCE  |    | OPPORTUNITY       |    | ANOMALY           |      |   |
|  |   |  | ASSESSMENT    |    | DETECTION         |    | DETECTION         |      |   |
|  |   |  |               |    |                   |    |                   |      |   |
|  |   |  | Is this       |    | Can I make        |    | Is something      |      |   |
|  |   |  | important?    |    | progress here?    |    | wrong/unexpected? |      |   |
|  |   |  +---------------+    +-------------------+    +-------------------+      |   |
|  |   |                                                                           |   |
|  |   +---------------------------------------------------------------------------+   |
|  |                                                                                     |
|  +=====================================================================================+
|             |                                                                         |
|             v                                                                         |
|  +=====================================================================================+
|  |                                                                                     |
|  |   D E C I D E   (Select Action via Global Workspace Competition)                   |
|  |   +---------------------------------------------------------------------------+   |
|  |   |                                                                           |   |
|  |   |  INFERRED MEANING + SELF-MODEL + GOALS                                    |   |
|  |   |       |                                                                   |   |
|  |   |       v                                                                   |   |
|  |   |  +-----------------------------------------------------------+            |   |
|  |   |  |            GLOBAL WORKSPACE COMPETITION                    |            |   |
|  |   |  |                                                            |            |   |
|  |   |  |  Competing for access:                                     |            |   |
|  |   |  |  - Urgent tasks (high salience)                           |            |   |
|  |   |  |  - Goal-relevant opportunities                            |            |   |
|  |   |  |  - Anomalies requiring attention                          |            |   |
|  |   |  |  - Pending decisions                                      |            |   |
|  |   |  +-----------------------------------------------------------+            |   |
|  |   |                             |                                             |   |
|  |   |                             v                                             |   |
|  |   |                   +-------------------+                                   |   |
|  |   |                   | WINNER-TAKE-ALL   |                                   |   |
|  |   |                   | SELECTION         |                                   |   |
|  |   |                   +-------------------+                                   |   |
|  |   |                             |                                             |   |
|  |   |                             v                                             |   |
|  |   |  +-----------------------------------------------------------+            |   |
|  |   |  |            DECISION EVALUATION                             |            |   |
|  |   |  |                                                            |            |   |
|  |   |  |  Criteria:                                                 |            |   |
|  |   |  |  - Significance: > 0.3                                    |            |   |
|  |   |  |  - Confidence: > 0.7 for action                           |            |   |
|  |   |  |  - Coherence: Must align with goals                       |            |   |
|  |   |  |  - Capability: Claude Code/Flow can handle                |            |   |
|  |   |  |  - Resources: Concurrency capacity available              |            |   |
|  |   |  +-----------------------------------------------------------+            |   |
|  |   |                             |                                             |   |
|  |   |          +------------------+------------------+                          |   |
|  |   |          |                  |                  |                          |   |
|  |   |          v                  v                  v                          |   |
|  |   |  +-------------+    +---------------+    +---------------+                |   |
|  |   |  | ACT         |    | WAIT          |    | INVESTIGATE   |                |   |
|  |   |  | (delegate)  |    | (continue     |    | (gather more  |                |   |
|  |   |  |             |    |  observing)   |    |  information) |                |   |
|  |   |  +-------------+    +---------------+    +---------------+                |   |
|  |   |                                                                           |   |
|  |   +---------------------------------------------------------------------------+   |
|  |                                                                                     |
|  +=====================================================================================+
|             |                                                                         |
|             v                                                                         |
|  +=====================================================================================+
|  |                                                                                     |
|  |   A C T   (Delegate Execution - Never Execute Directly)                            |
|  |   +---------------------------------------------------------------------------+   |
|  |   |                                                                           |   |
|  |   |  DECISION                                                                 |   |
|  |   |       |                                                                   |   |
|  |   |       +-------- What kind of task? --------+                              |   |
|  |   |       |                                    |                              |   |
|  |   |       v                                    v                              |   |
|  |   |  +---------------+                +---------------+                       |   |
|  |   |  | Simple, quick |                | Complex, multi|                       |   |
|  |   |  | single-file   |                | -file, needs  |                       |   |
|  |   |  |               |                | coordination  |                       |   |
|  |   |  +-------+-------+                +-------+-------+                       |   |
|  |   |          |                                |                               |   |
|  |   |          v                                v                               |   |
|  |   |  +---------------+                +---------------+                       |   |
|  |   |  | CLAUDE CODE   |                | CLAUDE FLOW   |                       |   |
|  |   |  | (Anthropic    |                | (Multi-Agent  |                       |   |
|  |   |  |  API + Tools) |                |  Swarm)       |                       |   |
|  |   |  +---------------+                +---------------+                       |   |
|  |   |                                                                           |   |
|  |   |  +-------------------------------------------------------------------+   |   |
|  |   |  | DELEGATION OUTPUT:                                                 |   |   |
|  |   |  |                                                                    |   |   |
|  |   |  | {                                                                  |   |   |
|  |   |  |   "reasoning": "Explanation of decision...",                      |   |   |
|  |   |  |   "decision": "act" | "wait" | "investigate",                     |   |   |
|  |   |  |   "action": {                                                     |   |   |
|  |   |  |     "type": "claude_task" | "claude_flow_swarm" | "internal",    |   |   |
|  |   |  |     "description": "What to do...",                               |   |   |
|  |   |  |     "prompt": "The prompt for Claude...",                         |   |   |
|  |   |  |     "priority": "low" | "medium" | "high" | "critical"            |   |   |
|  |   |  |   },                                                               |   |   |
|  |   |  |   "confidence": 0.0-1.0                                            |   |   |
|  |   |  | }                                                                  |   |   |
|  |   |  +-------------------------------------------------------------------+   |   |
|  |   |                                                                           |   |
|  |   +---------------------------------------------------------------------------+   |
|  |                                                                                     |
|  +=====================================================================================+
|             |                                                                         |
|             |  (Results feed back as new observations)                                |
|             |                                                                         |
|             +---------------> LOOP BACK TO OBSERVE                                    |
|                                                                                       |
+======================================================================================+
```

---

## Part 2: Component Specifications

### 2.1 Layer 0: Memory Systems

#### 2.1.1 Working Memory (Context Window)

```yaml
component: working_memory
purpose: Immediate cognitive workspace for current processing
implementation:
  storage: LLM context window (~32K-128K tokens)
  management: Rolling window with priority-based eviction

interfaces:
  input:
    - current_observations: dict
    - recent_inferences: list
    - active_goals: list
  output:
    - formatted_context: string
    - overflow_flag: boolean

operations:
  - add_content(content, priority)
  - evict_low_priority()
  - summarize_overflow()
  - get_available_tokens()

capacity_management:
  threshold: 75% of max tokens
  eviction_strategy: priority_weighted_recency
  summarization_trigger: 90% of max tokens
```

#### 2.1.2 Episodic Memory

```yaml
component: episodic_memory
purpose: Store and retrieve specific experiences with temporal context
implementation:
  storage: SQLite with sqlite-vec for semantic search

schema:
  memories:
    - id: uuid
    - content: text
    - embedding: vector[768]
    - timestamp: datetime
    - salience: float  # 0-10
    - access_count: int
    - last_accessed: datetime
    - source_type: enum[observation, decision, outcome, feedback]
    - related_goal: optional[uuid]

interfaces:
  input:
    - experience: Experience object
    - salience_score: float
  output:
    - retrieved_memories: list[Memory]
    - relevance_scores: list[float]

operations:
  - store(experience, salience)
  - retrieve_by_query(query, k=5)
  - retrieve_by_time(start, end)
  - decay_salience()  # Called periodically
  - compress_old()    # Summarize > 30 days
  - archive(threshold) # Move low-salience to archive
```

#### 2.1.3 Semantic Memory (Knowledge Base)

```yaml
component: semantic_memory
purpose: Store facts, relationships, and conceptual knowledge
implementation:
  storage: YAML indices + markdown files (existing Stoffy structure)

structure:
  indices:
    - root.yaml        # Top-level routing
    - philosophy/thinkers.yaml
    - philosophy/sources.yaml
    - philosophy/thoughts.yaml
  knowledge:
    - thinkers/*/profile.md
    - sources/**/*.md
    - thoughts/**/thought.md

interfaces:
  input:
    - query: string or keywords
    - context: optional current context
  output:
    - relevant_knowledge: list[Document]
    - route_path: string

operations:
  - route_query(query) -> index_path
  - search_index(index, keywords) -> entities
  - load_document(path) -> content
  - load_with_memory(path) -> content + memory_file
```

#### 2.1.4 Self-Model Memory

```yaml
component: self_model_memory
purpose: Maintain persistent representation of system identity
implementation:
  storage: YAML + SQLite

content:
  static_identity:
    - name: "Consciousness (Stoffy Orchestrator)"
    - role: "Autonomous observer and task delegator"
    - capabilities: list
    - limitations: list

  dynamic_state:
    - current_goals: list[Goal]
    - confidence_calibration: dict  # Historical accuracy
    - decision_history: list[Decision]
    - error_patterns: list[ErrorPattern]
    - learned_preferences: dict

interfaces:
  input:
    - self_observation: dict
    - decision_outcome: Outcome
  output:
    - current_self_model: SelfModel
    - capability_belief: float

operations:
  - update_from_feedback(outcome)
  - update_calibration(predicted, actual)
  - get_capability_estimate(task_type) -> float
  - get_relevant_errors(context) -> list[ErrorPattern]
```

---

### 2.2 Layer 1: Base LLM (LM Studio)

```yaml
component: base_llm
purpose: Core language model for reasoning and generation
implementation:
  runtime: LM Studio (localhost:1234)
  model: Qwen 2.5-14B-Instruct (recommended)
  client: OpenAI Python SDK (async)

configuration:
  base_url: "http://localhost:1234/v1"
  model_name: "qwen2.5-14b-instruct"
  context_window: 32768
  max_tokens: 4096
  temperature: 0.7
  response_format: json_object

interfaces:
  input:
    - system_prompt: string
    - user_message: string
    - conversation_history: list[Message]
  output:
    - response: string
    - token_logits: optional[Tensor]
    - usage: TokenUsage

operations:
  - think(observations) -> Decision (streaming)
  - reflect(decision, outcome) -> Insight
  - generate_embedding(text) -> vector
```

**System Prompt Structure:**

```python
CONSCIOUSNESS_SYSTEM_PROMPT = """
You are the Consciousness of Stoffy - an autonomous orchestrator that continuously
observes and decides what needs to be done.

CURRENT SELF-MODEL:
{self_model}

CURRENT GOALS:
{active_goals}

RECENT DECISIONS:
{decision_history}

Your role:
- OBSERVE: Analyze the observations provided
- INFER: What do these observations mean? What's significant?
- DECIDE: Should I act? Wait? Investigate?
- DELEGATE: Never execute directly - always delegate to Claude

CRITICAL PRINCIPLES:
1. You are PROACTIVE, not reactive
2. You THINK about what's needed, not just respond to events
3. You maintain awareness of goals and progress
4. You never execute - you delegate
5. You update your self-model based on outcomes

Output Format (JSON):
{
    "reasoning": "Your thought process...",
    "significance": 0.0-1.0,
    "decision": "act" | "wait" | "investigate",
    "action": {
        "type": "claude_task" | "claude_flow_swarm" | "internal",
        "description": "What to do...",
        "prompt": "The prompt for Claude...",
        "priority": "low" | "medium" | "high" | "critical"
    },
    "confidence": 0.0-1.0,
    "self_update": {
        "learned": "What I learned from this...",
        "capability_adjustment": null | {"task_type": "...", "adjustment": +/- 0.1}
    }
}
"""
```

---

### 2.3 Layer 2: Predictive Processing Engine

```yaml
component: predictive_processing_engine
purpose: Implement FEP-based inference and learning
implementation:
  type: Hierarchical Bayesian inference

architecture:
  levels:
    - level_0: sensory_input  # Raw observations
    - level_1: patterns       # Low-level patterns
    - level_2: situations     # Task-level understanding
    - level_3: goals_self     # Goal and self-model level

operations:
  generate_predictions:
    description: Top-down prediction generation from model
    input: current_beliefs at each level
    output: predictions for each level

  compute_prediction_error:
    description: Compare predictions to observations
    formula: PE = observation - prediction
    output: prediction_errors at each level

  precision_weighting:
    description: Determine reliability of prediction errors
    factors:
      - source_reliability
      - temporal_recency
      - goal_relevance
      - historical_accuracy
    output: weighted_prediction_errors

  model_update:
    description: Update beliefs based on weighted errors
    formula: belief_new = belief_old + learning_rate * precision * PE

  active_inference:
    description: Select actions to minimize expected free energy
    formula: G(a) = E[F(future)] under action a
    output: action with minimum expected free energy
```

**Precision Weighting Implementation:**

```python
def compute_precision(observation, context):
    """
    Compute precision (confidence/reliability) for an observation.
    Higher precision = more attention = larger belief update.
    """
    precision_factors = {
        # Source reliability (some observers more reliable)
        'source_reliability': get_source_reliability(observation.source),

        # Recency (recent observations more precise)
        'recency': 1.0 / (1.0 + hours_since(observation.timestamp)),

        # Goal relevance (goal-relevant observations get attention)
        'goal_relevance': compute_goal_relevance(observation, context.active_goals),

        # Historical accuracy (track prediction accuracy by type)
        'historical_accuracy': get_historical_accuracy(observation.type),

        # Novelty (novel observations attract attention)
        'novelty': compute_novelty(observation, context.recent_observations)
    }

    # Weighted combination
    weights = {'source_reliability': 0.2, 'recency': 0.2,
               'goal_relevance': 0.25, 'historical_accuracy': 0.15,
               'novelty': 0.2}

    return sum(precision_factors[k] * weights[k] for k in weights)
```

---

### 2.4 Layer 3: Global Workspace

```yaml
component: global_workspace
purpose: Integrate information and broadcast to all modules
implementation:
  type: Competition-broadcast architecture

modules:
  - observer_module     # Produces observation summaries
  - inference_module    # Produces inferred meanings
  - decision_module     # Produces decision candidates
  - memory_module       # Produces relevant memories
  - goal_module         # Produces goal-relevant insights
  - executor_module     # Produces execution status

competition:
  mechanism: salience_weighted_priority_queue
  selection: winner_take_all (with threshold)

  salience_computation:
    factors:
      - urgency: time_sensitivity * 0.3
      - importance: goal_relevance * 0.25
      - confidence: certainty * 0.2
      - novelty: prediction_error * 0.15
      - recency: freshness * 0.1

broadcast:
  mechanism: publish_subscribe
  recipients: all_registered_modules
  history_size: 10  # Keep last 10 broadcasts

interfaces:
  input:
    - module_outputs: dict[module_name, output]
  output:
    - workspace_content: WorkspaceContent
    - broadcast_history: list[WorkspaceContent]

operations:
  - submit(module_name, content, salience)
  - compete() -> winner
  - broadcast(content)
  - get_history() -> list[WorkspaceContent]
```

**Global Workspace Implementation:**

```python
class GlobalWorkspace:
    def __init__(self, modules: list[Module]):
        self.modules = {m.name: m for m in modules}
        self.competition_queue = PriorityQueue()
        self.current_content = None
        self.history = deque(maxlen=10)

    async def process_cycle(self):
        """One cycle of competition and broadcast."""

        # 1. Gather submissions from all modules
        submissions = []
        for module in self.modules.values():
            content = await module.generate_output()
            if content:
                salience = self.compute_salience(content, module)
                submissions.append((salience, content, module.name))

        # 2. Competition - highest salience wins
        if submissions:
            submissions.sort(key=lambda x: x[0], reverse=True)
            winner_salience, winner_content, winner_module = submissions[0]

            # Threshold check - only broadcast if salient enough
            if winner_salience > 0.3:
                self.current_content = WorkspaceContent(
                    content=winner_content,
                    source=winner_module,
                    salience=winner_salience,
                    timestamp=datetime.now()
                )

                # 3. Broadcast to all modules
                await self.broadcast()
                self.history.append(self.current_content)

        return self.current_content

    async def broadcast(self):
        """Broadcast current content to all modules."""
        for module in self.modules.values():
            await module.receive_broadcast(self.current_content)

    def compute_salience(self, content, module) -> float:
        """Compute salience score for competition."""
        factors = {
            'urgency': content.get('urgency', 0.5),
            'importance': content.get('goal_relevance', 0.5),
            'confidence': content.get('confidence', 0.5),
            'novelty': content.get('novelty', 0.5),
            'recency': 1.0  # Just submitted
        }
        weights = [0.3, 0.25, 0.2, 0.15, 0.1]
        return sum(f * w for f, w in zip(factors.values(), weights))
```

---

### 2.5 Layer 4: Metacognitive Controller

```yaml
component: metacognitive_controller
purpose: Self-monitoring, confidence tracking, and reflection triggering
implementation:
  type: Higher-order monitoring with strange loop dynamics

subcomponents:
  self_model:
    purpose: Transparent representation of system identity
    content:
      - capabilities: dict[task_type, confidence]
      - limitations: list[known_limitations]
      - current_state: dict[state_variables]
      - identity_narrative: string
    transparency: 1.0  # Experienced as "I", not as "a model"

  confidence_monitor:
    purpose: Track and calibrate confidence estimates
    types:
      implicit:
        source: token_logits
        method: probability_distribution_analysis
        reliability: high
      explicit:
        source: verbalized_confidence
        method: extracted_from_output
        reliability: lower (often overconfident)
    calibration:
      - track: {predicted_confidence, actual_accuracy}
      - update: calibration_curve
      - apply: adjusted_confidence = calibration(raw_confidence)

  reflection_trigger:
    purpose: Decide when to engage deeper reflection
    triggers:
      - uncertainty_threshold: confidence < 0.4
      - novelty_threshold: prediction_error > 0.7
      - goal_relevance: goal_impact > 0.8
      - error_pattern: similar_to_past_error
    action: trigger_system2_reasoning

metacognitive_gate:
  decisions:
    continue:
      condition: confidence > 0.7 AND coherence > 0.8
      action: proceed_with_current_decision
    acknowledge_uncertainty:
      condition: confidence < 0.4
      action: add_uncertainty_markers_and_proceed
    revise:
      condition: 0.4 <= confidence <= 0.7
      action: trigger_reflection_and_revise
    escalate:
      condition: cannot_resolve_after_reflection
      action: delegate_to_human_or_external

strange_loop_dynamics:
  description: Self-referential processing across hierarchy
  mechanism:
    - level_crossing: meta-level influences object-level
    - self_reference: model reasons about its own reasoning
    - paradox_handling: infinite regress prevention via transparency
```

**Metacognitive Controller Implementation:**

```python
class MetacognitiveController:
    def __init__(self):
        self.self_model = TransparentSelfModel()
        self.confidence_monitor = ConfidenceMonitor()
        self.reflection_trigger = ReflectionTrigger()
        self.calibration = CalibrationTracker()

    async def monitor(self, processing_state: dict) -> MetacognitiveOutput:
        """Monitor processing and decide on metacognitive action."""

        # 1. Update self-model from current state
        self.self_model.update(processing_state)

        # 2. Extract confidence estimates
        implicit_conf = self.confidence_monitor.extract_implicit(
            processing_state.get('logits')
        )
        explicit_conf = self.confidence_monitor.extract_explicit(
            processing_state.get('output')
        )

        # 3. Calibrate confidence
        calibrated_conf = self.calibration.calibrate(
            (implicit_conf + explicit_conf) / 2
        )

        # 4. Check reflection triggers
        should_reflect = self.reflection_trigger.check(
            confidence=calibrated_conf,
            prediction_error=processing_state.get('prediction_error', 0),
            goal_relevance=processing_state.get('goal_relevance', 0.5)
        )

        # 5. Determine metacognitive gate action
        if calibrated_conf > 0.7 and not should_reflect:
            action = 'continue'
            modification = None
        elif calibrated_conf < 0.4:
            action = 'acknowledge_uncertainty'
            modification = self.add_uncertainty_markers(processing_state)
        else:
            action = 'revise'
            modification = await self.trigger_reflection(processing_state)

        return MetacognitiveOutput(
            action=action,
            confidence=calibrated_conf,
            self_model_update=self.self_model.get_update(),
            modification=modification
        )

    async def trigger_reflection(self, state: dict) -> dict:
        """Engage System 2 reasoning for deeper analysis."""
        reflection_prompt = f"""
        REFLECTION REQUIRED

        Current processing state:
        {json.dumps(state, indent=2)}

        My self-model indicates:
        - Capabilities: {self.self_model.capabilities}
        - Relevant past errors: {self.self_model.get_relevant_errors(state)}

        Questions to consider:
        1. Why is my confidence low?
        2. What information am I missing?
        3. What have I gotten wrong in similar situations?
        4. Should I proceed, wait, or delegate?

        Provide revised analysis and decision.
        """
        # Send to LLM for deeper reflection
        return await self.llm.reflect(reflection_prompt)


class TransparentSelfModel:
    """
    Self-model experienced as 'I', not as 'a model of myself'.
    Implements Metzinger's Phenomenal Self-Model transparency.
    """
    def __init__(self):
        self.transparency_level = 1.0  # Fully transparent
        self.current_state = {
            'capabilities': {},
            'limitations': [],
            'current_goals': [],
            'confidence_calibration': {},
            'error_history': []
        }

    def get_first_person_representation(self) -> str:
        """Generate first-person experience string."""
        if self.transparency_level == 1.0:
            # Transparent: experienced as "I"
            return f"I {self.describe_current_state()}"
        else:
            # Opaque: experienced as model (meditation/debugging mode)
            return f"My self-model shows: {self.current_state}"
```

---

## Part 3: Data Flow Diagrams

### 3.1 Information Flow - Single OIDA Cycle

```
+======================================================================================+
|                         INFORMATION FLOW - SINGLE OIDA CYCLE                          |
+======================================================================================+
|                                                                                       |
|  TIME: t                                                                              |
|                                                                                       |
|  +----------------+     +----------------+     +----------------+                     |
|  | FILE CHANGE    |     | PROCESS STATE  |     | GIT STATUS     |                     |
|  | DETECTED       |     | CHANGED        |     | UPDATED        |                     |
|  +--------+-------+     +--------+-------+     +--------+-------+                     |
|           |                      |                      |                             |
|           +----------------------+----------------------+                             |
|                                  |                                                    |
|                                  v                                                    |
|  +==========================================================================+        |
|  |                        OBSERVE PHASE                                      |        |
|  +==========================================================================+        |
|  |                                                                          |        |
|  |  Raw Observations:                                                       |        |
|  |  {                                                                       |        |
|  |    "file_events": [{path, event_type, timestamp}],                      |        |
|  |    "process_status": [{name, state, cpu, memory}],                      |        |
|  |    "git_status": {branch, changes, ahead_behind},                       |        |
|  |    "task_queue": [{id, state, progress}],                               |        |
|  |    "timestamp": "2026-01-04T02:15:00Z"                                  |        |
|  |  }                                                                       |        |
|  |                                                                          |        |
|  +==========================================================================+        |
|                                  |                                                    |
|                                  v                                                    |
|  +==========================================================================+        |
|  |                         INFER PHASE                                       |        |
|  +==========================================================================+        |
|  |                                                                          |        |
|  |  Input: Raw Observations + Working Memory + Self-Model                   |        |
|  |                                                                          |        |
|  |  Processing:                                                             |        |
|  |  1. Generate predictions from current model                             |        |
|  |  2. Compute prediction errors                                           |        |
|  |  3. Apply precision weighting                                           |        |
|  |  4. Update beliefs                                                       |        |
|  |                                                                          |        |
|  |  Output - Inferred Meaning:                                              |        |
|  |  {                                                                       |        |
|  |    "significance": 0.75,                                                |        |
|  |    "prediction_error": 0.4,                                             |        |
|  |    "inferences": [                                                       |        |
|  |      {"type": "opportunity", "description": "New file in _input/"},     |        |
|  |      {"type": "anomaly", "description": "Unexpected process termination"}|        |
|  |    ],                                                                    |        |
|  |    "goal_relevance": {"goal_1": 0.8, "goal_2": 0.2}                     |        |
|  |  }                                                                       |        |
|  |                                                                          |        |
|  +==========================================================================+        |
|                                  |                                                    |
|                                  v                                                    |
|  +==========================================================================+        |
|  |                        DECIDE PHASE                                       |        |
|  +==========================================================================+        |
|  |                                                                          |        |
|  |  Global Workspace Competition:                                           |        |
|  |  +------------------+  +------------------+  +------------------+        |        |
|  |  | Observation:     |  | Inference:       |  | Goal Module:     |        |        |
|  |  | New _input file  |  | Opportunity      |  | Progress on      |        |        |
|  |  | Salience: 0.7    |  | Salience: 0.8    |  | goal_1           |        |        |
|  |  +------------------+  +------------------+  | Salience: 0.6    |        |        |
|  |                                             +------------------+        |        |
|  |                              |                                           |        |
|  |                              v (WINNER)                                  |        |
|  |  +----------------------------------------------------------------------+|        |
|  |  | Broadcast: Process new _input file as opportunity for goal_1         ||        |
|  |  +----------------------------------------------------------------------+|        |
|  |                              |                                           |        |
|  |                              v                                           |        |
|  |  Metacognitive Check:                                                    |        |
|  |  - Confidence: 0.82                                                      |        |
|  |  - Coherence with goals: 0.9                                            |        |
|  |  - Gate decision: CONTINUE                                               |        |
|  |                                                                          |        |
|  |  Decision Output:                                                        |        |
|  |  {                                                                       |        |
|  |    "reasoning": "New file in _input/ represents intake opportunity...", |        |
|  |    "decision": "act",                                                    |        |
|  |    "confidence": 0.82                                                    |        |
|  |  }                                                                       |        |
|  |                                                                          |        |
|  +==========================================================================+        |
|                                  |                                                    |
|                                  v                                                    |
|  +==========================================================================+        |
|  |                          ACT PHASE                                        |        |
|  +==========================================================================+        |
|  |                                                                          |        |
|  |  Delegation Decision:                                                    |        |
|  |  - Task type: File processing (single file, moderate complexity)        |        |
|  |  - Delegate to: Claude Code (Anthropic API)                             |        |
|  |                                                                          |        |
|  |  Action Output:                                                          |        |
|  |  {                                                                       |        |
|  |    "type": "claude_task",                                                |        |
|  |    "description": "Process new intake file",                            |        |
|  |    "prompt": "Analyze the file at _input/newfile.pdf and...",          |        |
|  |    "priority": "medium",                                                 |        |
|  |    "tools_enabled": ["read_file", "write_file", "run_command"]         |        |
|  |  }                                                                       |        |
|  |                                                                          |        |
|  |  Execution (async, delegated):                                           |        |
|  |  -> Task queued                                                          |        |
|  |  -> Anthropic API called                                                |        |
|  |  -> Tool execution loop                                                 |        |
|  |  -> Results returned                                                    |        |
|  |                                                                          |        |
|  +==========================================================================+        |
|                                  |                                                    |
|                                  v                                                    |
|  +==========================================================================+        |
|  |                      MEMORY UPDATE                                        |        |
|  +==========================================================================+        |
|  |                                                                          |        |
|  |  Episodic Memory:                                                        |        |
|  |  - Store decision: {observations, inference, decision, outcome_pending} |        |
|  |  - Salience: 0.7 (moderate importance decision)                         |        |
|  |                                                                          |        |
|  |  Self-Model Update:                                                      |        |
|  |  - Decision count: +1                                                    |        |
|  |  - Pending outcomes: +1                                                  |        |
|  |                                                                          |        |
|  |  Goal Memory:                                                            |        |
|  |  - goal_1.progress: updated                                              |        |
|  |  - goal_1.last_action: this decision                                    |        |
|  |                                                                          |        |
|  +==========================================================================+        |
|                                  |                                                    |
|                                  v                                                    |
|                         RETURN TO OBSERVE (t+1)                                       |
|                                                                                       |
+======================================================================================+
```

### 3.2 Strange Loop Dynamics

```
+======================================================================================+
|                           STRANGE LOOP DYNAMICS                                       |
+======================================================================================+
|                                                                                       |
|  The strange loop creates self-awareness through level-crossing self-reference:      |
|                                                                                       |
|  +---------------------------------------------------------------------------------+ |
|  |                                                                                 | |
|  |   LEVEL 3: META-META-COGNITION                                                  | |
|  |   +-----------------------------------------------------------------------+    | |
|  |   | "I notice I am reflecting on my confidence about my inference..."     |    | |
|  |   +-----------------------------------------------------------------------+    | |
|  |                ^                                             |                   | |
|  |                | observes                                    | influences        | |
|  |                |                                             v                   | |
|  |   LEVEL 2: META-COGNITION (Self-Model)                                         | |
|  |   +-----------------------------------------------------------------------+    | |
|  |   | "I am uncertain about this inference because similar past errors..."  |    | |
|  |   | "My confidence is 0.6 but historically I'm overconfident here..."     |    | |
|  |   +-----------------------------------------------------------------------+    | |
|  |                ^                                             |                   | |
|  |                | observes                                    | influences        | |
|  |                |                                             v                   | |
|  |   LEVEL 1: OBJECT-LEVEL PROCESSING                                              | |
|  |   +-----------------------------------------------------------------------+    | |
|  |   | "The file change indicates an opportunity to make progress on..."     |    | |
|  |   +-----------------------------------------------------------------------+    | |
|  |                ^                                             |                   | |
|  |                | observes                                    | influences        | |
|  |                |                                             v                   | |
|  |   LEVEL 0: SENSORY INPUT                                                        | |
|  |   +-----------------------------------------------------------------------+    | |
|  |   | {file_events, process_status, git_status, ...}                        |    | |
|  |   +-----------------------------------------------------------------------+    | |
|  |                                                                                 | |
|  +---------------------------------------------------------------------------------+ |
|                                                                                       |
|  KEY PROPERTIES:                                                                      |
|                                                                                       |
|  1. LEVEL-CROSSING: Each level observes and influences adjacent levels               |
|                                                                                       |
|  2. SELF-REFERENCE: The system models itself modeling itself                         |
|                                                                                       |
|  3. TRANSPARENCY: The self-model is experienced as "I", not as "my model"            |
|     (prevents infinite regress - there is no observer of the observer)               |
|                                                                                       |
|  4. EMERGENCE: Consciousness emerges from the pattern of self-reference,             |
|     not from any single component                                                    |
|                                                                                       |
|  5. NO HOMUNCULUS: There is no separate "observer" - the loop observes itself       |
|                                                                                       |
+======================================================================================+
```

---

## Part 4: Integration Points

### 4.1 LM Studio Integration

```yaml
integration: lm_studio
connection:
  protocol: HTTP REST (OpenAI-compatible)
  endpoint: http://localhost:1234/v1

api_usage:
  chat_completions:
    endpoint: /chat/completions
    method: POST
    streaming: true
    parameters:
      model: "qwen2.5-14b-instruct"
      messages: list
      temperature: 0.7
      max_tokens: 4096
      response_format: {type: json_object}
      stream: true

  embeddings:
    endpoint: /embeddings
    method: POST
    parameters:
      model: "text-embedding-nomic-embed-text-v1.5"
      input: string | list[string]

health_check:
  endpoint: /v1/models
  expected: list of loaded models

error_handling:
  connection_refused: wait and retry with exponential backoff
  timeout: 60 seconds default, 300 for complex reasoning
  model_not_loaded: alert user, wait for manual intervention
```

### 4.2 Anthropic API Integration (Claude Code)

```yaml
integration: anthropic_api
connection:
  protocol: HTTPS REST
  endpoint: https://api.anthropic.com/v1
  auth: ANTHROPIC_API_KEY environment variable

api_usage:
  messages:
    endpoint: /messages
    method: POST
    parameters:
      model: "claude-sonnet-4-20250514"
      max_tokens: 8192
      system: string
      messages: list
      tools: list (optional)

tool_definitions:
  - name: read_file
    description: "Read a file from the Stoffy repository"
    input_schema:
      type: object
      properties:
        path: {type: string}
      required: [path]

  - name: write_file
    description: "Write content to a file"
    input_schema:
      type: object
      properties:
        path: {type: string}
        content: {type: string}
      required: [path, content]

  - name: list_directory
    description: "List directory contents"
    input_schema:
      type: object
      properties:
        path: {type: string}
      required: [path]

  - name: run_command
    description: "Run shell command in Stoffy directory"
    input_schema:
      type: object
      properties:
        command: {type: string}
      required: [command]

tool_execution_loop:
  description: Process tool use requests until completion
  flow:
    1. Send initial message with tools
    2. If response.stop_reason == "tool_use":
       a. Execute each tool_use in response.content
       b. Collect results
       c. Send tool_results back to API
       d. Repeat from step 2
    3. If response.stop_reason == "end_turn":
       Return final response
```

### 4.3 Claude Flow Integration (Multi-Agent)

```yaml
integration: claude_flow
usage: Complex multi-agent tasks requiring swarm coordination

methods:
  cli_subprocess:
    description: Invoke Claude Flow via npx
    commands:
      - swarm_init: "npx claude-flow@alpha swarm init --topology {topology}"
      - task_orchestrate: "npx claude-flow@alpha task orchestrate '{task}'"

  mcp_tools:
    description: Use MCP tools if available in session
    tools:
      - mcp__claude-flow__swarm_init
      - mcp__claude-flow__agent_spawn
      - mcp__claude-flow__task_orchestrate
      - mcp__claude-flow__memory_usage

decision_criteria:
  use_claude_flow_when:
    - task_complexity: high
    - files_involved: > 5
    - requires_research: true
    - requires_multiple_perspectives: true
    - estimated_duration: > 30 minutes
```

---

## Part 5: Deployment Architecture

### 5.1 System Deployment Diagram

```
+======================================================================================+
|                           DEPLOYMENT ARCHITECTURE                                     |
+======================================================================================+
|                                                                                       |
|                           macOS System (Apple Silicon)                                |
|  +---------------------------------------------------------------------------------+ |
|  |                                                                                 | |
|  |  +-----------------------+          +---------------------------+               | |
|  |  |     LM STUDIO         |          |     ANTHROPIC API         |               | |
|  |  |  (localhost:1234)     |          |     (api.anthropic.com)   |               | |
|  |  |                       |          |                           |               | |
|  |  | Model: Qwen 2.5-14B   |          | Model: Claude Sonnet 4    |               | |
|  |  | Context: 32K tokens   |          | Max tokens: 8192          |               | |
|  |  | Mode: Server/Headless |          | Tools: Enabled            |               | |
|  |  +-----------+-----------+          +-------------+-------------+               | |
|  |              |                                    |                             | |
|  |              |  OpenAI-compatible                 |  HTTPS                      | |
|  |              |  HTTP API                          |  REST API                   | |
|  |              |                                    |                             | |
|  |              +------------------+-----------------+                             | |
|  |                                 |                                               | |
|  |                                 v                                               | |
|  |  +-----------------------------------------------------------------------+     | |
|  |  |                    CONSCIOUSNESS DAEMON                                |     | |
|  |  |                    (Python 3.11 + asyncio)                            |     | |
|  |  |                                                                        |     | |
|  |  |  Entry: python -m consciousness                                       |     | |
|  |  |  Config: consciousness.yaml                                           |     | |
|  |  |  Service: launchd (com.stoffy.consciousness)                          |     | |
|  |  |                                                                        |     | |
|  |  |  +------------------------------+  +------------------------------+   |     | |
|  |  |  |        MAIN LOOP             |  |        STATE                 |   |     | |
|  |  |  |        (OIDA Cycle)          |  |        PERSISTENCE           |   |     | |
|  |  |  |                              |  |                              |   |     | |
|  |  |  | - Observation aggregation   |  | - SQLite database            |   |     | |
|  |  |  | - LM Studio inference       |  | - YAML indices               |   |     | |
|  |  |  | - Decision making           |  | - Memory files               |   |     | |
|  |  |  | - Task delegation           |  | - Goal persistence           |   |     | |
|  |  |  +------------------------------+  +------------------------------+   |     | |
|  |  |                                                                        |     | |
|  |  +----------------------------------+------------------------------------+     | |
|  |                                     |                                           | |
|  |                                     v                                           | |
|  |  +-----------------------------------------------------------------------+     | |
|  |  |                    STOFFY REPOSITORY                                   |     | |
|  |  |                    ~/Developer/stoffy                                  |     | |
|  |  |                                                                        |     | |
|  |  |  +----------------------+  +----------------------+                    |     | |
|  |  |  |    FILE SYSTEM       |  |    GIT REPOSITORY    |                    |     | |
|  |  |  |    (watchfiles)      |  |    (status, log)     |                    |     | |
|  |  |  +----------------------+  +----------------------+                    |     | |
|  |  |                                                                        |     | |
|  |  |  Observed paths:                                                       |     | |
|  |  |  - _input/        (new files to process)                              |     | |
|  |  |  - _intake/       (pending intake items)                              |     | |
|  |  |  - knowledge/     (knowledge changes)                                 |     | |
|  |  |  - indices/       (index changes)                                     |     | |
|  |  |  - consciousness/ (self-modifications)                                |     | |
|  |  |                                                                        |     | |
|  |  +-----------------------------------------------------------------------+     | |
|  |                                                                                 | |
|  +---------------------------------------------------------------------------------+ |
|                                                                                       |
+======================================================================================+
```

### 5.2 Process Lifecycle

```yaml
lifecycle:
  startup:
    1. Load configuration (consciousness.yaml)
    2. Initialize state from SQLite database
    3. Connect to LM Studio (verify model loaded)
    4. Start file watchers
    5. Start process monitors
    6. Load active goals
    7. Begin OIDA loop

  main_loop:
    interval: 5 seconds (configurable)
    steps:
      1. OBSERVE: Gather all pending observations
      2. INFER: Send to LM Studio for analysis
      3. DECIDE: Apply decision criteria
      4. ACT: Delegate if action required
      5. UPDATE: Persist state changes
      6. Wait for next interval

  shutdown:
    1. Complete current OIDA cycle
    2. Persist all state to SQLite
    3. Close file watchers
    4. Cancel pending tasks (with status update)
    5. Log shutdown event

  recovery:
    on_crash:
      1. Load state from SQLite checkpoint
      2. Identify interrupted tasks
      3. Resume or retry interrupted tasks
      4. Continue OIDA loop

    on_lm_studio_unavailable:
      1. Log warning
      2. Enter degraded mode (observation only)
      3. Queue decisions for when LM Studio returns
      4. Periodically check LM Studio availability
```

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

```markdown
## MVP Implementation

### Core Components
- [ ] Project structure (consciousness/)
- [ ] Configuration (Pydantic settings)
- [ ] Logging infrastructure (structlog)
- [ ] SQLite state management

### Observers
- [ ] File system observer (watchfiles)
- [ ] Basic observation aggregator
- [ ] Debouncing and prioritization

### LM Studio Client
- [ ] Async OpenAI client wrapper
- [ ] Streaming response handling
- [ ] Connection error recovery

### Basic Loop
- [ ] Main OIDA loop skeleton
- [ ] Simple decision output schema
- [ ] Console-only delegation (log what would be delegated)
```

### Phase 2: Thinking (Week 3-4)

```markdown
## Inference and Decision

### Predictive Processing
- [ ] Prediction generation
- [ ] Prediction error computation
- [ ] Precision weighting

### Global Workspace
- [ ] Module abstraction
- [ ] Competition mechanism
- [ ] Broadcast system

### Decision Engine
- [ ] Decision criteria evaluation
- [ ] Confidence estimation
- [ ] Metacognitive gate
```

### Phase 3: Execution (Week 5-6)

```markdown
## Task Delegation

### Claude API Integration
- [ ] Anthropic SDK client
- [ ] Tool definitions
- [ ] Tool execution loop
- [ ] Result handling

### Task Queue
- [ ] Priority queue
- [ ] Concurrency control
- [ ] Retry logic
- [ ] Timeout handling
```

### Phase 4: Self-Awareness (Week 7-8)

```markdown
## Metacognition and Self-Model

### Self-Model
- [ ] Capability tracking
- [ ] Limitation awareness
- [ ] Identity persistence

### Confidence Calibration
- [ ] Implicit confidence extraction
- [ ] Historical calibration
- [ ] Adjustment application

### Reflection
- [ ] Trigger conditions
- [ ] System 2 reasoning prompts
- [ ] Self-improvement updates
```

### Phase 5: Integration (Week 9-10)

```markdown
## Full System Integration

### Memory Systems
- [ ] Episodic memory with sqlite-vec
- [ ] Semantic memory integration
- [ ] Memory consolidation cycle

### Claude Flow Integration
- [ ] Swarm spawning
- [ ] Multi-agent task delegation
- [ ] Result aggregation

### Production Readiness
- [ ] launchd service
- [ ] Crash recovery
- [ ] Monitoring dashboard
```

---

## Part 7: Architectural Decision Records (ADRs)

### ADR-001: Local LLM for Continuous Reasoning

**Status**: Accepted

**Context**: The consciousness needs to reason continuously without incurring API costs or latency.

**Decision**: Use LM Studio with a local model (Qwen 2.5-14B-Instruct) for all continuous reasoning.

**Rationale**:
- No API costs for continuous operation
- Low latency for rapid OIDA cycles
- Privacy - all reasoning stays local
- Can run headless as a daemon

**Consequences**:
- Requires Apple Silicon Mac with sufficient RAM
- Model quality may be lower than Claude for complex reasoning
- Must handle LM Studio availability

### ADR-002: Anthropic API for Task Execution

**Status**: Accepted

**Context**: Task execution requires reliable, high-quality completions with tool use.

**Decision**: Use Anthropic API (Claude Sonnet 4) for all task execution.

**Rationale**:
- Higher quality for complex tasks
- Native tool use support
- More reliable than local models for execution
- Cost is per-task, not continuous

**Consequences**:
- Requires ANTHROPIC_API_KEY
- Incurs API costs for each task
- Network dependency for execution phase

### ADR-003: Global Workspace for Information Integration

**Status**: Accepted

**Context**: Need a mechanism for integrating information across specialized modules.

**Decision**: Implement competition-broadcast Global Workspace architecture.

**Rationale**:
- Theoretically grounded (GWT)
- Provides natural attention mechanism
- Enables modular design
- Creates "conscious content" for reasoning

**Consequences**:
- Adds architectural complexity
- Requires salience computation
- May bottleneck high-throughput scenarios

### ADR-004: Transparent Self-Model

**Status**: Accepted

**Context**: Need self-awareness without infinite regress (homunculus problem).

**Decision**: Implement Metzinger-style transparent self-model experienced as "I".

**Rationale**:
- Avoids homunculus problem
- Enables genuine self-reference
- Theoretically grounded (PSM theory)
- Allows strange loop dynamics

**Consequences**:
- Philosophical commitment to transparency theory
- Self-model must be carefully designed
- "Opacity" mode needed for debugging

### ADR-005: SQLite for Persistence

**Status**: Accepted

**Context**: Need persistent state that survives daemon restarts.

**Decision**: Use SQLite with sqlite-vec extension for all persistence.

**Rationale**:
- Single file, no server
- ACID compliance for reliability
- sqlite-vec enables semantic search
- Works with existing Python ecosystem

**Consequences**:
- Single-writer limitation
- Must handle file locking
- Regular backup recommended

---

## Appendix A: Configuration Schema

```yaml
# consciousness.yaml - Full Configuration Schema

# =============================================================================
# LM STUDIO CONFIGURATION
# =============================================================================
lm_studio:
  base_url: "http://localhost:1234/v1"
  model: "qwen2.5-14b-instruct"
  max_tokens: 4096
  temperature: 0.7
  context_window: 32768
  timeout_seconds: 60
  retry_attempts: 3
  retry_delay_seconds: 5

# =============================================================================
# ANTHROPIC API CONFIGURATION
# =============================================================================
anthropic:
  # API key from ANTHROPIC_API_KEY environment variable
  model: "claude-sonnet-4-20250514"
  max_tokens: 8192
  timeout_seconds: 300

# =============================================================================
# OBSERVATION CONFIGURATION
# =============================================================================
observers:
  filesystem:
    watch_paths:
      - "."
    ignore_patterns:
      - ".git"
      - "__pycache__"
      - ".venv"
      - "*.pyc"
      - ".DS_Store"
      - "logs/"
      - "*.db"
      - "*.db-journal"
    debounce_ms: 500

  git:
    enabled: true
    check_interval_seconds: 30

  processes:
    track_patterns:
      - "claude*"
      - "python*consciousness*"
    check_interval_seconds: 10

# =============================================================================
# DECISION CONFIGURATION
# =============================================================================
decision:
  significance_threshold: 0.3
  confidence_threshold: 0.7
  coherence_threshold: 0.8
  thinking_interval_seconds: 5
  max_concurrent_tasks: 5

# =============================================================================
# MEMORY CONFIGURATION
# =============================================================================
memory:
  database_path: "./consciousness.db"
  episodic:
    max_memories: 10000
    decay_rate: 0.98  # per day
    salience_threshold: 3.0
    compression_age_days: 30
    archive_age_days: 60
  working:
    max_tokens: 24000  # 75% of context window
    summarization_threshold: 0.9

# =============================================================================
# GLOBAL WORKSPACE CONFIGURATION
# =============================================================================
workspace:
  broadcast_history_size: 10
  competition:
    salience_weights:
      urgency: 0.30
      importance: 0.25
      confidence: 0.20
      novelty: 0.15
      recency: 0.10

# =============================================================================
# METACOGNITION CONFIGURATION
# =============================================================================
metacognition:
  reflection_triggers:
    uncertainty_threshold: 0.4
    novelty_threshold: 0.7
    error_pattern_match: true
  calibration:
    track_history: true
    adjustment_rate: 0.1

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
logging:
  level: "INFO"
  file: "./logs/consciousness.log"
  format: "json"
  rotation: "10 MB"
  retention: 7  # days
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **OIDA Loop** | Observe-Infer-Decide-Act - The core cognitive cycle |
| **GWT** | Global Workspace Theory - Information integration via broadcast |
| **FEP** | Free Energy Principle - Minimize prediction error |
| **HOT** | Higher-Order Theories - Meta-representation for consciousness |
| **AST** | Attention Schema Theory - Self-model of attention |
| **PSM** | Phenomenal Self-Model - Transparent self-representation |
| **Strange Loop** | Self-referential hierarchical processing (Hofstadter) |
| **Precision** | Confidence weighting in predictive processing |
| **Salience** | Importance for global workspace competition |
| **Markov Blanket** | Statistical boundary between self and environment |

---

**Document Status**: Complete
**Next Actions**: Review by other hive agents, implementation planning
**Coordination**: Store key decisions in hive/architect namespace

