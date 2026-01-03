---
description: Orchestrate a philosophical debate between two agents
allowed-tools: Read, Glob, Grep, Write, TodoWrite, Task
argument-hint: <agent1> <agent2> <rounds> <topic to debate>
---

# Philosophical Debate: $ARGUMENTS

You are orchestrating a structured philosophical debate between two agents.

**ULTRATHINK** about this debate orchestration. This is important intellectual work.

---

## Step 1: Parse & Validate Input

Parse `$ARGUMENTS` to extract four components:
1. **agent1**: First agent name
2. **agent2**: Second agent name
3. **rounds**: Number of debate rounds (positive integer, typically 1-10)
4. **topic**: Everything after the rounds parameter

### Known Agent Names
```
philosophical-analyst
philosophical-generator
devils-advocate
thought-experimenter
symposiarch
philosophical-historian
cross-cultural-bridge
radical-innovator
concept-mapper
```

### Parsing Strategy
1. Split the input by spaces
2. Check if first token matches a known agent name (with or without `.md`)
3. Check if second token matches a known agent name
4. Check if third token is a positive integer (rounds)
5. Remaining tokens = topic (join with spaces)

### Validation Checks

**Check 1: Agent count**
If fewer than 2 agent-like tokens found:
```
=== DEBATE SETUP ERROR ===

Problem: Could not identify two agents in your input.

Input received: $ARGUMENTS

Expected format:
  /debate <agent1> <agent2> <rounds> <topic>

Available agents:
  - philosophical-analyst (rigorous argument analysis)
  - philosophical-generator (creative ideation)
  - devils-advocate (systematic objections)
  - thought-experimenter (thought experiment design)
  - symposiarch (debate orchestration)
  - philosophical-historian (genealogical analysis)
  - cross-cultural-bridge (cross-traditional translation)
  - radical-innovator (iconoclastic thinking)
  - concept-mapper (visual structure mapping)

Examples:
  /debate philosophical-analyst devils-advocate 5 Is free will compatible with determinism?
  /debate thought-experimenter radical-innovator 4 What is the nature of consciousness?
```
**STOP** - do not proceed.

**Check 2: Agent existence**
Verify both agents exist:
```bash
test -f .claude/agents/<agent1>.md && echo "Agent 1 exists" || echo "Agent 1 NOT FOUND"
test -f .claude/agents/<agent2>.md && echo "Agent 2 exists" || echo "Agent 2 NOT FOUND"
```

If either agent not found:
```
=== DEBATE SETUP ERROR ===

Problem: Agent '<agent_name>' not found in .claude/agents/

Available agents:
  [list all .md files in .claude/agents/]

Did you mean one of these?
  [suggest similar names if possible]
```
**STOP** - do not proceed.

**Check 3: Topic validation**
If topic is empty or looks like an agent name:
```
=== DEBATE SETUP ERROR ===

Problem: Missing or invalid topic.

Your input: $ARGUMENTS
Detected agents: <agent1>, <agent2>
Detected rounds: <rounds>
Detected topic: <empty or agent-like string>

The topic should be a philosophical question or statement, not an agent name.

Examples:
  /debate philosophical-analyst devils-advocate 5 Is consciousness physical?
  /debate thought-experimenter radical-innovator 4 What is the nature of time?
  /debate cross-cultural-bridge philosophical-historian 3 Can Western and Eastern ethics be reconciled?
```
**STOP** - do not proceed.

**Check 3.5: Rounds validation**
If rounds is not a positive integer or is missing:
```
=== DEBATE SETUP ERROR ===

Problem: Invalid or missing rounds parameter.

Input received: $ARGUMENTS
Detected agents: <agent1>, <agent2>
Third token: <token> (expected positive integer)

The rounds parameter must be a positive integer (e.g., 3, 5, 7).
Recommended range: 2-7 rounds for substantive debate.

Expected format:
  /debate <agent1> <agent2> <rounds> <topic>

Examples:
  /debate philosophical-analyst devils-advocate 5 Is free will compatible with determinism?
  /debate thought-experimenter radical-innovator 3 What is the nature of consciousness?
```
**STOP** - do not proceed.

**Check 3.6: Rounds range warning**
If rounds > 10:
Display warning but continue:
```
⚠️ WARNING: High round count ({rounds})

Debates with more than 10 rounds may become repetitive.
Recommended: 3-7 rounds for most topics.

Proceeding with {rounds} rounds...
```

**Check 4: Same agent detection**
If agent1 == agent2:
```
=== DEBATE SETUP ERROR ===

Problem: You specified the same agent twice: <agent_name>

A debate requires two different perspectives. Try combining:
  - philosophical-analyst + devils-advocate (analysis vs objections)
  - thought-experimenter + radical-innovator (scenarios vs assumptions)
  - cross-cultural-bridge + philosophical-historian (cultures vs history)
```
**STOP** - do not proceed.

---

## Step 2: Setup Debate

### 2.1 Create Orchestration Todo List

Use TodoWrite to track the debate:
```
1. [in_progress] Validate input parameters
2. [pending] Agent 1 opening position
3. [pending] Agent 2 response
4. [pending] Dialectical exchange rounds
5. [pending] Detect synthesis or impasse
6. [pending] Closing statements
7. [pending] Generate debate summary
```

### 2.2 Load Agent Descriptions

Read both agent files to understand their capabilities:
```
Read: .claude/agents/<agent1>.md (first 30 lines - get description and skills)
Read: .claude/agents/<agent2>.md (first 30 lines - get description and skills)
```

### 2.3 Announce Debate

Display to user:
```
=== PHILOSOPHICAL DEBATE INITIATED ===

Topic: <topic>

Participants:
  1. <agent1_name> - <brief description from file>
  2. <agent2_name> - <brief description from file>

Format: Sequential Extended Dialogue
  - Opening positions
  - Multiple exchange rounds (max {rounds})
  - Closing statements

Convergence signals: Synthesis, Impasse, or Max Rounds

Beginning debate...
```

### 2.4 Initialize State
```
round = 0
max_rounds = <parsed_rounds_parameter>  // Use the rounds value from parsed input
synthesis_reached = false
impasse_detected = false
agent1_last_position = ""
agent2_last_position = ""
agent1_assigned_position = "AFFIRMATIVE"
agent2_assigned_position = "CRITICAL"
```

### 2.5 Assign Debate Positions

Analyze the topic to identify the core dialectical tension:
- If topic is a yes/no question → AFFIRMATIVE vs NEGATIVE
- If topic contrasts two ideas → SIDE_A vs SIDE_B
- If topic asks "what is X?" → REALIST vs ANTI-REALIST (or similar metaphysical split)
- If topic is normative → PROPONENT vs CRITIC

**Position Assignment (Automatic):**
- **Agent 1**: Takes the **AFFIRMATIVE / PRO** position
- **Agent 2**: Takes the **CRITICAL / CONTRA** position

Display to user:
```
Position Assignment:
  • <agent1_name>: Will argue FOR / AFFIRMATIVE position
  • <agent2_name>: Will argue AGAINST / CRITICAL position

Note: Positions are assigned to ensure dialectical tension.
      Agents may still reach synthesis if arguments genuinely compel it.
```

---

## Step 3: Opening Round

### 3.1 Agent 1 Opening

Invoke Agent 1 via Task tool:

