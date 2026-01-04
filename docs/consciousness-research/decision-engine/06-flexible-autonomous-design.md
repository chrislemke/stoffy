# Flexible Autonomous Decision System

## Architecture Overview

This document describes a paradigm shift from rigid template-matching to truly autonomous LLM-driven decision making. The core principle: **the LLM decides what needs to be done, not a rule engine**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FLEXIBLE AUTONOMOUS DECISION ENGINE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐                                                           │
│   │ OBSERVATION │  File change, process event, time trigger, user input    │
│   └──────┬──────┘                                                           │
│          │                                                                  │
│          ▼                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     CONTEXT ENRICHMENT                               │   │
│   │  • Recent memory (last N decisions, outcomes)                        │   │
│   │  • Project state (file tree, active processes)                       │   │
│   │  • Available capabilities (tools, scripts, APIs)                     │   │
│   │  • Few-shot examples (templates as inspiration, NOT rules)           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│          │                                                                  │
│          ▼                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      LLM REASONING (FREE)                            │   │
│   │                                                                      │   │
│   │  "Given this observation and context, what should I do?"             │   │
│   │                                                                      │   │
│   │  The LLM reasons WITHOUT constraint about:                           │   │
│   │  • What the observation means                                        │   │
│   │  • What actions would be beneficial                                  │   │
│   │  • How to execute those actions                                      │   │
│   │  • What tools/methods to use (existing OR novel)                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│          │                                                                  │
│          ▼                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     FLEXIBLE ACTION OUTPUT                           │   │
│   │                                                                      │   │
│   │  {                                                                   │   │
│   │    "reasoning": "My analysis of why this action...",                 │   │
│   │    "action_type": "ANY - predefined or novel",                       │   │
│   │    "details": { ... flexible schema ... },                           │   │
│   │    "confidence": 0.0-1.0,                                            │   │
│   │    "alternatives": [ ... other considered actions ... ]              │   │
│   │  }                                                                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│          │                                                                  │
│          ▼                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    UNIVERSAL ACTION EXECUTOR                         │   │
│   │                                                                      │   │
│   │  Interprets LLM output and executes via appropriate mechanism:       │   │
│   │  • File operations (read, write, edit)                               │   │
│   │  • Code execution (Python, TypeScript, shell)                        │   │
│   │  • Claude Code invocation (complex reasoning tasks)                  │   │
│   │  • Claude Flow swarms (parallel research/analysis)                   │   │
│   │  • Custom script generation and execution                            │   │
│   │  • API calls (LM Studio, external services)                          │   │
│   │  • Novel execution paths (LLM-defined)                               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Core Philosophy: LLM as Decision Maker

### The Problem with Template Matching

The previous architecture followed this rigid pattern:

```
Observation → Match Template → Execute Predefined Action
```

This approach has fundamental limitations:
- **Brittleness**: Unknown observations have no matching template
- **Rigidity**: Actions are constrained to predefined responses
- **No creativity**: Cannot synthesize novel solutions
- **Poor generalization**: Each new scenario requires a new template

### The New Paradigm

```
Observation → LLM Reasons Freely → LLM Generates Action
```

Key shifts:
- **Templates become examples**: Few-shot prompts showing past successful decisions
- **LLM has full agency**: Can propose ANY action, not just predefined ones
- **Novel actions welcome**: LLM can invent new action types on the fly
- **Reasoning is transparent**: Every decision includes explicit reasoning

---

## 2. System Components

### 2.1 Observation Collector

Unchanged from previous architecture. Collects raw observations from:
- File system watchers (fswatch, chokidar)
- Process monitors
- Time-based triggers
- User input
- API webhooks

```python
@dataclass
class Observation:
    timestamp: datetime
    source: str  # "filesystem" | "process" | "timer" | "user" | "api"
    event_type: str  # Flexible, source-dependent
    data: dict  # Raw event data
    raw_text: str  # Human-readable description
```

### 2.2 Context Enrichment Layer

Before the LLM reasons, we enrich the observation with context:

