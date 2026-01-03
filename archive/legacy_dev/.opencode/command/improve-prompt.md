---
description: Improve a prompt using Claude's official best practices for LLMs
subtask: true
agent: prompt-improver
---

# Improve Prompt

Analyze and improve a prompt using expert prompt engineering techniques based on Anthropic's official best practices for Claude models.

**Usage:**
```
/improve-prompt <your prompt here>
```

The prompt can be any length and include spaces, newlines, quotes, and special characters.

**Examples:**
```
/improve-prompt Create an analytics dashboard
/improve-prompt Summarize this document and highlight the key points
/improve-prompt You are a helpful assistant that answers questions about Python code
/improve-prompt Write a function that sorts a list of numbers
```

---

## Prompt to Improve

```
$ARGUMENTS
```

---

## Instructions

The user wants to improve the prompt shown above. Follow your process:

1. **Ask clarifying questions** about:
   - Target model (Claude, GPT, Gemini, general-purpose?)
   - Use case (what the prompt is trying to achieve)
   - Current problems (what's not working well?)
   - Constraints (length, tone, format requirements?)

2. **Wait for the user's answers** before proceeding with improvements

3. **Analyze** the original prompt for weaknesses using your expertise

4. **Apply** relevant techniques from your prompt engineering best practices

5. **Output** the improved prompt in markdown format with:
   - The improved prompt in a code block (ready to copy)
   - A table of changes made
   - Brief rationale explaining why the changes will help

Your goal is to help users write more effective prompts that consistently get better results from LLMs.