```
Task(
  subagent_type: "<agent1>",
  prompt: """
  ULTRATHINK about this philosophical debate.

  You are <agent1_name> participating in a structured philosophical debate.

  TOPIC: <topic>
  OPPONENT: <agent2_name>

  ## YOUR ASSIGNED POSITION: AFFIRMATIVE / PRO

  You have been assigned to DEFEND the AFFIRMATIVE position on this topic.
  - If the topic is a question, argue for the "yes" answer
  - If the topic contrasts ideas, defend the first/dominant idea
  - If the topic asks "what is X?", argue for a robust positive account
  - If the topic is normative, argue FOR the proposition

  **IMPORTANT**: Even if you personally might lean the other way, your job is to:
  1. Find the STRONGEST possible arguments for this position
  2. Defend it vigorously and charitably
  3. Anticipate and preempt objections
  4. Only concede ground when philosophically compelled by superior arguments

  This is not mere devil's advocacy - argue as if you genuinely hold this position.

  ## Step 1: Create Your Todo List
  Use TodoWrite to plan your argument development:
  1. Analyze the philosophical question from the AFFIRMATIVE perspective
  2. Identify the strongest philosophical arguments FOR the position
  3. Formulate your core thesis defending the affirmative view
  4. Develop supporting arguments with warrants
  5. Anticipate likely objections from the CRITICAL side
  6. Prepare rebuttals to those objections

  ## Step 2: Deliver Your Opening Position
  Present your opening position with:
  - A clear, defensible thesis statement DEFENDING the affirmative view
  - 2-3 primary supporting arguments (each with reasoning, not just assertions)
  - Acknowledgment of the question's genuine complexity
  - Preview of how you'll respond to likely objections from the critical side

  ## Debate Guidelines:
  - Be intellectually rigorous but advocate vigorously for your position
  - Steel-man the opposing view, but argue against it
  - Every claim requires a warrant (reasoning, evidence, or philosophical grounding)
  - Engage dialectically - build on ideas, don't just assert
  - Aim for genuine insight while defending your assigned position

  Begin your opening now.
  """,
  model: "opus"
)
```

**Wait for completion**, then:
- Store response as `agent1_opening`
- Display: `### <Agent1 Name> - Opening Position\n<response>`
- Update todo: Mark "Agent 1 opening position" as completed

### 3.1.5 Understanding Verification Protocol

**CRITICAL DESIGN PRINCIPLE**: Agents must demonstrate understanding BEFORE responding.

This is the core mechanism that prevents "talking past each other":

```
┌─────────────────────────────────────────────────────────────────────┐
│  BEFORE (Agents talk past each other)                               │
│  ─────────────────────────────────────                              │
│  Agent 1: Makes argument X                                          │
│  Agent 2: Responds with Y (unrelated to X)                          │
│  Agent 1: Responds with Z (unrelated to Y)                          │
│  Result: No genuine engagement                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  AFTER (Agents genuinely engage)                                    │
│  ───────────────────────────────                                    │
│  Agent 1: Makes argument X                                          │
│  Agent 2: "I understand you claim X because A, B, C..."             │
│           → Now responds to ACTUAL X                                │
│  Agent 1: "You argued Y because D, E, F..."                         │
│           → Now responds to ACTUAL Y                                │
│  Result: Genuine dialectical exchange                               │
└─────────────────────────────────────────────────────────────────────┘
```

**The Gate Structure**:
1. Every agent response MUST BEGIN with understanding verification
2. Understanding verification comes BEFORE any counter-arguments
3. Response must reference the restated arguments (not assumed versions)

**Why This Works**:
- Forces agents to actually read and process opponent's position
- Makes strawmanning immediately visible (restatement vs actual text)
- Grounds responses in what opponent SAID, not what agent assumes
- Creates feedback loop: if understanding is wrong, opponent can correct

---

### 3.2 Agent 2 Response

Invoke Agent 2 with Agent 1's opening:

```
Task(
  subagent_type: "<agent2>",
  prompt: """
  ULTRATHINK about this philosophical debate.

  You are <agent2_name> participating in a structured philosophical debate.

  TOPIC: <topic>
  OPPONENT: <agent1_name>

  ## Your Opponent's Opening Position:
  <agent1_opening>

  ---

  ## YOUR ASSIGNED POSITION: CRITICAL / CONTRA

  You have been assigned to CHALLENGE and OPPOSE your opponent's position.
  - If they argued "yes", you argue "no" (or "it's fundamentally more complicated")
  - If they defended X, you challenge X or defend its alternative
  - Your job is to find the STRONGEST possible objections and alternatives

  **IMPORTANT**: Even if you found their arguments persuasive, your job is to:
  1. Find the STRONGEST possible counter-arguments
  2. Expose hidden assumptions and weaknesses
  3. Present alternative frameworks or positions
  4. Only concede ground when philosophically compelled by superior reasoning

  This is not mere contrarianism - argue as if you genuinely oppose their view.

  ## Step 1: Demonstrate Understanding (REQUIRED - GATES STEP 2)

  **CRITICAL**: Before formulating ANY response, you MUST demonstrate that you
  accurately understand your opponent's position. This is NOT optional.

  Your response MUST BEGIN with an understanding verification section:

  1. **Restate Core Thesis**: "I understand your central claim to be: [one sentence summary]"
  2. **Identify Key Arguments**: "You support this with: (a) [argument 1], (b) [argument 2], (c) [argument 3]"
  3. **Acknowledge Strongest Point**: "Your most compelling argument is [X] because [why it's strong]"

  DO NOT proceed to Step 2 until you have completed Step 1 in your response.
  Responses that skip understanding verification are INCOMPLETE.

  ## Step 2: Create Your Todo List
  Use TodoWrite to plan your counter-argument:
  1. Verify you've completed understanding demonstration (Step 1)
  2. Identify weaknesses in their SPECIFIC arguments (not strawmen)
  3. Formulate your CRITICAL thesis opposing their view
  4. Develop counter-arguments that engage their actual claims
  5. Anticipate how opponent will defend against your objections
  6. Prepare responses to their likely rebuttals

  ## Step 3: Deliver Your Opening Response
  Respond to your opponent with:
  - Your understanding verification from Step 1 (MUST come first)
  - A clear statement of your CRITICAL position opposing their view
  - Your counter-thesis and supporting arguments
  - Specific challenges to their key claims (reference what they actually said)
  - Questions that expose tensions in their STATED view (not assumed view)

  ## Debate Guidelines:
  - Be intellectually rigorous but advocate vigorously AGAINST their position
  - Steel-man briefly, then attack the strongest version of their argument
  - Every claim requires a warrant (reasoning, evidence, or philosophical grounding)
  - Engage dialectically - respond to what was actually said
  - Aim for genuine insight while maintaining your critical stance

  Begin your response now.
  """,
  model: "opus"
)
```

**Wait for completion**, then:
- Store response as `agent2_response`
- Display: `### <Agent2 Name> - Opening Response\n<response>`
- Update todo: Mark "Agent 2 response" as completed, set "Dialectical exchange rounds" to in_progress

---

## Step 4: Dialectical Exchange Loop

```
WHILE (round < max_rounds AND NOT synthesis_reached AND NOT impasse_detected):
    round += 1
```

### 4.1 Agent 1 Turn