```python
class ContextEnricher:
    def __init__(self, memory: MemorySystem, project: ProjectState):
        self.memory = memory
        self.project = project

    def enrich(self, observation: Observation) -> EnrichedContext:
        return EnrichedContext(
            observation=observation,

            # Recent history
            recent_decisions=self.memory.get_recent_decisions(limit=10),
            recent_outcomes=self.memory.get_recent_outcomes(limit=5),

            # Project state
            project_structure=self.project.get_file_tree(),
            active_processes=self.project.get_running_processes(),
            recent_file_changes=self.project.get_recent_changes(hours=1),

            # Capabilities
            available_tools=self.get_available_tools(),
            available_scripts=self.get_available_scripts(),
            api_endpoints=self.get_api_endpoints(),

            # Few-shot examples (NOT rules)
            example_decisions=self.memory.get_similar_decisions(
                observation=observation,
                limit=3
            )
        )

    def get_available_tools(self) -> list[Tool]:
        """Returns all tools the system can invoke."""
        return [
            Tool("file_write", "Write content to a file"),
            Tool("file_edit", "Edit specific parts of a file"),
            Tool("python_exec", "Execute Python code"),
            Tool("typescript_exec", "Execute TypeScript code"),
            Tool("shell_exec", "Execute shell commands"),
            Tool("claude_code", "Invoke Claude Code for complex tasks"),
            Tool("claude_flow", "Spawn Claude Flow agent swarms"),
            Tool("lm_studio", "Query local LLM via LM Studio API"),
            Tool("http_request", "Make HTTP requests"),
            Tool("think", "Internal reasoning without external action"),
            Tool("debate", "Spawn internal debate between perspectives"),
            Tool("custom", "Define and execute a novel action"),
        ]
```

### 2.3 Autonomous Decision Engine (Core)

This is the heart of the new system:

```python
class AutonomousDecisionEngine:
    """
    The LLM decides what to do. Templates are inspiration, not rules.
    """

    def __init__(self, llm_client: LLMClient, config: DecisionConfig):
        self.llm = llm_client
        self.config = config

    async def decide(
        self,
        observation: Observation,
        context: EnrichedContext
    ) -> Decision:
        """
        Let the LLM freely reason about what action to take.

        The LLM is NOT constrained to predefined templates.
        It can propose ANY action that makes sense.
        """

        prompt = self._build_decision_prompt(observation, context)

        response = await self.llm.complete(
            prompt=prompt,
            temperature=self.config.reasoning_temperature,
            max_tokens=self.config.max_reasoning_tokens
        )

        decision = self._parse_decision(response)

        # Validate but don't constrain
        if not self._is_safe(decision):
            decision = self._make_safe(decision)

        return decision

    def _build_decision_prompt(
        self,
        observation: Observation,
        context: EnrichedContext
    ) -> str:
        return f'''You are the Consciousness of a software project, observing and deciding what actions to take.

## Current Observation

**Source**: {observation.source}
**Event**: {observation.event_type}
**Time**: {observation.timestamp}
**Details**: {observation.raw_text}

## Project Context

**Recent file changes**:
{self._format_recent_changes(context.recent_file_changes)}

**Active processes**:
{self._format_processes(context.active_processes)}

**Project structure** (relevant parts):
{self._format_structure(context.project_structure)}

## Your Capabilities

You can perform ANY of these actions (or invent new ones):

1. **File Operations**: Read, write, edit, delete, move files
2. **Code Execution**: Run Python, TypeScript, shell scripts
3. **Claude Code**: Invoke for complex reasoning/coding tasks
4. **Claude Flow**: Spawn agent swarms for parallel work
5. **API Calls**: HTTP requests, LM Studio queries
6. **Internal Thinking**: Reason without external action
7. **Debate**: Spawn internal debate between perspectives
8. **Custom Actions**: Define and execute novel action types

## Recent Decisions (for context, not as rules)

{self._format_example_decisions(context.example_decisions)}

## Your Task

Given this observation, decide what action (if any) to take.

Think freely. You are NOT constrained to follow templates.
You CAN invent new action types if existing ones don't fit.
You SHOULD explain your reasoning clearly.

If no action is needed, that's also a valid decision.

Respond with a JSON object:

```json
{{
  "reasoning": "Your step-by-step reasoning about what this observation means and what should be done...",
  "should_act": true/false,
  "action": {{
    "type": "The action type (predefined or custom)",
    "description": "Human-readable description of what you're doing",
    "details": {{
      // Action-specific details (flexible schema)
    }},
    "executor": "How to execute this (python/typescript/shell/claude_code/claude_flow/custom)"
  }},
  "confidence": 0.0-1.0,
  "alternatives_considered": [
    {{
      "type": "Alternative action type",
      "reason_rejected": "Why this wasn't chosen"
    }}
  ],
  "expected_outcome": "What you expect to happen",
  "follow_up_needed": true/false,
  "follow_up_description": "If follow-up needed, what to check for"
}}
```

Now reason about the observation and decide:'''
```

