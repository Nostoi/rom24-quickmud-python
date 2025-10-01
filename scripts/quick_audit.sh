#!/bin/bash
# quick_audit.sh - Quick audit script for immediate analysis
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔍 Quick ROM Parity Audit"
echo "========================="

# Check for Codex CLI
if ! command -v codex &> /dev/null; then
    echo "❌ Codex CLI not found. Install with:"
    echo "   npm install -g @openai/codex"
    echo "   # or"
    echo "   brew install codex"
    exit 1
fi

# Show current low-confidence subsystems
echo "📊 Low-confidence subsystems (< 0.80):"
grep -A1 "###.*— Parity Audit" PYTHON_PORT_PLAN.md | \
    grep -E "(###|confidence)" | \
    paste - - | \
    awk -F'confidence' '{if ($2) print $1 $2}' | \
    awk '{
        gsub(/^###[[:space:]]*/, "");
        gsub(/[[:space:]]*—.*confidence[[:space:]]*/, " (");
        gsub(/\).*$/, ")");
        if ($0 ~ /\(0\.[0-7][0-9]*\)/) print "  ❌ " $0;
    }'

echo
echo "🤖 Running quick audit with Codex..."
echo "Press Ctrl+C to cancel"

# Run focused audit on the worst subsystem
codex exec "Following AGENT.md, identify the subsystem with the lowest confidence score in PYTHON_PORT_PLAN.md and generate 1-2 specific P0 tasks to address its most critical architectural gaps. Focus on ROM parity issues that would improve correctness."