```
Task(
  subagent_type: "<agent1>",
  prompt: """
  ULTRATHINK about your response in this ongoing debate.

  ## Debate Context:
  TOPIC: <topic>
  OPPONENT: <agent2_name>
  ROUND: <round> of <max_rounds>

  ## POSITION REMINDER: You are defending the AFFIRMATIVE position
  Maintain your assigned stance while engaging honestly with arguments.
  You may acknowledge strong points, but don't abandon your position
  unless you've been genuinely convinced by superior philosophical reasoning.

  ## Your Opponent's Last Argument:
  <agent2_last_response>

  ---

  ## STEP A: Understanding Verification (REQUIRED)

  **CRITICAL**: Before responding, you MUST demonstrate understanding of your opponent's
  last argument. Your response MUST BEGIN with this verification:

  1. "Your argument in the last round was: [one-sentence restatement of their core claim]"
  2. "Your strongest new point was: [identify their best argument]"
  3. "You challenged my position by arguing: [their main objection to you]"

  DO NOT proceed to Step B until you have completed Step A in your response.

  ## STEP B: Response (Only after completing Step A)

  Respond to your opponent's SPECIFIC arguments from Step A:

  1. **Engage Directly**: Address their arguments AS YOU RESTATED THEM (not assumed versions)
  2. **Challenge**: Where is their CRITICAL view wrong? Reference what they actually said
  3. **Defend**: Respond to their specific objections from Step A (not strawmen)
  4. **Advance**: New arguments that BUILD ON this exchange, not ignore it

  ## Convergence Check (Use Sparingly):
  Only signal synthesis if you've been GENUINELY convinced by superior reasoning:
  - State: "I find myself compelled to agree on [specific point]"
  - Explain SPECIFICALLY what argument changed your view
  - Articulate what you now believe and why

  WARNING: Acknowledging a good point is NOT the same as synthesis.
  Partial agreement while maintaining your core position is NOT synthesis.
  Only signal synthesis if you would now argue FOR your opponent's thesis.

  If you're at an IMPASSE (genuine philosophical deadlock), signal this:
  - State: "We appear to have reached an irreducible disagreement"
  - Clarify what the core disagreement is
  - Explain why it may be genuinely undecidable

  ## Guidelines:
  - Be concise but substantive
  - Directly address what your opponent said
  - New arguments should advance YOUR AFFIRMATIVE position
  - Philosophical charity: interpret them at their best, then argue against it

  Respond now.
  """,
  model: "opus"
)
```

**After response**:
- Check for synthesis signals ("I agree", "common ground", "synthesis", "compelled")
- Check for impasse signals ("irreducible disagreement", "impasse", "undecidable")
- Check for repetition (similar to previous position)
- Store as `agent1_last_position`
- Display response

### 4.2 Agent 2 Turn

```
Task(
  subagent_type: "<agent2>",
  prompt: """
  ULTRATHINK about your response in this ongoing debate.

  ## Debate Context:
  TOPIC: <topic>
  OPPONENT: <agent1_name>
  ROUND: <round> of <max_rounds>

  ## POSITION REMINDER: You are defending the CRITICAL position
  Maintain your assigned stance while engaging honestly with arguments.
  You may acknowledge strong points, but don't abandon your opposition
  unless you've been genuinely convinced by superior philosophical reasoning.

  ## Your Opponent's Last Argument:
  <agent1_last_response>

  ---

  ## STEP A: Understanding Verification (REQUIRED)

  **CRITICAL**: Before responding, you MUST demonstrate understanding of your opponent's
  last argument. Your response MUST BEGIN with this verification:

  1. "Your argument in the last round was: [one-sentence restatement of their core claim]"
  2. "Your strongest new point was: [identify their best argument]"
  3. "You defended your position by arguing: [their main defense]"

  DO NOT proceed to Step B until you have completed Step A in your response.

  ## STEP B: Response (Only after completing Step A)

  Respond to your opponent's SPECIFIC arguments from Step A:

  1. **Engage Directly**: Address their arguments AS YOU RESTATED THEM (not assumed versions)
  2. **Challenge**: Where is their AFFIRMATIVE view wrong? Reference what they actually said
  3. **Defend**: Respond to their specific arguments from Step A (not strawmen)
  4. **Advance**: New objections that BUILD ON this exchange, not ignore it

  ## Convergence Check (Use Sparingly):
  Only signal synthesis if you've been GENUINELY convinced by superior reasoning:
  - State: "I find myself compelled to agree on [specific point]"
  - Explain SPECIFICALLY what argument changed your view
  - Articulate what you now believe and why

  WARNING: Acknowledging a good point is NOT the same as synthesis.
  Partial agreement while maintaining your core opposition is NOT synthesis.
  Only signal synthesis if you would now argue FOR your opponent's thesis.

  If you're at an IMPASSE (genuine philosophical deadlock), signal this:
  - State: "We appear to have reached an irreducible disagreement"
  - Clarify what the core disagreement is
  - Explain why it may be genuinely undecidable

  ## Guidelines:
  - Be concise but substantive
  - Directly address what your opponent said
  - New arguments should advance YOUR CRITICAL position
  - Philosophical charity: interpret them at their best, then argue against it

  Respond now.
  """,
  model: "opus"
)
```

**After response**:
- Check for synthesis signals ("I agree", "common ground", "synthesis", "compelled")
- Check for impasse signals ("irreducible disagreement", "impasse", "undecidable")
- Check for repetition (similar to previous position)
- Store as `agent2_last_position`
- Display response
- Continue loop or break

### 4.2.5 Understanding Validation (Orchestrator Check)

After each agent response, the orchestrator should verify understanding:

**Check 1: Did the response include understanding verification?**
- Look for: "I understand your claim to be...", "Your argument was...", "You argued that..."
- If MISSING: The agent may be talking past opponent
- Consider: Flagging response as incomplete, requesting revision

**Check 2: Does the restatement match what opponent actually said?**
- Compare agent's "I understand you to claim..." with opponent's actual text
- Flag significant divergences (strawmanning)
- Example of divergence:
  - Opponent said: "Free will requires libertarianism because determinism eliminates responsibility"
  - Agent restated: "You claim free will requires absence of causation" ← STRAWMAN

**Check 3: Does the response engage with restated arguments?**
- Look for: references to "your point about X", quotes, paraphrases
- If missing: Agent may have verified understanding then ignored it

**Note**: This is guidance for orchestrator evaluation. For now, this is not automated
checking - the orchestrator should use judgment about when to flag issues.

---

### 4.3 Convergence Detection

**IMPORTANT**: Debates should NOT converge too quickly. The goal is genuine philosophical exploration, not premature agreement.

After each exchange, check:

**Synthesis Detection (STRICT CRITERIA)**:
Synthesis requires ALL of the following:
1. At least 2 complete rounds have occurred (round >= 2)
2. Response contains EXPLICIT synthesis language: "I find myself compelled to agree", "you've convinced me on the core thesis", "I now hold your position"
3. The agent EXPLICITLY articulates what specific argument changed their view
4. The agent would now argue FOR their opponent's original position
5. **NEW**: The agent demonstrates ACCURATE understanding of what they're agreeing with
   - Must include: "I now accept your argument that [accurate restatement]"
   - Cannot be synthesis if agent misrepresents what they're agreeing to
   - The restatement must match opponent's actual stated position