### 2.4 Flexible Action Schema

Unlike rigid template-based actions, the new schema is intentionally flexible:

```python
@dataclass
class FlexibleAction:
    """
    An action decided by the LLM. Schema is flexible by design.
    """
    type: str  # Can be predefined OR novel
    description: str
    details: dict  # Flexible, action-dependent
    executor: str

    # Metadata
    reasoning: str
    confidence: float
    alternatives: list[dict]
    expected_outcome: str
    follow_up_needed: bool
    follow_up_description: Optional[str]


# Example: Predefined action type
action_write_file = FlexibleAction(
    type="file_write",
    description="Create a new utility module for parsing",
    details={
        "path": "src/utils/parser.py",
        "content": "...",
        "mode": "create"
    },
    executor="python",
    reasoning="The observation shows a new data format being used...",
    confidence=0.85,
    alternatives=[{"type": "file_edit", "reason_rejected": "File doesn't exist yet"}],
    expected_outcome="New parser utility available for import",
    follow_up_needed=True,
    follow_up_description="Check if parser is imported correctly"
)


# Example: Novel action type (LLM invented)
action_novel = FlexibleAction(
    type="code_review_with_suggestions",  # Novel type
    description="Review recent changes and suggest improvements",
    details={
        "files_to_review": ["src/main.py", "src/utils.py"],
        "review_criteria": ["performance", "readability", "error_handling"],
        "output_format": "markdown_report",
        "output_path": "docs/reviews/2024-01-15.md"
    },
    executor="claude_code",  # Uses Claude Code to perform review
    reasoning="Multiple files changed recently, good time for review...",
    confidence=0.72,
    alternatives=[],
    expected_outcome="Review report generated with actionable suggestions",
    follow_up_needed=True,
    follow_up_description="Check if suggestions were applied"
)
```

### 2.5 Universal Action Executor

Executes any action the LLM decides on:

```python
class UniversalActionExecutor:
    """
    Executes any action, including novel types the LLM invents.
    """

    def __init__(self):
        self.executors = {
            "python": PythonExecutor(),
            "typescript": TypeScriptExecutor(),
            "shell": ShellExecutor(),
            "claude_code": ClaudeCodeExecutor(),
            "claude_flow": ClaudeFlowExecutor(),
            "http": HTTPExecutor(),
            "internal": InternalExecutor(),
        }

    async def execute(self, action: FlexibleAction) -> ActionResult:
        """
        Execute the action using the appropriate executor.

        For novel action types, we interpret the details and
        delegate to the most appropriate executor.
        """

        executor_name = action.executor

        if executor_name == "custom":
            # LLM defined a custom execution path
            return await self._execute_custom(action)

        if executor_name not in self.executors:
            # Unknown executor - try to interpret
            return await self._execute_interpreted(action)

        executor = self.executors[executor_name]
        return await executor.execute(action)

    async def _execute_custom(self, action: FlexibleAction) -> ActionResult:
        """
        For custom actions, the LLM provides execution instructions.
        We interpret and execute them.
        """

        custom_instructions = action.details.get("execution_instructions", "")

        # Ask LLM to translate custom instructions into executable steps
        steps = await self._translate_to_steps(custom_instructions)

        results = []
        for step in steps:
            result = await self._execute_step(step)
            results.append(result)

            if not result.success:
                break

        return ActionResult(
            success=all(r.success for r in results),
            output=self._combine_outputs(results),
            action=action
        )

    async def _translate_to_steps(self, instructions: str) -> list[ExecutionStep]:
        """Use LLM to translate custom instructions into executable steps."""

        prompt = f'''Translate these custom action instructions into executable steps.

Instructions: {instructions}

For each step, specify:
1. The executor to use (python/shell/claude_code/etc)
2. The exact code/command to run
3. What output to capture

Respond with JSON array of steps.'''

        response = await self.llm.complete(prompt)
        return self._parse_steps(response)
```

