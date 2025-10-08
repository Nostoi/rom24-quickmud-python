#!/bin/bash
for i in {1..10}; do
  echo "🔄 Cycle $i"
  codex execute "AGENT.md" --approve-all || break
  codex execute "AGENT.EXECUTOR.md" --approve-all || break
done