**What does NOT count as synthesis:**
- Acknowledging a good point ("You're right that...")
- Partial agreement ("We agree on this aspect, but...")
- Finding common ground on secondary issues
- Polite concessions without position change
- Agreeing on definitions or framing

If genuine synthesis is detected:
- Set `synthesis_reached = true`
- Display: "SYNTHESIS REACHED: <agent> has been convinced by <argument>"
- Break loop

**Impasse Detection**:
- Response contains: "irreducible disagreement", "impasse", "fundamental disagreement", "we must agree to disagree"
- OR: Both agents repeat substantially similar positions twice in a row
- OR: Arguments become circular without new considerations
- Set `impasse_detected = true`
- Display: "IMPASSE DETECTED: Core disagreement is <description>"
- Break loop

**Max Rounds (Forced Convergence)**:
- If `round >= max_rounds`, exit loop naturally
- Neither synthesis nor impasse - debate simply reached time limit
- Display: "MAX ROUNDS REACHED: Debate continues without resolution"

---

## Step 5: Closing Round

### 5.1 Agent 1 Closing

```
Task(
  subagent_type: "<agent1>",
  prompt: """
  ULTRATHINK about your closing statement.

  ## Debate Summary:
  TOPIC: <topic>
  OPPONENT: <agent2_name>
  ROUNDS COMPLETED: <round>
  OUTCOME: <SYNTHESIS | IMPASSE | MAX_ROUNDS>

  ---

  ## Deliver Your Closing Statement:

  Provide a brief (3-5 paragraphs) closing that:

  1. **Final Position**: State your final position on the topic
  2. **Acknowledgments**: What did you learn from your opponent? What were their strongest points?
  3. **Concessions**: Any points where you've updated your view?
  4. **Remaining Disagreements**: What do you still disagree about, and why?
  5. **Philosophical Insight**: What broader insight emerged from this exchange?

  Be gracious, intellectually honest, and focused on truth-seeking over victory.
  """,
  model: "opus"
)
```

### 5.2 Agent 2 Closing

```
Task(
  subagent_type: "<agent2>",
  prompt: """
  ULTRATHINK about your closing statement.

  ## Debate Summary:
  TOPIC: <topic>
  OPPONENT: <agent1_name>
  ROUNDS COMPLETED: <round>
  OUTCOME: <SYNTHESIS | IMPASSE | MAX_ROUNDS>

  ## Opponent's Closing:
  <agent1_closing>

  ---

  ## Deliver Your Closing Statement:

  Provide a brief (3-5 paragraphs) closing that:

  1. **Final Position**: State your final position on the topic
  2. **Acknowledgments**: What did you learn from your opponent? What were their strongest points?
  3. **Concessions**: Any points where you've updated your view?
  4. **Remaining Disagreements**: What do you still disagree about, and why?
  5. **Philosophical Insight**: What broader insight emerged from this exchange?

  Be gracious, intellectually honest, and focused on truth-seeking over victory.
  """,
  model: "opus"
)
```

---

## Step 6: Generate Report

Display final summary:

```
=== DEBATE COMPLETE ===

Topic: <topic>
Participants: <agent1> vs <agent2>
Rounds: <total_rounds>
Outcome: <SYNTHESIS | IMPASSE | MAX_ROUNDS_REACHED>

---

## Opening Positions

### <Agent1 Name>:
<1-2 sentence summary of opening thesis>

### <Agent2 Name>:
<1-2 sentence summary of opening thesis>

---

## Dialectical Exchange Highlights

### Round 1:
<Agent1>: <key point or move>
<Agent2>: <key response>

### Round 2:
<Agent1>: <key point or move>
<Agent2>: <key response>

[... additional rounds ...]

---

## Closing Statements

### <Agent1 Name>:
<summary of closing position>

### <Agent2 Name>:
<summary of closing position>

---

## Philosophical Insights

### Areas of Agreement:
- <point 1>
- <point 2>

### Genuine Disagreements:
- <irreducible difference 1 and why>
- <irreducible difference 2 and why>

### Key Insights Generated:
- <insight 1 that emerged from the dialectic>
- <insight 2>

### Open Questions:
- <question that remains unanswered>

---

Debate orchestrated by /debate command.
```

---

## Step 7: Generate HTML Visualization

After the report, generate a beautiful interactive HTML webpage displaying the debate as a chat interface.

### 7.1 Extract Agent Profile Data

For each agent, read the first 50 lines of their profile file and extract:

```
Read: .claude/agents/<agent1>.md (first 50 lines)
Read: .claude/agents/<agent2>.md (first 50 lines)
```

**Extract from YAML frontmatter:**
- `name` - agent identifier
- `description` - brief description of the agent's role
- `model` - model used (usually "opus")

**Extract from content:**
- First paragraph after frontmatter = mission statement
- Any listed competencies or intellectual virtues (first 3-5)

### 7.2 Agent Icons Mapping

Use these icons for each agent type:
```
philosophical-analyst: 🔍
philosophical-generator: 💡
devils-advocate: 👹
thought-experimenter: 🧪
symposiarch: 🎭
philosophical-historian: 📜
cross-cultural-bridge: 🌉
radical-innovator: ⚡
concept-mapper: 🗺️
```

### 7.3 Generate HTML File

Create a complete, self-contained HTML file with embedded CSS and JavaScript.

**Filename pattern:**
```
/tmp/cc_genui_debate_<topic_slug>_<YYYYMMDD>_<HHMMSS>.html
```

**Example:**
```
/tmp/cc_genui_debate_free_will_determinism_20251230_143052.html
```

### 7.4 Complete HTML Template

