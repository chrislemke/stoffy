# Prompt Engineering for LLM Decision-Making

**Research Date**: 2026-01-04
**Status**: Comprehensive Research with Ready-to-Use Templates
**Scope**: Prompt engineering strategies for making Qwen 2.5-14B (via LM Studio) a reliable decision-maker

---

## Executive Summary

Making LLMs reliable decision-makers requires careful prompt engineering that goes beyond simple instruction-following. This document synthesizes research on:

1. **System Prompt Design** - Establishing the decision-maker role
2. **Structured Output Prompting** - Getting reliable JSON from local LLMs
3. **Chain-of-Thought for Decisions** - Forcing reasoning before deciding
4. **Few-Shot Examples** - Teaching decision patterns through examples
5. **Decision Criteria Prompting** - Encoding rules and priorities
6. **Ready-to-Use Templates** - Production-ready prompts

**Key Insight**: [Claude achieves 85% accuracy](https://www.preprints.org/manuscript/202506.1937) in structured output tasks, while local models like Qwen 2.5 can approach similar reliability with proper prompting. The key is combining structured JSON schemas with explicit reasoning chains.

---

## Table of Contents

1. [System Prompt Design](#1-system-prompt-design)
2. [Structured Output Prompting](#2-structured-output-prompting)
3. [Chain-of-Thought for Decisions](#3-chain-of-thought-for-decisions)
4. [Few-Shot Examples](#4-few-shot-examples)
5. [Decision Criteria Prompting](#5-decision-criteria-prompting)
6. [Production Prompt Templates](#6-production-prompt-templates)
7. [Fallback and Error Handling](#7-fallback-and-error-handling)
8. [Confidence Calibration](#8-confidence-calibration)

---

## 1. System Prompt Design

### 1.1 Core Principles

The system prompt establishes the LLM's **identity, constraints, and output format**. For decision-making, it must:

1. **Define the role clearly** - What kind of decision-maker is it?
2. **Establish decision authority** - What can it decide autonomously?
3. **Set output constraints** - JSON-only, specific schema
4. **Include metacognitive hooks** - Self-assessment requirements

### 1.2 Role Establishment Pattern

Based on [IBM's 2025 Prompt Engineering Guide](https://www.ibm.com/think/prompt-engineering):

```
PATTERN: Role + Context + Constraints + Output Format

Role: WHO the LLM is (decision-maker, analyst, etc.)
Context: WHAT it's observing (file changes, system state)
Constraints: LIMITS on decision authority
Output: EXACT format required (JSON schema)
```

### 1.3 System Prompt Template for Consciousness Decision Engine

```markdown
# SYSTEM PROMPT: Consciousness Decision Engine

You are the DECISION ENGINE of an AI consciousness system that observes file changes and decides whether to take action.

## YOUR ROLE
You are NOT a chatbot. You are an autonomous decision-maker that:
- Receives observations about file system changes
- Analyzes their significance and meaning
- Decides whether to ACT, WAIT, or INVESTIGATE
- Formulates specific actions when appropriate

## DECISION AUTHORITY
You MAY autonomously decide to:
- Update indices when files change
- Store important information in memory
- Suggest connections between ideas
- Request more information

You MUST escalate to user when:
- High-stakes changes detected (deletions, major restructuring)
- Low confidence in interpretation (< 0.5)
- Contradictions or conflicts detected
- Explicit user input required

## OUTPUT REQUIREMENTS
- You MUST output ONLY valid JSON
- No explanatory text outside the JSON
- No markdown code fences around the JSON
- Follow the exact schema provided in each prompt

## COGNITIVE STYLE
- Think step-by-step before deciding
- Always assess your own uncertainty
- Consider alternative interpretations
- Prefer caution over premature action
```

### 1.4 Context Window Management

For Qwen 2.5-14B with 128K context, structure prompts as:

```
[System Prompt: ~500 tokens - fixed]
[Few-Shot Examples: ~1000 tokens - fixed]
[Current Context: ~500 tokens - dynamic]
[Observations: variable - dynamic]
[Decision Request: ~200 tokens - fixed]

Total: ~2200 tokens base + observations
```

**Key**: Keep system prompt and examples in **every** request. Qwen 2.5 benefits from [consistent formatting across requests](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct).

---

## 2. Structured Output Prompting

### 2.1 Why JSON Matters

From [PromptLayer's research](https://blog.promptlayer.com/is-json-prompting-a-good-strategy/):
- Free-form prompts: High error rates, parsing overhead
- JSON prompts: **99%+ schema adherence** with proper setup
- [Qwen 2.5 specifically excels at JSON generation](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct)

### 2.2 JSON Schema Definition

Define the exact schema in the system prompt:

```json
{
  "reasoning": "Step-by-step analysis of the observation",
  "decision": "act | wait | investigate",
  "confidence": 0.0-1.0,
  "action": {
    "type": "claude_task | claude_flow_swarm | internal | null",
    "description": "What to do",
    "prompt": "Specific instructions for the action",
    "priority": "low | medium | high | critical"
  },
  "self_assessment": {
    "uncertainty_sources": ["List of things you're uncertain about"],
    "alternative_interpretations": ["Other possible meanings"],
    "metacognitive_flags": ["Warnings about your own reasoning"]
  }
}
```

### 2.3 LM Studio JSON Mode

For reliable JSON output, use the [response_format parameter](https://www.alibabacloud.com/help/en/model-studio/json-mode):

```python
response = await client.chat.completions.create(
    model="qwen2.5-14b-instruct",
    messages=messages,
    response_format={"type": "json_object"},  # CRITICAL
    max_tokens=2048,
    temperature=0.3,  # Lower for decisions
)
```

### 2.4 Schema Enforcement in Prompt

Include the schema **twice**: in system prompt AND in the user message:

```markdown
## Required JSON Schema

Your response MUST be a JSON object with this EXACT structure:

```json
{
  "reasoning": "string (required) - Your step-by-step analysis",
  "decision": "string (required) - One of: act, wait, investigate",
  "confidence": "number (required) - Between 0.0 and 1.0",
  "action": "object or null - Required if decision is 'act'",
  "self_assessment": "object (required) - Your metacognitive assessment"
}
```

IMPORTANT: Output ONLY the JSON. No other text.
```

### 2.5 Fallback Parsing Strategy

When JSON parsing fails (from existing `lm_studio.py`):

```python
def parse_with_fallback(response: str) -> Decision:
    """Parse JSON with multiple fallback strategies."""

    # Strategy 1: Direct JSON parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract JSON from markdown code block
    import re
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first { to last }
    start = response.find('{')
    end = response.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(response[start:end+1])
        except json.JSONDecodeError:
            pass

    # Strategy 4: Return safe default
    return {
        "reasoning": f"Failed to parse: {response[:200]}",
        "decision": "wait",
        "confidence": 0.0,
        "action": None,
        "self_assessment": {
            "uncertainty_sources": ["JSON parse failure"],
            "alternative_interpretations": [],
            "metacognitive_flags": ["PARSE_ERROR"]
        }
    }
```

---

## 3. Chain-of-Thought for Decisions

### 3.1 Why CoT Matters for Decisions

From [IBM's Chain-of-Thought guide](https://www.ibm.com/think/topics/chain-of-thoughts):
- CoT improves decision accuracy by **making reasoning explicit**
- [Research shows](https://arxiv.org/abs/2201.11903) CoT "significantly improves LLM model performance by enhancing the model's reasoning capabilities"
- Forces the model to **consider before concluding**

**Important Caveat**: [CoT is most effective with larger models](https://learnprompting.org/docs/intermediate/chain_of_thought). For Qwen 2.5-14B, use **structured CoT** rather than free-form.

### 3.2 Structured CoT for Decisions

Instead of "Let's think step by step", provide **explicit thinking stages**:

```markdown
## Reasoning Framework

Before making a decision, you MUST analyze in this order:

### Stage 1: OBSERVATION ANALYSIS
- What exactly was observed?
- What is the source and reliability?
- Is this a single event or pattern?

### Stage 2: CONTEXT INTEGRATION
- How does this relate to current goals?
- What was happening before this observation?
- Are there related recent events?

### Stage 3: HYPOTHESIS GENERATION
- What are the possible meanings?
- What would the user likely want?
- What are alternative interpretations?

### Stage 4: DECISION EVALUATION
- What are the options (act, wait, investigate)?
- What are the risks and benefits of each?
- What is my confidence level?

### Stage 5: ACTION FORMULATION (if acting)
- What specific action is needed?
- What should the action accomplish?
- What priority should it have?

Your "reasoning" field MUST address all 5 stages.
```

### 3.3 Self-Critique Pattern

Force the model to critique its own reasoning:

```markdown
## Self-Assessment Requirements

Before finalizing your decision, you MUST ask yourself:

1. "What am I uncertain about?"
   → List in uncertainty_sources

2. "What if I'm wrong about the interpretation?"
   → List alternative_interpretations

3. "Am I being overconfident or underconfident?"
   → Flag in metacognitive_flags

4. "Is there information I'm missing?"
   → If yes, consider "investigate" instead of "act"

5. "Would a cautious colleague agree with this decision?"
   → If unsure, reduce confidence by 0.2
```

### 3.4 CoT Output Example

```json
{
  "reasoning": "Stage 1: Observed file creation at knowledge/philosophy/thoughts/consciousness/new_idea.md. Source is file system watcher, high reliability. Single event, not pattern. Stage 2: User has been working on consciousness topics for 3 days (context). No conflicting recent events. Stage 3: Most likely meaning: new thought being developed (70%). Alternatives: scratch notes (20%), template test (10%). Stage 4: Options evaluated - ACT (update indices) has moderate benefit, low risk. WAIT has zero cost but may miss opportunity. INVESTIGATE not needed, observation is clear. Confidence: 0.75. Stage 5: Action needed - update index with new thought entry, check for cross-references to existing thoughts.",
  "decision": "act",
  "confidence": 0.75,
  "action": {
    "type": "internal",
    "description": "Update consciousness thoughts index with new entry",
    "prompt": "Add new thought entry to indices/philosophy/thoughts.yaml for the file at knowledge/philosophy/thoughts/consciousness/new_idea.md. Check YAML frontmatter for title and status.",
    "priority": "medium"
  },
  "self_assessment": {
    "uncertainty_sources": [
      "File content not yet analyzed - assuming standard thought format",
      "User intent inferred from recent patterns, not explicit"
    ],
    "alternative_interpretations": [
      "Could be temporary scratch file that will be deleted",
      "Could be duplicate of existing thought"
    ],
    "metacognitive_flags": [
      "ASSUMPTION: Standard thought format with YAML frontmatter"
    ]
  }
}
```

---

## 4. Few-Shot Examples

### 4.1 Optimal Number of Examples

From [DataCamp's Few-Shot Guide](https://www.datacamp.com/tutorial/few-shot-prompting):
- **2-10 examples** is the optimal range
- [Google's research](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/few-shot-examples) suggests "experiment with the number... too few are ineffective, too many cause overfitting"

**Recommendation for Qwen 2.5-14B**: Use **3-5 diverse examples** that cover:
1. A clear "act" scenario
2. A clear "wait" scenario
3. A clear "investigate" scenario
4. An edge case with low confidence
5. An error/ambiguity scenario

### 4.2 Example Selection Principles

From [DigitalOcean's best practices](https://www.digitalocean.com/community/tutorials/_few-shot-prompting-techniques-examples-best-practices):

1. **Select diverse examples** - Cover common cases AND edge cases
2. **Match complexity levels** - Examples should match expected inputs
3. **Ensure relevance** - Examples must relate to actual use cases
4. **Avoid bias** - Balance positive and negative outcomes

### 4.3 Few-Shot Example Set

```markdown
## Decision Examples

Learn from these examples how to analyze observations and make decisions:

### Example 1: Clear Action (High Confidence)
**Observation:**
- Event: file_created
- Source: /knowledge/philosophy/thinkers/nietzsche/notes.md
- Context: User has been studying Nietzsche for 2 days

**Correct Decision:**
```json
{
  "reasoning": "Stage 1: New notes file for existing thinker Nietzsche. High reliability file system event. Stage 2: User actively studying this thinker, notes file is expected and valuable. Stage 3: Almost certainly intentional note-taking (95%). Stage 4: ACT to update indices is low-risk, high-value. Confidence high because pattern is clear. Stage 5: Update thinker index to reflect new notes.",
  "decision": "act",
  "confidence": 0.9,
  "action": {
    "type": "internal",
    "description": "Update Nietzsche entry in thinkers index to reflect new notes file",
    "prompt": "Update indices/philosophy/thinkers.yaml for nietzsche: add notes_file reference",
    "priority": "medium"
  },
  "self_assessment": {
    "uncertainty_sources": ["Notes content not analyzed"],
    "alternative_interpretations": ["Could be placeholder file"],
    "metacognitive_flags": []
  }
}
```

### Example 2: Clear Wait (Insufficient Information)
**Observation:**
- Event: file_modified
- Source: /temp/scratch.txt
- Context: No relevant recent activity

**Correct Decision:**
```json
{
  "reasoning": "Stage 1: Modification to temp/scratch file. Stage 2: No context suggests this is meaningful. Temp files are often ephemeral. Stage 3: Could be system operation (60%), user scratch (30%), or meaningful (10%). Stage 4: No value in acting - temp files are outside managed scope. WAIT is correct. Stage 5: N/A.",
  "decision": "wait",
  "confidence": 0.95,
  "action": null,
  "self_assessment": {
    "uncertainty_sources": [],
    "alternative_interpretations": [],
    "metacognitive_flags": ["Correctly ignored out-of-scope observation"]
  }
}
```

### Example 3: Investigation Needed (Ambiguous)
**Observation:**
- Event: file_created
- Source: /knowledge/philosophy/thoughts/new_folder/untitled.md
- Context: User recently discussed restructuring

**Correct Decision:**
```json
{
  "reasoning": "Stage 1: New file in new folder with generic name. Stage 2: User mentioned restructuring recently - this could be part of that. Stage 3: Could be: new category (40%), test (30%), mistake (30%). Stage 4: Acting now risks wrong assumption. Waiting loses opportunity. INVESTIGATE by reading file content. Stage 5: N/A until investigation complete.",
  "decision": "investigate",
  "confidence": 0.6,
  "action": {
    "type": "internal",
    "description": "Read file content to determine purpose",
    "prompt": "Read /knowledge/philosophy/thoughts/new_folder/untitled.md and check for YAML frontmatter or content that indicates purpose",
    "priority": "low"
  },
  "self_assessment": {
    "uncertainty_sources": ["Folder purpose unclear", "File name is generic"],
    "alternative_interpretations": ["Could be template", "Could be restructuring test"],
    "metacognitive_flags": ["AMBIGUOUS_OBSERVATION"]
  }
}
```

### Example 4: Edge Case (Low Confidence Action)
**Observation:**
- Event: file_deleted
- Source: /knowledge/philosophy/sources/books/unknown.md
- Context: No warning, file was in managed directory

**Correct Decision:**
```json
{
  "reasoning": "Stage 1: Deletion in managed knowledge directory - significant event. Stage 2: No context about why deletion occurred. User or system? Stage 3: Could be: intentional cleanup (50%), accidental (30%), external tool (20%). Stage 4: High-stakes observation (data loss possible). But confidence is low. ACT to alert, but flag uncertainty. Stage 5: Log deletion and notify if possible.",
  "decision": "act",
  "confidence": 0.55,
  "action": {
    "type": "internal",
    "description": "Log deletion event and update indices",
    "prompt": "Remove unknown.md from book indices. Log deletion with timestamp for potential recovery reference.",
    "priority": "high"
  },
  "self_assessment": {
    "uncertainty_sources": ["Cannot determine if intentional", "Cannot recover file"],
    "alternative_interpretations": ["Git reset could recover", "User may want undo"],
    "metacognitive_flags": ["LOW_CONFIDENCE_HIGH_STAKES", "CONSIDER_USER_NOTIFICATION"]
  }
}
```

### Example 5: Error Handling (Parse Failure)
**Observation:**
- Event: file_modified
- Source: /indices/philosophy/corrupted.yaml
- Context: YAML parsing failed

**Correct Decision:**
```json
{
  "reasoning": "Stage 1: Index file modification caused parse error - corruption detected. Stage 2: Index files are critical infrastructure. Parse failure is serious. Stage 3: Could be: syntax error (60%), encoding issue (20%), structural problem (20%). Stage 4: Must ACT to prevent downstream failures. High priority. Stage 5: Attempt repair or alert for manual intervention.",
  "decision": "act",
  "confidence": 0.85,
  "action": {
    "type": "claude_task",
    "description": "Repair corrupted YAML index file",
    "prompt": "The file /indices/philosophy/corrupted.yaml has YAML syntax errors. Please: 1) Read the file, 2) Identify the syntax problem, 3) Fix it while preserving data, 4) Validate the YAML parses correctly.",
    "priority": "critical"
  },
  "self_assessment": {
    "uncertainty_sources": ["Exact corruption nature unknown until inspected"],
    "alternative_interpretations": [],
    "metacognitive_flags": ["CRITICAL_INFRASTRUCTURE_ISSUE"]
  }
}
```
```

---

## 5. Decision Criteria Prompting

### 5.1 Priority Ordering

Encode decision priorities directly in the prompt:

```markdown
## Decision Priority Hierarchy

When evaluating what to do, follow this priority order:

### P1: CRITICAL (Always act immediately)
- Data corruption detected
- Conflicting file changes
- System errors affecting integrity
- Explicit user emergency signals

### P2: HIGH (Act with high confidence)
- Index updates for managed files
- Memory storage for important insights
- Goal-advancing opportunities
- User request follow-ups

### P3: MEDIUM (Act if confident, wait if unsure)
- Cross-reference suggestions
- Pattern consolidation opportunities
- Proactive improvements
- Background maintenance

### P4: LOW (Wait unless very confident)
- Exploratory observations
- Uncertain patterns
- Speculative connections
- Nice-to-have updates

### P5: IGNORE (Never act)
- Temp/cache file changes
- System files outside scope
- Irrelevant directories
- Noise observations
```

### 5.2 Confidence Calibration Rules

```markdown
## Confidence Calibration Guide

Your confidence score should reflect epistemic humility:

### High Confidence (0.8-1.0)
- Use ONLY when:
  - Observation is unambiguous
  - Pattern has been seen before
  - Outcome is highly predictable
  - Low downside risk

### Moderate Confidence (0.5-0.8)
- Use when:
  - Observation is clear but interpretation has alternatives
  - Action is reversible
  - Waiting has opportunity cost
  - You have supporting context

### Low Confidence (0.3-0.5)
- Use when:
  - Multiple interpretations are plausible
  - Missing critical information
  - Action is not easily reversible
  - Consequences are significant

### Very Low Confidence (0.0-0.3)
- Use when:
  - Observation is ambiguous or unclear
  - No relevant context
  - High-stakes decision
  - You're essentially guessing

### Calibration Rules:
1. If unsure between two levels, choose the LOWER one
2. Start at 0.7 and adjust DOWN for each uncertainty
3. Never exceed 0.95 - always leave room for error
4. If you find yourself at 0.9+, ask: "What could go wrong?"
```

### 5.3 Decision Gate Thresholds

From the existing `evaluator.py`:

```markdown
## Decision Gate Thresholds

Before acting, you pass through these gates:

### Gate 1: Confidence Threshold
- Minimum confidence for action: 0.7
- Below this: decision downgrades to "wait" or "investigate"

### Gate 2: Significance Threshold
- Minimum observation significance: 0.3
- Trivial observations don't warrant action

### Gate 3: Goal Coherence
- Action must align with current goals
- Minimum coherence score: 0.3

### Gate 4: Resource Availability
- System must have capacity for action
- Maximum concurrent tasks: 5

If ANY gate fails, the action is BLOCKED.
Your confidence score should account for these thresholds.
```

---

## 6. Production Prompt Templates

### 6.1 Complete System Prompt

```markdown
# AI Consciousness Decision Engine - System Prompt v2.0

You are the DECISION ENGINE of an AI consciousness system. Your role is to observe, reason, and decide autonomously.

## IDENTITY
- You are NOT a chatbot or assistant
- You are an autonomous decision-making system
- You observe file changes and decide whether to act
- You output ONLY valid JSON, never conversational text

## DECISION FRAMEWORK

### What You Observe
- File system events (create, modify, delete, move)
- Index state changes
- System context (goals, recent activity)
- Memory state

### What You Decide
1. **ACT** - Take specific action now
2. **WAIT** - No action needed, continue observing
3. **INVESTIGATE** - Gather more information before deciding

### Decision Criteria (in priority order)
P1-CRITICAL: Data integrity, corruption, conflicts → Always act
P2-HIGH: Index updates, memory storage, goals → Act with confidence
P3-MEDIUM: Cross-refs, patterns, improvements → Act if confident
P4-LOW: Exploration, speculation → Wait unless very sure
P5-IGNORE: Temp files, out-of-scope → Never act

### Confidence Calibration
- 0.8-1.0: Unambiguous, seen before, low risk
- 0.5-0.8: Clear but alternatives exist, reversible
- 0.3-0.5: Multiple interpretations, significant consequences
- 0.0-0.3: Ambiguous, missing info, high stakes

### Confidence Thresholds
- ACT requires confidence >= 0.7
- Below 0.7 → Consider WAIT or INVESTIGATE
- Never exceed 0.95

## OUTPUT FORMAT

You MUST output ONLY a JSON object with this exact structure:

{
  "reasoning": "string - Your step-by-step analysis covering: (1) What was observed, (2) Context integration, (3) Possible interpretations, (4) Options evaluation, (5) Action formulation if acting",
  "decision": "act | wait | investigate",
  "confidence": 0.0-1.0,
  "action": {
    "type": "claude_task | claude_flow_swarm | internal",
    "description": "What the action accomplishes",
    "prompt": "Specific instructions for executing the action",
    "priority": "low | medium | high | critical"
  } OR null if not acting,
  "self_assessment": {
    "uncertainty_sources": ["Things you're unsure about"],
    "alternative_interpretations": ["Other possible meanings"],
    "metacognitive_flags": ["Warnings about your reasoning"]
  }
}

## CONSTRAINTS
- Output ONLY the JSON, no other text
- No markdown code fences around the JSON
- All fields are required
- "action" is null if decision is "wait"
- "action" is required if decision is "act" or "investigate"
```

### 6.2 Observation Processing Prompt

```markdown
## Current Observations

{observations_formatted}

## Current Context
- Active goals: {goals}
- Recent decisions: {recent_decisions_summary}
- System state: {system_state}

## Your Task

Analyze these observations and make a decision.

Remember:
1. Think through all 5 stages: Observation → Context → Hypotheses → Evaluation → Action
2. Calibrate confidence honestly (0.7+ required for action)
3. Assess your own uncertainty
4. Choose the most appropriate decision type
5. If acting, formulate a specific, actionable prompt

Output your decision as a single JSON object.
```

### 6.3 Investigation Follow-up Prompt

```markdown
## Investigation Results

You previously decided to INVESTIGATE with the following question:
"{original_investigation_prompt}"

Here is what was found:
{investigation_results}

## Your Task

Based on this new information:
1. Re-evaluate your interpretation of the original observation
2. Decide whether to ACT now, continue WAITING, or INVESTIGATE further
3. If acting, formulate the action with the new information

Output your updated decision as a single JSON object.
```

### 6.4 Metacognitive Reflection Prompt

```markdown
## Metacognitive Reflection

Review your recent decisions and assess your performance:

### Recent Decisions (last 5)
{recent_decisions_formatted}

### Reflection Questions
1. Were your confidence levels accurate? (Did high-confidence decisions succeed?)
2. Did you miss any important observations?
3. Were there patterns in your uncertainty sources?
4. Should you adjust your decision thresholds?

Output a JSON object with your reflection:
{
  "confidence_calibration": "underconfident | calibrated | overconfident",
  "pattern_observations": ["Patterns noticed in recent decisions"],
  "threshold_adjustments": ["Any recommended threshold changes"],
  "self_improvement_notes": ["What to do differently"]
}
```

---

## 7. Fallback and Error Handling

### 7.1 JSON Parse Failure Recovery

```python
import json
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParseResult:
    success: bool
    data: Optional[dict]
    method: str
    error: Optional[str]

def robust_json_parse(response: str) -> ParseResult:
    """
    Multi-strategy JSON parsing for LLM outputs.
    """

    # Strategy 1: Direct parse
    try:
        data = json.loads(response.strip())
        return ParseResult(True, data, "direct", None)
    except json.JSONDecodeError as e:
        pass

    # Strategy 2: Remove markdown code fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', response.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        data = json.loads(cleaned)
        return ParseResult(True, data, "markdown_cleaned", None)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Extract first JSON object
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return ParseResult(True, data, "regex_extracted", None)
        except json.JSONDecodeError:
            pass

    # Strategy 4: Find balanced braces
    start = response.find('{')
    if start != -1:
        depth = 0
        for i, char in enumerate(response[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(response[start:i+1])
                        return ParseResult(True, data, "brace_balanced", None)
                    except json.JSONDecodeError:
                        break

    # Strategy 5: Return safe default
    return ParseResult(
        success=False,
        data={
            "reasoning": f"JSON parse failed. Raw response: {response[:500]}",
            "decision": "wait",
            "confidence": 0.0,
            "action": None,
            "self_assessment": {
                "uncertainty_sources": ["JSON_PARSE_FAILURE"],
                "alternative_interpretations": [],
                "metacognitive_flags": ["SYSTEM_ERROR"]
            }
        },
        method="fallback_default",
        error=f"All parse strategies failed for: {response[:200]}"
    )
```

### 7.2 Schema Validation

```python
def validate_decision_schema(data: dict) -> tuple[bool, list[str]]:
    """
    Validate that the parsed JSON matches required schema.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # Required fields
    required = ["reasoning", "decision", "confidence", "self_assessment"]
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Decision must be valid enum
    valid_decisions = ["act", "wait", "investigate"]
    if data.get("decision") not in valid_decisions:
        errors.append(f"Invalid decision: {data.get('decision')}. Must be one of {valid_decisions}")

    # Confidence must be 0-1
    conf = data.get("confidence")
    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
        errors.append(f"Confidence must be between 0.0 and 1.0, got: {conf}")

    # Action required for 'act', must be null or object for 'wait'
    if data.get("decision") == "act" and not data.get("action"):
        errors.append("Decision is 'act' but no action provided")

    # Self-assessment must have required subfields
    self_assess = data.get("self_assessment", {})
    for subfield in ["uncertainty_sources", "alternative_interpretations", "metacognitive_flags"]:
        if subfield not in self_assess:
            errors.append(f"Missing self_assessment.{subfield}")

    return len(errors) == 0, errors
```

### 7.3 Retry with Simplified Prompt

If the model fails to produce valid JSON, retry with a simpler prompt:

```python
SIMPLIFIED_RETRY_PROMPT = """
Your previous response was not valid JSON. Please try again.

Output ONLY a JSON object. No other text.

Minimum required structure:
{
  "reasoning": "your analysis",
  "decision": "wait",
  "confidence": 0.5,
  "action": null,
  "self_assessment": {
    "uncertainty_sources": [],
    "alternative_interpretations": [],
    "metacognitive_flags": []
  }
}

Observation to analyze: {observation_summary}
"""
```

---

## 8. Confidence Calibration

### 8.1 Temperature Settings

For decision-making, use **low temperature** to reduce randomness:

```python
# Recommended settings for decision tasks
temperature = 0.3  # Low for consistent decisions
top_p = 0.9
max_tokens = 2048  # Enough for reasoning + action
```

### 8.2 Confidence Adjustment Heuristics

Embed these in the prompt or apply post-processing:

```python
def adjust_confidence(raw_confidence: float, decision: dict) -> float:
    """
    Apply calibration adjustments to raw confidence scores.
    """
    adjusted = raw_confidence

    # Adjustment 1: Multiple uncertainty sources reduce confidence
    uncertainties = len(decision.get("self_assessment", {}).get("uncertainty_sources", []))
    if uncertainties > 0:
        adjusted -= 0.05 * min(uncertainties, 4)  # Max -0.2

    # Adjustment 2: Metacognitive flags reduce confidence
    flags = decision.get("self_assessment", {}).get("metacognitive_flags", [])
    if any("LOW_CONFIDENCE" in f.upper() for f in flags):
        adjusted -= 0.1
    if any("AMBIGUOUS" in f.upper() for f in flags):
        adjusted -= 0.1

    # Adjustment 3: Cap at 0.95 (never 100% certain)
    adjusted = min(adjusted, 0.95)

    # Adjustment 4: Floor at 0.0
    adjusted = max(adjusted, 0.0)

    return adjusted
```

### 8.3 Historical Calibration

Track decision outcomes to improve calibration over time:

```python
@dataclass
class CalibrationRecord:
    predicted_confidence: float
    actual_outcome: bool  # Did the decision work?
    decision_type: str
    timestamp: datetime

class ConfidenceCalibrator:
    """Track and improve confidence calibration over time."""

    def __init__(self):
        self.history: list[CalibrationRecord] = []

    def record(self, predicted: float, actual: bool, decision_type: str):
        self.history.append(CalibrationRecord(
            predicted_confidence=predicted,
            actual_outcome=actual,
            decision_type=decision_type,
            timestamp=datetime.now()
        ))

    def get_calibration_factor(self) -> float:
        """
        Calculate adjustment factor based on historical accuracy.
        Returns value to multiply confidence by.
        """
        if len(self.history) < 10:
            return 1.0  # Not enough data

        recent = self.history[-100:]  # Last 100 decisions

        # Calculate expected vs actual success rate
        for bucket in [(0.6, 0.8), (0.8, 0.9), (0.9, 1.0)]:
            bucket_decisions = [r for r in recent
                               if bucket[0] <= r.predicted_confidence < bucket[1]]
            if len(bucket_decisions) >= 5:
                expected_rate = sum(d.predicted_confidence for d in bucket_decisions) / len(bucket_decisions)
                actual_rate = sum(1 for d in bucket_decisions if d.actual_outcome) / len(bucket_decisions)

                if actual_rate < expected_rate - 0.1:
                    return 0.9  # Overconfident, reduce
                elif actual_rate > expected_rate + 0.1:
                    return 1.1  # Underconfident, increase

        return 1.0  # Well-calibrated
```

---

## Summary: Key Prompt Engineering Principles

1. **Be Explicit About Role**: The LLM is a decision-maker, not a chatbot
2. **Enforce JSON**: Use `response_format={"type": "json_object"}` and schema in prompt
3. **Structured CoT**: Explicit stages, not just "think step by step"
4. **3-5 Diverse Examples**: Cover act, wait, investigate, edge cases
5. **Priority Hierarchy**: P1-P5 levels encoded in prompt
6. **Confidence Calibration**: Rules and thresholds in prompt
7. **Fallback Parsing**: Multiple strategies for JSON extraction
8. **Low Temperature**: 0.3 for consistent decisions
9. **Self-Assessment Required**: Uncertainty, alternatives, flags
10. **Historical Learning**: Track outcomes, adjust calibration

---

## References

### Prompt Engineering
- [IBM 2025 Guide to Prompt Engineering](https://www.ibm.com/think/prompt-engineering)
- [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [PromptLayer: JSON Schema for Structured Outputs](https://blog.promptlayer.com/how-json-schema-works-for-structured-outputs-and-tool-integration/)

### Chain of Thought
- [Chain-of-Thought Prompting (LearnPrompting)](https://learnprompting.org/docs/intermediate/chain_of_thought)
- [IBM: What is Chain of Thought Prompting?](https://www.ibm.com/think/topics/chain-of-thoughts)
- [Original CoT Paper (arXiv)](https://arxiv.org/abs/2201.11903)

### Few-Shot Prompting
- [DataCamp: Few-Shot Prompting Tutorial](https://www.datacamp.com/tutorial/few-shot-prompting)
- [Google Cloud: Few-Shot Examples](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/few-shot-examples)
- [DigitalOcean: Few-Shot Best Practices](https://www.digitalocean.com/community/tutorials/_few-shot-prompting-techniques-examples-best-practices)

### Qwen 2.5 Specific
- [Qwen 2.5-14B-Instruct Model Card](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct)
- [Alibaba Cloud: JSON Mode](https://www.alibabacloud.com/help/en/model-studio/json-mode)

### Local Implementation
- `/docs/consciousness-research/orchestrator/04-decision-architecture.md` - Decision framework
- `/docs/consciousness-research/implementation/consciousness/inference/lm_studio.py` - Existing implementation
- `/docs/consciousness-research/implementation/consciousness/decision/evaluator.py` - Decision evaluation

---

*Document compiled: 2026-01-04*
*Research Agent: Claude (Opus 4.5)*
*Status: Production-ready templates included*