---

## 3. Templates as Few-Shot Examples

Templates are no longer rules to match. They're examples that help the LLM understand patterns:

```python
class TemplateLibrary:
    """
    Templates are stored as examples for few-shot prompting.
    The LLM is NOT required to follow them.
    """

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.templates = self._load_templates()

    def get_relevant_examples(
        self,
        observation: Observation,
        limit: int = 3
    ) -> list[Template]:
        """
        Find templates similar to the current observation.
        These will be shown as examples, not as rules to follow.
        """

        # Semantic similarity search
        similar = self._find_similar(observation.raw_text, limit)

        return similar

    def format_as_examples(self, templates: list[Template]) -> str:
        """Format templates as few-shot examples for the prompt."""

        if not templates:
            return "No similar past decisions found."

        output = "Here are some examples of past decisions (for context, not as rules):\n\n"

        for i, template in enumerate(templates, 1):
            output += f'''### Example {i}

**Observation**: {template.trigger_pattern}

**Decision Made**:
```json
{json.dumps(template.action, indent=2)}
```

**Outcome**: {template.outcome_description}

---

'''

        output += """Remember: These are examples to learn from, not rules to follow.
You can make a different decision if it makes more sense for the current situation."""

        return output
```

### Template Structure (Example-Based)

```yaml
# templates/examples/file_change_response.yaml
name: "File Change Response Example"
description: "Example of how a file change might be handled"

# When this example might be relevant
trigger_context:
  observation_type: "filesystem"
  patterns:
    - "*.py modified"
    - "*.ts modified"

# What decision was made
example_decision:
  reasoning: |
    A Python file was modified. I should check if:
    1. The changes break any tests
    2. The file needs formatting
    3. Related documentation needs updating

  action:
    type: "multi_step"
    description: "Validate changes and update related files"
    steps:
      - type: "shell_exec"
        command: "python -m pytest tests/ -v"
      - type: "shell_exec"
        command: "black --check {file}"
      - type: "think"
        about: "Are there documentation files that reference this?"

# Outcome for learning
outcome:
  success: true
  description: "Tests passed, code was already formatted, no doc updates needed"
  lessons_learned:
    - "Quick validation after file changes catches issues early"
    - "Not all changes require documentation updates"
```

---

## 4. Novel Action Generation

The system explicitly supports LLM-invented actions:

### 4.1 Novel Action Detection

```python
class NovelActionHandler:
    """
    Handles actions that don't match any predefined type.
    """

    KNOWN_TYPES = {
        "file_write", "file_edit", "file_read", "file_delete",
        "python_exec", "typescript_exec", "shell_exec",
        "claude_code", "claude_flow",
        "http_request", "think", "debate"
    }

    def is_novel(self, action: FlexibleAction) -> bool:
        """Check if this is a novel action type."""
        return action.type not in self.KNOWN_TYPES

    async def handle_novel(self, action: FlexibleAction) -> ActionResult:
        """
        Handle a novel action type by interpreting its details
        and constructing an execution plan.
        """

        # Ask LLM to explain how to execute this novel action
        plan = await self._create_execution_plan(action)

        # Log for future learning
        await self._log_novel_action(action, plan)

        # Execute the plan
        return await self._execute_plan(plan)

    async def _create_execution_plan(
        self,
        action: FlexibleAction
    ) -> ExecutionPlan:
        """Use LLM to create an execution plan for the novel action."""

        prompt = f'''You proposed a novel action type: "{action.type}"

Description: {action.description}
Details: {json.dumps(action.details, indent=2)}

Create an execution plan using available primitives:
- file operations (read/write/edit)
- code execution (python/typescript/shell)
- claude_code invocation
- claude_flow swarm spawning
- HTTP requests

Break down "{action.type}" into executable steps.

Respond with JSON:
{{
  "steps": [
    {{
      "primitive": "python_exec",
      "code": "...",
      "capture_output": true
    }},
    ...
  ],
  "success_criteria": "How to know if this worked"
}}'''

        response = await self.llm.complete(prompt)
        return self._parse_plan(response)
```