Write this HTML structure (with all placeholders replaced with actual debate data):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Philosophical Debate: {TOPIC}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
    <style>
        /* ========================================
           MODERN ACADEMIC DESIGN SYSTEM
           ======================================== */

        :root {
            /* Color Palette */
            --color-ink: #1a1a2e;
            --color-slate: #4a4a68;
            --color-gold: #c9a227;
            --color-agent1: #2563eb;
            --color-agent1-bg: #eff6ff;
            --color-agent1-border: #bfdbfe;
            --color-agent2: #7c3aed;
            --color-agent2-bg: #f5f3ff;
            --color-agent2-border: #ddd6fe;
            --color-ivory: #fdfcfa;
            --color-paper: #ffffff;
            --color-border: #e5e2dc;
            --color-muted: #6b7280;
            --color-success: #059669;
            --color-warning: #d97706;
            --color-error: #dc2626;

            /* Typography */
            --font-display: 'Crimson Text', Georgia, serif;
            --font-body: 'Source Serif 4', Georgia, serif;
            --font-ui: 'Inter', system-ui, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

            /* Spacing */
            --space-xs: 0.25rem;
            --space-sm: 0.5rem;
            --space-md: 1rem;
            --space-lg: 1.5rem;
            --space-xl: 2rem;
            --space-2xl: 3rem;

            /* Shadows */
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: var(--font-body);
            font-size: 1.0625rem;
            line-height: 1.7;
            color: var(--color-ink);
            background: var(--color-ivory);
            min-height: 100vh;
        }

        /* ========================================
           HEADER & HERO
           ======================================== */

        .debate-header {
            background: linear-gradient(135deg, var(--color-ink) 0%, #2d2d4a 100%);
            color: white;
            padding: var(--space-2xl) var(--space-xl);
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .debate-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            opacity: 0.5;
        }

        .debate-header-content {
            position: relative;
            z-index: 1;
            max-width: 900px;
            margin: 0 auto;
        }

        .debate-label {
            font-family: var(--font-ui);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-gold);
            margin-bottom: var(--space-sm);
        }

        .debate-topic {
            font-family: var(--font-display);
            font-size: 2.25rem;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: var(--space-lg);
            text-wrap: balance;
        }

        .debate-meta {
            display: flex;
            justify-content: center;
            gap: var(--space-lg);
            flex-wrap: wrap;
            font-family: var(--font-ui);
            font-size: 0.875rem;
        }

        .meta-item {
            display: flex;
            align-items: center;
            gap: var(--space-xs);
            opacity: 0.9;
        }

        .outcome-badge {
            display: inline-flex;
            align-items: center;
            gap: var(--space-xs);
            padding: var(--space-xs) var(--space-sm);
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .outcome-synthesis {
            background: rgba(5, 150, 105, 0.2);
            color: #6ee7b7;
        }

        .outcome-impasse {
            background: rgba(217, 119, 6, 0.2);
            color: #fcd34d;
        }

        .outcome-maxrounds {
            background: rgba(107, 114, 128, 0.2);
            color: #d1d5db;
        }

        /* ========================================
           PARTICIPANTS SECTION
           ======================================== */

        .participants {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: var(--space-lg);
            max-width: 1000px;
            margin: calc(-1 * var(--space-xl)) auto var(--space-xl);
            padding: 0 var(--space-lg);
            position: relative;
            z-index: 10;
        }

        .agent-card {
            background: var(--color-paper);
            border-radius: 12px;
            padding: var(--space-lg);
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--color-border);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .agent-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg), 0 0 0 1px var(--color-gold);
        }

        .agent-card.agent-1 {
            border-top: 4px solid var(--color-agent1);
        }

        .agent-card.agent-2 {
            border-top: 4px solid var(--color-agent2);
        }

        .agent-header {
            display: flex;
            align-items: center;
            gap: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .agent-icon {
            font-size: 2rem;
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
        }

        .agent-1 .agent-icon {
            background: var(--color-agent1-bg);
        }

        .agent-2 .agent-icon {
            background: var(--color-agent2-bg);
        }

        .agent-name {
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--color-ink);
        }

        .agent-1 .agent-name { color: var(--color-agent1); }
        .agent-2 .agent-name { color: var(--color-agent2); }

        .agent-description {
            font-size: 0.9375rem;
            color: var(--color-slate);
            margin-bottom: var(--space-md);
            line-height: 1.6;
        }

        .agent-badges {
            display: flex;
            flex-wrap: wrap;
            gap: var(--space-xs);
        }

        .badge {
            font-family: var(--font-ui);
            font-size: 0.6875rem;
            font-weight: 500;
            padding: 2px 8px;
            border-radius: 4px;
            background: var(--color-border);
            color: var(--color-slate);
        }

        .agent-1 .badge { background: var(--color-agent1-bg); color: var(--color-agent1); }
        .agent-2 .badge { background: var(--color-agent2-bg); color: var(--color-agent2); }

        .vs-divider {
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--font-display);
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--color-gold);
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        /* ========================================
           TOOLBAR
           ======================================== */

        .toolbar {
            position: sticky;
            top: 0;
            background: var(--color-paper);
            border-bottom: 1px solid var(--color-border);
            padding: var(--space-md) var(--space-lg);
            z-index: 100;
            box-shadow: var(--shadow-sm);
        }

        .toolbar-content {
            max-width: 900px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: var(--space-md);
            flex-wrap: wrap;
        }

        .round-nav {
            display: flex;
            gap: var(--space-xs);
            align-items: center;
        }

        .round-btn {
            font-family: var(--font-ui);
            font-size: 0.8125rem;
            font-weight: 500;
            padding: var(--space-xs) var(--space-sm);
            border: 1px solid var(--color-border);
            border-radius: 6px;
            background: var(--color-paper);
            color: var(--color-slate);
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .round-btn:hover {
            background: var(--color-ivory);
            border-color: var(--color-slate);
        }

        .round-btn.active {
            background: var(--color-ink);
            color: white;
            border-color: var(--color-ink);
        }

        .search-box {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            background: var(--color-ivory);
            border: 1px solid var(--color-border);
            border-radius: 8px;
            padding: var(--space-xs) var(--space-sm);
            flex: 1;
            max-width: 300px;
        }

        .search-box:focus-within {
            border-color: var(--color-gold);
            box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.1);
        }

        .search-input {
            font-family: var(--font-ui);
            font-size: 0.875rem;
            border: none;
            background: transparent;
            outline: none;
            flex: 1;
            min-width: 100px;
        }

        .search-nav {
            display: flex;
            gap: 2px;
            align-items: center;
        }

        .search-nav-btn {
            padding: 2px 6px;
            border: none;
            background: transparent;
            cursor: pointer;
            color: var(--color-slate);
            border-radius: 4px;
        }

        .search-nav-btn:hover {
            background: var(--color-border);
        }

        .search-count {
            font-family: var(--font-ui);
            font-size: 0.75rem;
            color: var(--color-muted);
            padding: 0 var(--space-xs);
        }

        /* ========================================
           TRANSCRIPT
           ======================================== */

        .transcript {
            max-width: 900px;
            margin: 0 auto;
            padding: var(--space-xl) var(--space-lg);
        }

        .section-title {
            font-family: var(--font-display);
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--color-ink);
            margin-bottom: var(--space-lg);
            padding-bottom: var(--space-sm);
            border-bottom: 2px solid var(--color-border);
            display: flex;
            align-items: center;
            gap: var(--space-sm);
        }

        .round-section {
            margin-bottom: var(--space-2xl);
            scroll-margin-top: 80px;
        }

        .round-label {
            font-family: var(--font-ui);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-muted);
            margin-bottom: var(--space-md);
        }

        .message {
            position: relative;
            margin-bottom: var(--space-lg);
            padding: var(--space-lg);
            border-radius: 12px;
            max-width: 90%;
        }

        .message.agent-1 {
            background: var(--color-agent1-bg);
            border: 1px solid var(--color-agent1-border);
            margin-right: auto;
            border-left: 4px solid var(--color-agent1);
        }

        .message.agent-2 {
            background: var(--color-agent2-bg);
            border: 1px solid var(--color-agent2-border);
            margin-left: auto;
            border-right: 4px solid var(--color-agent2);
            border-left: none;
        }

        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--space-md);
            padding-bottom: var(--space-sm);
            border-bottom: 1px solid currentColor;
            opacity: 0.3;
        }

        .message-agent {
            font-family: var(--font-ui);
            font-size: 0.875rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: var(--space-xs);
        }

        .message.agent-1 .message-agent { color: var(--color-agent1); }
        .message.agent-2 .message-agent { color: var(--color-agent2); }

        .message-header {
            border-bottom-color: var(--color-border);
            opacity: 1;
        }

        .copy-btn {
            font-family: var(--font-ui);
            font-size: 0.75rem;
            padding: 4px 8px;
            border: 1px solid var(--color-border);
            border-radius: 4px;
            background: var(--color-paper);
            color: var(--color-muted);
            cursor: pointer;
            transition: all 0.15s ease;
            opacity: 0;
        }

        .message:hover .copy-btn {
            opacity: 1;
        }

        .copy-btn:hover {
            background: var(--color-ink);
            color: white;
            border-color: var(--color-ink);
        }

        .copy-btn.copied {
            background: var(--color-success);
            color: white;
            border-color: var(--color-success);
        }

        .message-content {
            font-size: 1rem;
            line-height: 1.8;
        }

        .message-content p {
            margin-bottom: var(--space-md);
        }

        .message-content p:last-child {
            margin-bottom: 0;
        }

        .message-content strong {
            font-weight: 600;
            color: var(--color-ink);
        }

        .message-content em {
            font-style: italic;
        }

        .message-content ul, .message-content ol {
            margin: var(--space-md) 0;
            padding-left: var(--space-lg);
        }

        .message-content li {
            margin-bottom: var(--space-xs);
        }

        .message-content blockquote {
            margin: var(--space-md) 0;
            padding: var(--space-md) var(--space-lg);
            border-left: 3px solid var(--color-gold);
            background: rgba(201, 162, 39, 0.05);
            font-style: italic;
        }

        .message-content h3, .message-content h4 {
            font-family: var(--font-display);
            margin: var(--space-lg) 0 var(--space-sm);
        }

        .message-content h3 { font-size: 1.125rem; }
        .message-content h4 { font-size: 1rem; }

        .highlight {
            background: rgba(201, 162, 39, 0.3);
            padding: 0 2px;
            border-radius: 2px;
        }

        .highlight.current {
            background: var(--color-gold);
            color: white;
        }

        /* ========================================
           SUMMARY
           ======================================== */

        .summary {
            background: var(--color-paper);
            border-top: 1px solid var(--color-border);
            padding: var(--space-2xl) var(--space-lg);
        }

        .summary-content {
            max-width: 900px;
            margin: 0 auto;
        }

        .summary-title {
            font-family: var(--font-display);
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--color-ink);
            text-align: center;
            margin-bottom: var(--space-xl);
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: var(--space-lg);
        }

        .summary-card {
            background: var(--color-ivory);
            border-radius: 12px;
            padding: var(--space-lg);
            border: 1px solid var(--color-border);
        }

        .summary-card h3 {
            font-family: var(--font-ui);
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: var(--space-md);
            display: flex;
            align-items: center;
            gap: var(--space-sm);
        }

        .summary-card.agreements h3 { color: var(--color-success); }
        .summary-card.disagreements h3 { color: var(--color-error); }
        .summary-card.insights h3 { color: var(--color-gold); }
        .summary-card.questions h3 { color: var(--color-agent2); }

        .summary-card ul {
            list-style: none;
            font-size: 0.9375rem;
        }

        .summary-card li {
            padding: var(--space-xs) 0;
            padding-left: var(--space-md);
            position: relative;
        }

        .summary-card li::before {
            content: '•';
            position: absolute;
            left: 0;
            color: var(--color-muted);
        }

        /* ========================================
           FOOTER
           ======================================== */

        .debate-footer {
            text-align: center;
            padding: var(--space-xl);
            color: var(--color-muted);
            font-family: var(--font-ui);
            font-size: 0.875rem;
            border-top: 1px solid var(--color-border);
        }

        .debate-footer a {
            color: var(--color-gold);
            text-decoration: none;
        }

        .debate-footer a:hover {
            text-decoration: underline;
        }

        /* ========================================
           RESPONSIVE
           ======================================== */

        @media (max-width: 768px) {
            .participants {
                grid-template-columns: 1fr;
                margin-top: var(--space-lg);
            }

            .vs-divider {
                padding: var(--space-sm) 0;
            }

            .debate-topic {
                font-size: 1.75rem;
            }

            .message {
                max-width: 100%;
            }

            .toolbar-content {
                flex-direction: column;
            }

            .search-box {
                max-width: 100%;
            }
        }

        /* ========================================
           PRINT
           ======================================== */

        @media print {
            .toolbar, .copy-btn {
                display: none;
            }

            .debate-header {
                background: white;
                color: black;
                border-bottom: 2px solid black;
            }

            .message {
                break-inside: avoid;
                max-width: 100%;
            }

            .participants {
                margin-top: 0;
            }

            .agent-card {
                box-shadow: none;
                border: 1px solid #ccc;
            }
        }
    </style>
