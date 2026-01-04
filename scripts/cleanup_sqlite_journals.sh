#!/usr/bin/env bash
# Cleanup all SQLite journal files (*.db-journal) in the repository.
# This script is safe to run repeatedly; it will delete only files matching the pattern.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
echo "Cleaning SQLite journal files in $REPO_ROOT..."
find "$REPO_ROOT" -type f -name "*.db-journal" -print -delete || true

echo "Cleanup complete."