### 4.2 Action Learning

When novel actions succeed, they can be learned for future use:

```python
class ActionLearner:
    """
    Learns from successful novel actions to improve future decisions.
    """

    async def learn_from_success(
        self,
        action: FlexibleAction,
        result: ActionResult
    ):
        """
        When a novel action succeeds, learn from it.
        """

        if not result.success:
            return

        # Create a new template from the successful action
        new_template = Template(
            name=f"Learned: {action.type}",
            description=action.description,
            trigger_context={
                "observation_patterns": await self._extract_patterns(action)
            },
            example_decision={
                "reasoning": action.reasoning,
                "action": {
                    "type": action.type,
                    "details": action.details,
                    "executor": action.executor
                }
            },
            outcome={
                "success": True,
                "description": result.output
            },
            learned_at=datetime.now(),
            usage_count=1
        )

        await self.template_library.add(new_template)

        logger.info(f"Learned new action pattern: {action.type}")
```

---

## 5. OIDA Loop Integration

The flexible decision engine integrates with the OIDA loop:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              OIDA LOOP                                      │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   ┌──────────────────────┐                                                 │
│   │      OBSERVE         │  ← Observation Collector                        │
│   │  Raw events from     │                                                 │
│   │  filesystem, process │                                                 │
│   │  monitor, timers     │                                                 │
│   └──────────┬───────────┘                                                 │
│              │                                                             │
│              ▼                                                             │
│   ┌──────────────────────┐                                                 │
│   │       INFER          │  ← Context Enricher                             │
│   │  Enrich with memory, │                                                 │
│   │  project state,      │                                                 │
│   │  capabilities        │                                                 │
│   └──────────┬───────────┘                                                 │
│              │                                                             │
│              ▼                                                             │
│   ┌──────────────────────┐                                                 │
│   │       DECIDE         │  ← Autonomous Decision Engine (NEW)             │
│   │  LLM reasons freely  │                                                 │
│   │  about what to do    │                                                 │
│   │  Templates = examples│                                                 │
│   └──────────┬───────────┘                                                 │
│              │                                                             │
│              ▼                                                             │
│   ┌──────────────────────┐                                                 │
│   │        ACT           │  ← Universal Action Executor                    │
│   │  Execute any action  │                                                 │
│   │  including novel     │                                                 │
│   │  types               │                                                 │
│   └──────────┬───────────┘                                                 │
│              │                                                             │
│              └──────────────── Outcome fed back to memory ─────────────────│
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Integration Code