</head>
<body>
    <!-- HEADER -->
    <header class="debate-header">
        <div class="debate-header-content">
            <div class="debate-label">Philosophical Debate</div>
            <h1 class="debate-topic">{TOPIC}</h1>
            <div class="debate-meta">
                <span class="meta-item">📅 {DATE}</span>
                <span class="meta-item">🔄 {ROUNDS} Rounds</span>
                <span class="outcome-badge {OUTCOME_CLASS}">{OUTCOME_ICON} {OUTCOME}</span>
            </div>
        </div>
    </header>

    <!-- PARTICIPANTS -->
    <section class="participants">
        <article class="agent-card agent-1">
            <div class="agent-header">
                <div class="agent-icon">{AGENT1_ICON}</div>
                <h2 class="agent-name">{AGENT1_DISPLAY_NAME}</h2>
            </div>
            <p class="agent-description">{AGENT1_DESCRIPTION}</p>
            <div class="agent-badges">
                {AGENT1_BADGES}
            </div>
        </article>

        <div class="vs-divider">VS</div>

        <article class="agent-card agent-2">
            <div class="agent-header">
                <div class="agent-icon">{AGENT2_ICON}</div>
                <h2 class="agent-name">{AGENT2_DISPLAY_NAME}</h2>
            </div>
            <p class="agent-description">{AGENT2_DESCRIPTION}</p>
            <div class="agent-badges">
                {AGENT2_BADGES}
            </div>
        </article>
    </section>

    <!-- TOOLBAR -->
    <nav class="toolbar">
        <div class="toolbar-content">
            <div class="round-nav">
                <button class="round-btn active" data-section="opening">Opening</button>
                {ROUND_BUTTONS}
                <button class="round-btn" data-section="closing">Closing</button>
            </div>

            <div class="search-box">
                <span>🔍</span>
                <input type="text" class="search-input" placeholder="Search transcript..." id="searchInput">
                <div class="search-nav">
                    <span class="search-count" id="searchCount"></span>
                    <button class="search-nav-btn" id="prevMatch" title="Previous (Shift+Enter)">↑</button>
                    <button class="search-nav-btn" id="nextMatch" title="Next (Enter)">↓</button>
                    <button class="search-nav-btn" id="clearSearch" title="Clear">✕</button>
                </div>
            </div>
        </div>
    </nav>

    <!-- TRANSCRIPT -->
    <main class="transcript">
        <!-- Opening Positions -->
        <section class="round-section" id="opening">
            <h2 class="section-title">📖 Opening Positions</h2>

            <article class="message agent-1">
                <div class="message-header">
                    <span class="message-agent">{AGENT1_ICON} {AGENT1_DISPLAY_NAME}</span>
                    <button class="copy-btn" onclick="copyMessage(this)">Copy</button>
                </div>
                <div class="message-content">
                    {AGENT1_OPENING}
                </div>
            </article>

            <article class="message agent-2">
                <div class="message-header">
                    <span class="message-agent">{AGENT2_ICON} {AGENT2_DISPLAY_NAME}</span>
                    <button class="copy-btn" onclick="copyMessage(this)">Copy</button>
                </div>
                <div class="message-content">
                    {AGENT2_OPENING}
                </div>
            </article>
        </section>

        <!-- Dialectical Rounds -->
        {ROUND_SECTIONS}

        <!-- Closing Statements -->
        <section class="round-section" id="closing">
            <h2 class="section-title">🏁 Closing Statements</h2>

            <article class="message agent-1">
                <div class="message-header">
                    <span class="message-agent">{AGENT1_ICON} {AGENT1_DISPLAY_NAME}</span>
                    <button class="copy-btn" onclick="copyMessage(this)">Copy</button>
                </div>
                <div class="message-content">
                    {AGENT1_CLOSING}
                </div>
            </article>

            <article class="message agent-2">
                <div class="message-header">
                    <span class="message-agent">{AGENT2_ICON} {AGENT2_DISPLAY_NAME}</span>
                    <button class="copy-btn" onclick="copyMessage(this)">Copy</button>
                </div>
                <div class="message-content">
                    {AGENT2_CLOSING}
                </div>
            </article>
        </section>
    </main>

    <!-- SUMMARY -->
    <section class="summary">
        <div class="summary-content">
            <h2 class="summary-title">Philosophical Insights</h2>

            <div class="summary-grid">
                <div class="summary-card agreements">
                    <h3>✅ Areas of Agreement</h3>
                    <ul>
                        {AGREEMENTS_LIST}
                    </ul>
                </div>

                <div class="summary-card disagreements">
                    <h3>⚔️ Genuine Disagreements</h3>
                    <ul>
                        {DISAGREEMENTS_LIST}
                    </ul>
                </div>

                <div class="summary-card insights">
                    <h3>💎 Key Insights</h3>
                    <ul>
                        {INSIGHTS_LIST}
                    </ul>
                </div>

                <div class="summary-card questions">
                    <h3>❓ Open Questions</h3>
                    <ul>
                        {QUESTIONS_LIST}
                    </ul>
                </div>
            </div>
        </div>
    </section>

    <!-- FOOTER -->
    <footer class="debate-footer">
        <p>Debate orchestrated by <code>/debate</code> command</p>
        <p>Transcript saved to: <code>{MARKDOWN_PATH}</code></p>
    </footer>

    <!-- JAVASCRIPT -->
    <script>
        // ========================================
        // ROUND NAVIGATION
        // ========================================

        const roundBtns = document.querySelectorAll('.round-btn');
        const sections = document.querySelectorAll('.round-section');

        roundBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const sectionId = btn.dataset.section;
                const section = document.getElementById(sectionId);

                if (section) {
                    // Update active button
                    roundBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');

                    // Scroll to section
                    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT') return;

            const currentActive = document.querySelector('.round-btn.active');
            const btns = Array.from(roundBtns);
            const currentIndex = btns.indexOf(currentActive);

            if (e.key === 'ArrowRight' && currentIndex < btns.length - 1) {
                btns[currentIndex + 1].click();
            } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
                btns[currentIndex - 1].click();
            }
        });

        // Update active button on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const sectionId = entry.target.id;
                    roundBtns.forEach(btn => {
                        btn.classList.toggle('active', btn.dataset.section === sectionId);
                    });
                }
            });
        }, { threshold: 0.3 });

        sections.forEach(section => observer.observe(section));

        // ========================================
        // SEARCH FUNCTIONALITY
        // ========================================

        const searchInput = document.getElementById('searchInput');
        const searchCount = document.getElementById('searchCount');
        const prevMatchBtn = document.getElementById('prevMatch');
        const nextMatchBtn = document.getElementById('nextMatch');
        const clearSearchBtn = document.getElementById('clearSearch');

        let currentMatchIndex = 0;
        let matches = [];

        function clearHighlights() {
            document.querySelectorAll('.highlight').forEach(el => {
                const parent = el.parentNode;
                parent.replaceChild(document.createTextNode(el.textContent), el);
                parent.normalize();
            });
            matches = [];
            currentMatchIndex = 0;
            searchCount.textContent = '';
        }

        function highlightMatches(searchTerm) {
            clearHighlights();

            if (!searchTerm || searchTerm.length < 2) return;

            const messageContents = document.querySelectorAll('.message-content');
            const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');

            messageContents.forEach(content => {
                const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, null, false);
                const textNodes = [];

                while (walker.nextNode()) {
                    if (walker.currentNode.textContent.match(regex)) {
                        textNodes.push(walker.currentNode);
                    }
                }

                textNodes.forEach(node => {
                    const span = document.createElement('span');
                    span.innerHTML = node.textContent.replace(regex, '<mark class="highlight">$1</mark>');
                    node.parentNode.replaceChild(span, node);
                });
            });

            matches = document.querySelectorAll('.highlight');

            if (matches.length > 0) {
                currentMatchIndex = 0;
                updateMatchHighlight();
                searchCount.textContent = `1 of ${matches.length}`;
            } else {
                searchCount.textContent = 'No matches';
            }
        }

        function updateMatchHighlight() {
            matches.forEach((m, i) => {
                m.classList.toggle('current', i === currentMatchIndex);
            });

            if (matches[currentMatchIndex]) {
                matches[currentMatchIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
                searchCount.textContent = `${currentMatchIndex + 1} of ${matches.length}`;
            }
        }

        function goToNextMatch() {
            if (matches.length === 0) return;
            currentMatchIndex = (currentMatchIndex + 1) % matches.length;
            updateMatchHighlight();
        }

        function goToPrevMatch() {
            if (matches.length === 0) return;
            currentMatchIndex = (currentMatchIndex - 1 + matches.length) % matches.length;
            updateMatchHighlight();
        }

        let debounceTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                highlightMatches(e.target.value);
            }, 300);
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    goToPrevMatch();
                } else {
                    goToNextMatch();
                }
            } else if (e.key === 'Escape') {
                clearHighlights();
                searchInput.value = '';
                searchInput.blur();
            }
        });

        nextMatchBtn.addEventListener('click', goToNextMatch);
        prevMatchBtn.addEventListener('click', goToPrevMatch);
        clearSearchBtn.addEventListener('click', () => {
            clearHighlights();
            searchInput.value = '';
        });

        // ========================================
        // COPY FUNCTIONALITY
        // ========================================

        function copyMessage(btn) {
            const content = btn.closest('.message').querySelector('.message-content').innerText;

            navigator.clipboard.writeText(content).then(() => {
                btn.textContent = 'Copied!';
                btn.classList.add('copied');

                setTimeout(() => {
                    btn.textContent = 'Copy';
                    btn.classList.remove('copied');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                btn.textContent = 'Error';
            });
        }

        // Global keyboard shortcut: Ctrl/Cmd + F focuses search
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        });
    </script>
