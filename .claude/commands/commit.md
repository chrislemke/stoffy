---
description: Stage all changes, commit with a philosophical message, and push to remote
allowed-tools: Bash(git*)
argument-hint: [optional: additional context for commit message]
---

# Philosophical Commit: $ARGUMENTS

You are creating a git commit for a philosophical thought repository. Frame all changes in the language of intellectual inquiry.

## Step 1: Check Repository Status

Run `git status` to see what's changed.

**If no changes exist**: Report "No changes to commit. The repository rests in equipoise." and stop.

## Step 2: Stage All Changes

Run `git add -A` to stage all unstaged changes.

## Step 3: Analyze Changes

Run these commands to understand what changed:
- `git diff --staged --stat` for an overview
- `git diff --staged` for the actual content changes

**Identify**:
- Which themes are affected (life_meaning, consciousness, free_will, morality, existence, knowledge)
- Which thinkers are referenced
- Whether new thoughts are seeded or existing ones refined
- Whether sources or references are updated

## Step 4: Generate Philosophical Commit Message

Create a commit message that frames the changes as intellectual movements, not file operations.

### Title Guidelines

Use philosophical verbs:
- **Seed**: New thought or inquiry initiated
- **Explore**: Expanding into new territory
- **Refine**: Sharpening existing position
- **Synthesize**: Combining multiple threads
- **Challenge**: Questioning established position
- **Extend**: Building upon existing foundation
- **Articulate**: Clarifying or expressing more precisely
- **Integrate**: Weaving into broader framework
- **Question**: Raising new doubts or inquiries

### Title Examples

| Instead of... | Write... |
|---------------|----------|
| "Add consciousness thought" | "Seed inquiry into the phenomenology of awareness" |
| "Update Aristotle notes" | "Extend Aristotelian virtue framework" |
| "Fix typo in Kant profile" | "Refine articulation of Kantian categories" |
| "New thought about meaning" | "Explore the constitution of existential significance" |
| "Update multiple thinker refs" | "Synthesize cross-traditional philosophical threads" |

### Description Guidelines

Write 1-3 sentences that:
- Describe the philosophical significance of the changes
- Reference affected themes or thinkers when relevant
- Frame changes as part of an ongoing inquiry

If `$ARGUMENTS` was provided, incorporate that context into the message.

## Step 5: Execute Commit

Create the commit using heredoc format:

```bash
git commit -m "$(cat <<'EOF'
<philosophical title>

<1-3 sentence description of philosophical significance>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**CRITICAL**: Do NOT include `Co-Authored-By` trailer.

## Step 6: Push to Remote

After a successful commit, push the changes to the remote repository:

```bash
git push
```

If the push fails (e.g., upstream not set), try:

```bash
git push -u origin $(git branch --show-current)
```

**Handle errors gracefully**: If push fails due to network issues or authentication, report the error but note that the commit was successful locally.

## Step 7: Report Results

Display a summary:

```
=== COMMIT & PUSH COMPLETE ===

<commit hash (short)>

<full commit message>

Files affected:
  <list of changed files>

Themes touched: <themes>
Thinkers referenced: <thinkers if any>

Remote: <pushed to origin/branch-name> or <push failed: reason>
```

## Important Notes

1. **Do not ask for confirmation** - commit and push immediately after analysis
2. **Frame philosophically** - even mundane changes have intellectual context
3. **Be concise but meaningful** - title under 72 characters
4. **Honor the inquiry** - every change is part of the philosophical journey
5. **Push completes the cycle** - thoughts shared are thoughts preserved