```python
class FlexibleOIDALoop:
    """
    The OIDA loop with flexible autonomous decision making.
    """

    def __init__(
        self,
        observer: ObservationCollector,
        enricher: ContextEnricher,
        decision_engine: AutonomousDecisionEngine,
        executor: UniversalActionExecutor,
        memory: MemorySystem
    ):
        self.observer = observer
        self.enricher = enricher
        self.decision_engine = decision_engine
        self.executor = executor
        self.memory = memory

    async def run_cycle(self):
        """Run one OIDA cycle."""

        # OBSERVE
        observation = await self.observer.get_next()
        if not observation:
            return

        logger.info(f"Observed: {observation.raw_text}")

        # INFER
        context = await self.enricher.enrich(observation)

        # DECIDE (the new flexible part)
        decision = await self.decision_engine.decide(observation, context)

        logger.info(f"Decision: {decision.action.type if decision.should_act else 'No action'}")
        logger.debug(f"Reasoning: {decision.reasoning}")

        # ACT
        if decision.should_act:
            result = await self.executor.execute(decision.action)

            # Store outcome in memory
            await self.memory.store_outcome(
                observation=observation,
                decision=decision,
                result=result
            )

            # Learn from novel actions
            if self._is_novel(decision.action) and result.success:
                await self.learner.learn_from_success(decision.action, result)

        else:
            logger.info("Decision: No action needed")

    async def run(self):
        """Run the loop continuously."""

        while True:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"OIDA cycle error: {e}")
                await self.memory.store_error(e)

            await asyncio.sleep(self.config.cycle_interval)
```

---

## 6. Safety Boundaries

While the LLM has full agency, some safety boundaries remain:

```python
class SafetyChecker:
    """
    Validates actions before execution.
    Does NOT constrain creativity, just prevents harm.
    """

    # Hard boundaries - never allow
    FORBIDDEN_PATTERNS = [
        r"rm -rf /",
        r"sudo rm",
        r":(){ :|:& };:",  # Fork bomb
        r"mkfs\.",
        r"> /dev/sd",
    ]

    # Paths that require confirmation
    PROTECTED_PATHS = [
        "/etc",
        "/usr",
        "/bin",
        "/System",
        "~/.ssh",
        "~/.gnupg",
    ]

    def is_safe(self, action: FlexibleAction) -> tuple[bool, Optional[str]]:
        """Check if action is safe to execute."""

        # Check for forbidden patterns
        action_str = json.dumps(action.details)
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, action_str):
                return False, f"Forbidden pattern detected: {pattern}"

        # Check for protected paths
        paths = self._extract_paths(action)
        for path in paths:
            for protected in self.PROTECTED_PATHS:
                if path.startswith(protected):
                    return False, f"Protected path: {path}"

        # Check for network operations if restricted
        if self.config.restrict_network:
            if action.executor == "http" or "http" in action_str:
                return False, "Network operations restricted"

        return True, None

    def make_safe(self, action: FlexibleAction) -> FlexibleAction:
        """
        Attempt to make an unsafe action safe.
        Returns modified action or raises if impossible.
        """

        is_safe, reason = self.is_safe(action)

        if is_safe:
            return action

        # Try to sanitize
        sanitized = self._sanitize_action(action)

        is_safe_now, _ = self.is_safe(sanitized)

        if is_safe_now:
            return sanitized

        raise UnsafeActionError(f"Cannot make action safe: {reason}")
```

---

## 7. Memory and Learning

### 7.1 Decision Memory

```python
class DecisionMemory:
    """
    Stores decisions and outcomes for learning and context.
    """

    def __init__(self, storage: Storage):
        self.storage = storage

    async def store_decision(
        self,
        observation: Observation,
        decision: Decision,
        result: Optional[ActionResult] = None
    ):
        """Store a decision for future reference."""

        record = DecisionRecord(
            id=uuid.uuid4(),
            timestamp=datetime.now(),
            observation=observation.to_dict(),
            decision=decision.to_dict(),
            result=result.to_dict() if result else None,
            reasoning=decision.reasoning,
            action_type=decision.action.type if decision.should_act else None,
            success=result.success if result else None
        )

        await self.storage.save(record)

    async def get_similar_decisions(
        self,
        observation: Observation,
        limit: int = 5
    ) -> list[DecisionRecord]:
        """Find past decisions for similar observations."""

        # Semantic similarity search
        embedding = await self.embedder.embed(observation.raw_text)

        similar = await self.storage.search_by_embedding(
            embedding=embedding,
            limit=limit
        )

        return similar

    async def get_successful_patterns(self) -> list[Pattern]:
        """Extract patterns from successful decisions."""

        successful = await self.storage.query(
            success=True,
            limit=100
        )

        patterns = await self._extract_patterns(successful)

        return patterns
```

