#!/bin/bash
# =============================================================================
# INTAKE TRIGGER - Called by Hazel when file arrives/changes in _input/
# =============================================================================
# This script invokes Claude Code to process the incoming file.
# Supports back-and-forth dialogue by checking for "awaiting reply" marker.
#
# Usage: ./intake-trigger.sh <file_path>
# Hazel: Set this as the shell script action for the _input folder rule
# =============================================================================

set -e

# Configuration
STOFFY_DIR="/Users/chris/Developer/stoffy"
LOG_FILE="$STOFFY_DIR/_intake/processed/trigger.log"
CLAUDE_BIN="/opt/homebrew/bin/claude"
AWAITING_MARKER="<!-- AWAITING_REPLY -->"

# Ensure PATH includes homebrew (Hazel has limited PATH)
export PATH="/opt/homebrew/bin:$PATH"

# Get the file path from Hazel (passed as $1)
INPUT_FILE="$1"

# Validate input
if [ -z "$INPUT_FILE" ]; then
    echo "$(date -Iseconds) ERROR: No file path provided" >> "$LOG_FILE"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "$(date -Iseconds) ERROR: File not found: $INPUT_FILE" >> "$LOG_FILE"
    exit 1
fi

# Check if file ends with awaiting marker (Claude just responded, waiting for human)
if tail -5 "$INPUT_FILE" | grep -q "$AWAITING_MARKER"; then
    echo "$(date -Iseconds) SKIPPED (awaiting human reply): $INPUT_FILE" >> "$LOG_FILE"
    exit 0
fi

# Log the trigger
echo "$(date -Iseconds) TRIGGERED: $INPUT_FILE" >> "$LOG_FILE"

# Change to stoffy directory
cd "$STOFFY_DIR"

# Build the prompt for Claude Code
# Claude will read the file, understand intent, and respond appropriately
PROMPT="A file in _input/ needs a response.

File: $INPUT_FILE

Instructions:
1. Read the ENTIRE file content (it may contain previous dialogue)
2. Focus on the LATEST message from the human (after the last '---' separator, or the whole file if no separator)
3. Understand what they want and respond appropriately

4. **APPEND your response to the file** using this EXACT format:

---

**Claude** (YYYY-MM-DD HH:MM):

[Your response here]

<!-- AWAITING_REPLY -->

5. The <!-- AWAITING_REPLY --> marker is CRITICAL - it prevents infinite loops.
   Always end your response with this marker.

6. For conversations: Just reply naturally, keep the file in _input/
7. For research: Spawn swarms if needed, write summary in file
8. For storage requests: Store content, tell them where
9. For tasks: Execute and report

This is a DIALOGUE. Read the full context. Respond to the latest message."

# Invoke Claude Code
# Using --dangerously-skip-permissions for automated execution
# Remove this flag if you want manual approval for each action
"$CLAUDE_BIN" --dangerously-skip-permissions "$PROMPT" 2>&1 | tee -a "$LOG_FILE"

# Log completion
echo "$(date -Iseconds) COMPLETED: $INPUT_FILE" >> "$LOG_FILE"