</body>
</html>
```

### 7.5 Markdown to HTML Conversion

When inserting debate content into the HTML template, convert markdown to HTML:

| Markdown | HTML |
|----------|------|
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `### Heading` | `<h3>Heading</h3>` |
| `#### Heading` | `<h4>Heading</h4>` |
| `- Item` | `<ul><li>Item</li></ul>` |
| `1. Item` | `<ol><li>Item</li></ol>` |
| `> Quote` | `<blockquote>Quote</blockquote>` |
| Empty line | `</p><p>` (new paragraph) |

Wrap all message content in `<p>` tags and handle line breaks appropriately.

### 7.6 Template Placeholders

Replace these placeholders with actual debate data:

| Placeholder | Value |
|-------------|-------|
| `{TOPIC}` | The debate topic/question |
| `{DATE}` | Formatted date (e.g., "December 30, 2025") |
| `{ROUNDS}` | Total number of rounds |
| `{OUTCOME}` | "Synthesis", "Impasse", or "Max Rounds" |
| `{OUTCOME_CLASS}` | "outcome-synthesis", "outcome-impasse", or "outcome-maxrounds" |
| `{OUTCOME_ICON}` | "🤝" for synthesis, "⚖️" for impasse, "🔄" for max rounds |
| `{AGENT1_ICON}` | Icon from 7.2 mapping |
| `{AGENT1_DISPLAY_NAME}` | Formatted agent name (e.g., "Philosophical Analyst") |
| `{AGENT1_DESCRIPTION}` | Brief description from agent file |
| `{AGENT1_BADGES}` | `<span class="badge">Badge1</span>...` |
| `{AGENT1_OPENING}` | Full opening statement (HTML converted) |
| `{AGENT1_CLOSING}` | Full closing statement (HTML converted) |
| `{AGENT2_*}` | Same as above for agent 2 |
| `{ROUND_BUTTONS}` | `<button class="round-btn" data-section="round1">Round 1</button>...` |
| `{ROUND_SECTIONS}` | Full HTML for each dialectical round |
| `{AGREEMENTS_LIST}` | `<li>Point 1</li>...` |
| `{DISAGREEMENTS_LIST}` | `<li>Point 1</li>...` |
| `{INSIGHTS_LIST}` | `<li>Insight 1</li>...` |
| `{QUESTIONS_LIST}` | `<li>Question 1</li>...` |
| `{MARKDOWN_PATH}` | Path to saved markdown file |