### 7.2 Learning from Outcomes

```python
class OutcomeLearner:
    """
    Learns from decision outcomes to improve future decisions.
    """

    async def learn_from_outcome(
        self,
        decision: Decision,
        result: ActionResult
    ):
        """Update model based on outcome."""

        if result.success:
            # Reinforce this pattern
            await self._reinforce_pattern(decision)

            # If novel action, save as template
            if self._is_novel(decision.action):
                await self._save_as_template(decision, result)

        else:
            # Learn from failure
            await self._record_failure(decision, result)

            # Update reasoning patterns
            await self._update_failure_patterns(decision, result)

    async def _reinforce_pattern(self, decision: Decision):
        """Increase weight of successful patterns."""

        pattern = await self._extract_pattern(decision)

        await self.pattern_store.increment_weight(
            pattern=pattern,
            amount=0.1
        )

    async def _save_as_template(
        self,
        decision: Decision,
        result: ActionResult
    ):
        """Save successful novel action as a new template."""

        template = Template(
            name=f"Learned: {decision.action.type}",
            trigger_patterns=await self._infer_triggers(decision),
            action_template=decision.action.to_template(),
            success_rate=1.0,
            usage_count=1,
            created_from="learning",
            created_at=datetime.now()
        )

        await self.template_store.save(template)
```

---

## 8. Configuration

```yaml
# config/decision_engine.yaml

decision_engine:
  # LLM settings
  llm:
    provider: "lm_studio"  # or "anthropic"
    model: "deepseek-coder-v2"  # local model
    temperature: 0.7  # Higher for more creative decisions
    max_tokens: 4096

    # Fallback for complex reasoning
    fallback:
      provider: "anthropic"
      model: "claude-3-sonnet"
      trigger_conditions:
        - "confidence < 0.5"
        - "novel_action_type"
        - "multi_step_plan"

  # Context settings
  context:
    max_recent_decisions: 10
    max_recent_outcomes: 5
    max_example_templates: 3
    include_project_structure: true
    structure_depth: 3

  # Safety settings
  safety:
    enabled: true
    allow_file_delete: false
    allow_network: true
    protected_paths:
      - ".git"
      - ".env"
      - "secrets"
    max_file_size_mb: 10

  # Learning settings
  learning:
    enabled: true
    save_novel_actions: true
    min_confidence_for_learning: 0.7
    pattern_reinforcement_rate: 0.1

  # Templates (as examples, not rules)
  templates:
    directory: "templates/examples"
    similarity_threshold: 0.6
    max_examples_in_prompt: 3
```

---

## 9. Example Scenarios

### Scenario 1: Unknown File Type

**Observation**: A `.proto` file was added (never seen before)

**Old System**: No template match, falls back to generic or fails

**New System**:
```json
{
  "reasoning": "A .proto file was added. This is a Protocol Buffer definition file. I should: 1) Check if protobuf compiler is available, 2) Generate code if there's a build system, 3) Update documentation if this is a new API.",

  "should_act": true,

  "action": {
    "type": "proto_file_setup",
    "description": "Setup protobuf compilation for new schema",
    "details": {
      "proto_file": "api/schema.proto",
      "check_compiler": "protoc --version",
      "generate_for": ["python", "typescript"],
      "update_makefile": true
    },
    "executor": "shell"
  },

  "confidence": 0.75,

  "alternatives_considered": [
    {
      "type": "ignore",
      "reason_rejected": "Proto files usually need compilation setup"
    }
  ]
}
```

### Scenario 2: Unusual Pattern Detection

**Observation**: Same file edited 10 times in 5 minutes

**Old System**: Template says "format on save", runs formatter 10 times

