---
description: Analyze a TODO list and generate an execution manual
subagent: todo-analyzer-executor
subtask: true
---

# TODO Executor

## Input

**TODO File Path**: `$ARGUMENTS`

## Instructions

1. **Verify Input**
   - Check that the TODO file exists at the provided path
   - If missing, report error and exit

2. **Read TODO File**
   - Load the complete contents of the TODO file

3. **Discover Project Context**
   - Identify the project root (parent directory of the TODO file)
   - List all markdown files in the project
   - Note the project structure and organization

4. **Analyze and Generate Manual**

   Analyze the TODO list within the project context:
   - Parse all tasks (completed and pending)
   - Understand what each task requires
   - Identify which files each task affects
   - Determine dependencies and optimal order
   - Estimate effort for each task

5. **Save Output**

   Save the execution manual to: `[PROJECT_ROOT]/execution-manual.md`

6. **Report Summary**

   Display:
   ```
   ╔══════════════════════════════════════╗
   ║     TODO ANALYSIS COMPLETE           ║
   ╠══════════════════════════════════════╣
   ║ Total Tasks:          X              ║
   ║ Completed:            Y              ║
   ║ Remaining:            Z              ║
   ╚══════════════════════════════════════╝

   Manual saved to: [path]

   Recommended starting point: [first task and why]
   ```
