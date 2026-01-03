#!/bin/bash
# open_assistant Environment Activation Script
# Usage: source scripts/activate.sh
#
# This script:
#   1. Changes to the repository directory
#   2. Activates the open_assistant conda environment
#
# Tip: Use 'make activate' to add shell aliases for quick access

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_NAME="open_assistant"

# Check if being sourced (not executed)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script must be sourced, not executed."
    echo "Usage: source $0"
    exit 1
fi

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: conda not found. Run 'make setup' first."
    return 1
fi

# Change to repo directory
cd "$REPO_ROOT"

# Activate the environment
conda activate "$ENV_NAME"

echo "Activated '$ENV_NAME' in $REPO_ROOT"