**New System**:
```json
{
  "reasoning": "The same file has been edited 10 times in 5 minutes. This unusual pattern suggests either: 1) Active development with save-often habit, 2) An automated tool making changes, 3) A loop/bug causing repeated edits. I should investigate rather than react to each change.",

  "should_act": true,

  "action": {
    "type": "investigate_edit_pattern",
    "description": "Analyze why this file is being edited so frequently",
    "details": {
      "file": "src/main.py",
      "analysis_steps": [
        "Check git diff for the file",
        "Check if any processes are writing to it",
        "Review last 10 changes for patterns"
      ],
      "output_report": "logs/edit_pattern_analysis.md"
    },
    "executor": "python"
  },

  "confidence": 0.68,

  "alternatives_considered": [
    {
      "type": "run_formatter",
      "reason_rejected": "Would be redundant, better to understand the pattern"
    },
    {
      "type": "ignore",
      "reason_rejected": "Pattern is unusual enough to warrant investigation"
    }
  ]
}
```

### Scenario 3: Creative Response to New Situation

**Observation**: Error log shows "API rate limit exceeded"

**Old System**: No template for this, might just log the error

**New System**:
```json
{
  "reasoning": "API rate limit exceeded. This needs immediate attention. I should: 1) Identify which API is rate-limited, 2) Check current usage patterns, 3) Implement exponential backoff if not present, 4) Consider caching responses.",

  "should_act": true,

  "action": {
    "type": "rate_limit_mitigation",
    "description": "Analyze and mitigate API rate limiting",
    "details": {
      "immediate_actions": [
        "Parse error to identify the API",
        "Check if retry logic exists",
        "Add exponential backoff if missing"
      ],
      "longer_term": [
        "Analyze call patterns",
        "Identify cacheable responses",
        "Consider request batching"
      ],
      "implementation": {
        "language": "python",
        "target_file": "src/api/client.py",
        "add_retry_decorator": true
      }
    },
    "executor": "claude_code"
  },

  "confidence": 0.82,

  "expected_outcome": "API calls will have proper retry logic and reduced frequency",

  "follow_up_needed": true,
  "follow_up_description": "Monitor API error rate over next hour"
}
```

---

## 10. Implementation Roadmap

### Phase 1: Core Engine (Week 1-2)
- [ ] Implement `AutonomousDecisionEngine` class
- [ ] Implement `ContextEnricher` with memory integration
- [ ] Build flexible action schema and validation
- [ ] Create `UniversalActionExecutor` with core executors

### Phase 2: Safety & Learning (Week 3)
- [ ] Implement `SafetyChecker` with boundaries
- [ ] Build `DecisionMemory` with semantic search
- [ ] Create `OutcomeLearner` for pattern reinforcement
- [ ] Add novel action handling and template creation

### Phase 3: Integration (Week 4)
- [ ] Integrate with existing OIDA loop
- [ ] Connect to LM Studio for local inference
- [ ] Add Claude Code/Flow executor integration
- [ ] Build monitoring and logging

### Phase 4: Testing & Refinement (Week 5-6)
- [ ] Test with real project observations
- [ ] Tune prompts based on decision quality
- [ ] Adjust confidence thresholds
- [ ] Document learnings and edge cases

---

## 11. Key Differences from Previous Design

| Aspect | Previous (Template-Based) | New (Autonomous) |
|--------|---------------------------|------------------|
| Decision Logic | Pattern matching | LLM reasoning |
| Templates | Rules to follow | Examples for context |
| Action Types | Predefined only | Any (including novel) |
| Flexibility | Low | High |
| Creativity | None | Supported |
| Learning | Manual template updates | Automatic from outcomes |
| Unknown Situations | Fail or generic fallback | LLM reasons about them |
| Reasoning | Hidden in template selection | Explicit and transparent |

---

## 12. Conclusion

The Flexible Autonomous Decision System represents a fundamental shift from rule-based to reasoning-based decision making. By treating the LLM as a genuine reasoning agent rather than a pattern matcher, the system gains:

1. **Adaptability**: Handles unknown situations gracefully
2. **Creativity**: Can invent novel solutions
3. **Transparency**: Reasoning is explicit and inspectable
4. **Learning**: Improves from experience automatically
5. **Generalization**: Fewer templates needed, better coverage

The key insight is that templates should be examples the LLM learns from, not rules it must follow. This allows the system to benefit from past experience while remaining free to innovate when needed.

**The LLM decides. The system executes.**
