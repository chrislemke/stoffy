# Memory: /debate Command

> **CRITICAL**: This memory file captures human feedback about the `/debate` command. Apply these learnings with **higher weight** when orchestrating debates.

---

## Feedback Entry #1

**Date**: 2025-12-31
**Source Debate**: `debates/2025-12-30_predictive_brain_karl_friston_vs_laozi.md`
**Type**: `architectural_limitation`
**Confidence**: `high`

### Human Feedback

> "This debate is pretty bad. Whenever Friston says something Laozi seems to answer totally out of context. Here we can learn that the debate command is still not capable of providing the two agents a good platform for a two-agent-debate where both agents react to each other."

### Analysis

The current `/debate` command prompts fail to ensure genuine dialectical engagement between agents. The Friston-Laozi debate exhibited:

1. **Parallel monologues**: Each agent presents their views without directly addressing the other's specific claims
2. **Weak cross-references**: Responses acknowledge opponent's "ideas" in general but don't quote or paraphrase specific arguments
3. **Persona drift**: Thinker-persona agents (Laozi) default to their characteristic philosophical style rather than engaging with technical arguments (Friston's FEP)

### Root Causes

| Cause | Location | Impact |
|-------|----------|--------|
| No quotation requirement | Steps 3.2, 4.1, 4.2 | Agents don't reference specific claims |
| Generic "acknowledge" instruction | Dialectical prompts | Vague "what did they get right" vs specific engagement |
| Persona override | Thinker agents | Style trumps substance |
| Context dilution | Full debate history | Agents may not focus on latest argument |

### Recommended Improvements (Not Yet Implemented)

For future debate orchestrations, consider:

1. **Mandatory quotation**: Require agents to quote or paraphrase ONE specific claim before responding
2. **Engagement structure**: Change "Acknowledge" to "ENGAGE" - directly address a specific claim first
3. **Key claims extraction**: Before each response, extract 1-2 key claims from opponent for focused engagement
4. **Persona guidance**: Add explicit instruction that even thinker-personas must directly engage arguments, not just teach
5. **Engagement verification**: Check responses for explicit cross-references; warn if weak

### Workaround (Current)

When orchestrating debates manually or reviewing transcripts:
- Look for explicit "you said X" / "you argued that Y" structures
- If absent, the debate likely has the engagement problem
- Consider smaller rounds with focused topics
- Use philosophical-analyst or devils-advocate (argument-focused) over thinker-personas for better engagement

---

## Summary

| Key | Value |
|-----|-------|
| Problem | Agents talk past each other instead of engaging |
| Severity | High - defeats purpose of dialectic |
| Status | Identified, not yet fixed in code |
| Workaround | Use argument-focused agents, manual intervention |

---

*Memory created by `/learn` command on 2025-12-31*