### 7.7 Generate Round Sections

For each dialectical round, generate this HTML:

```html
<section class="round-section" id="round{N}">
    <div class="round-label">Round {N}</div>

    <article class="message agent-1">
        <div class="message-header">
            <span class="message-agent">{AGENT1_ICON} {AGENT1_DISPLAY_NAME}</span>
            <button class="copy-btn" onclick="copyMessage(this)">Copy</button>
        </div>
        <div class="message-content">
            {AGENT1_ROUND_N_RESPONSE}
        </div>
    </article>

    <article class="message agent-2">
        <div class="message-header">
            <span class="message-agent">{AGENT2_ICON} {AGENT2_DISPLAY_NAME}</span>
            <button class="copy-btn" onclick="copyMessage(this)">Copy</button>
        </div>
        <div class="message-content">
            {AGENT2_ROUND_N_RESPONSE}
        </div>
    </article>
</section>
```

### 7.8 Write and Open HTML File

1. **Generate filename:**
   ```
   timestamp = current datetime formatted as YYYYMMDD_HHMMSS
   topic_slug = topic.lower().replace(' ', '_').replace(/[^a-z0-9_]/g, '')[:50]
   filename = f"/tmp/cc_genui_debate_{topic_slug}_{timestamp}.html"
   ```

2. **Write the file:**
   ```
   Write(
     file_path: filename,
     content: completed_html_template
   )
   ```

3. **Open in browser:**
   ```bash
   open {filename}
   ```

4. **Display confirmation:**
   ```
   === HTML VISUALIZATION GENERATED ===

   Interactive debate viewer opened in browser.

   File saved to: {filename}

   Features:
   • Round navigation with keyboard support (←/→)
   • Full-text search (Ctrl/Cmd+F)
   • Copy individual messages
   • Print-optimized stylesheet
   ```

---

## Step 8: Save Debate Transcript

After generating the HTML, also save the full debate to the `debates/` folder as markdown for archival.

### 8.1 Generate Filename

Create a filename using this pattern:
```
debates/YYYY-MM-DD_<topic_slug>_<agent1>_vs_<agent2>.md
```

**Slug Generation**:
1. Take the topic, convert to lowercase
2. Replace spaces with underscores
3. Remove special characters (keep only alphanumeric and underscores)
4. Truncate to 50 characters maximum

**Examples**:
- Topic: "Is free will compatible with determinism?"
- Slug: `is_free_will_compatible_with_determinism`
- Filename: `debates/2025-12-30_is_free_will_compatible_with_determinism_philosophical-analyst_vs_devils-advocate.md`

### 8.2 Ensure Folder Exists

```bash
mkdir -p debates
```

### 8.3 Write Full Transcript

Use the Write tool to create a markdown file with this structure:

```markdown
---
topic: "<full topic question>"
date: YYYY-MM-DD
participants:
  - name: <agent1>
    role: "Opening position"
  - name: <agent2>
    role: "Respondent"
rounds: <N>
outcome: <SYNTHESIS | IMPASSE | MAX_ROUNDS>
---

# Philosophical Debate: <Topic>

**Date:** YYYY-MM-DD
**Participants:** <Agent1> vs <Agent2>
**Outcome:** <Outcome>

---

## Opening Positions

### <Agent1 Name>

<FULL opening statement - not a summary>

---

### <Agent2 Name>

<FULL opening response - not a summary>

---

## Dialectical Exchange

### Round 1

#### <Agent1 Name>

<FULL response>

---

#### <Agent2 Name>

<FULL response>

---

### Round 2

[Continue for each round with FULL text]

---

## Closing Statements

### <Agent1 Name>

<FULL closing statement>

---

### <Agent2 Name>

<FULL closing statement>

---

## Summary

### Areas of Agreement
- <point 1>
- <point 2>

### Genuine Disagreements
- <disagreement 1>
- <disagreement 2>

### Key Insights
- <insight 1>
- <insight 2>

### Open Questions
- <question>

---

*Debate orchestrated by `/debate` command on YYYY-MM-DD*
```

**IMPORTANT**: Save the FULL text of all statements, not summaries. The transcript should be a complete record of the entire debate that can be read and understood independently.

### 8.4 Report File Location

After saving, display:

```
=== DEBATE SAVED ===

Transcript saved to: debates/<filename>.md

You can review the full debate at any time by reading this file.
```

---

## Important Notes

1. **ULTRATHINK everywhere**: Both agents and the orchestrator should ultrathink at each step
2. **Sequential execution**: Wait for each agent response before proceeding (no background tasks)
3. **Context preservation**: Each agent receives full context of opponent's previous argument
4. **Graceful convergence**: Detect synthesis naturally, don't force agreement
5. **Honest impasse**: If positions are genuinely incompatible, acknowledge it
6. **No winner declaration**: This is dialectic, not debate competition - insight is the goal
7. **Todo tracking**: Update the orchestration todo list throughout
8. **Model selection**: Use `opus` for sophisticated philosophical reasoning
9. **Persistent storage**: Always save both HTML and markdown versions
10. **Full text, not summaries**: The saved transcript must contain complete statements for future reference
11. **HTML visualization**: Always generate the interactive HTML viewer and open it in the browser
12. **Agent profiles**: Extract and display agent information prominently in the HTML header
13. **Self-contained HTML**: Embed all CSS and JavaScript inline - no external dependencies except fonts
14. **Interactive features**: Include round navigation, search, and copy functionality in the HTML
