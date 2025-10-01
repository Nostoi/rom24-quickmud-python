# Autonomous Coding Scripts for ROM 2.4 Python Port

This directory contains scripts for autonomous coding using OpenAI Codex CLI with your agent system.

## Prerequisites

Install OpenAI Codex CLI:

```bash
# Option 1: npm
npm install -g @openai/codex

# Option 2: Homebrew (macOS)
brew install codex

# Option 3: Direct download from GitHub releases
# https://github.com/openai/codex/releases
```

First-time setup:

```bash
codex  # Follow authentication prompts
```

## Scripts

### 1. `autonomous_coding.sh` - Full Autonomous Workflow

The main script that runs both AGENT.md (analysis) and AGENT.EXECUTOR.md (execution) in a loop.

```bash
# Basic usage
./scripts/autonomous_coding.sh

# Full automation (no approval prompts)
./scripts/autonomous_coding.sh --full-auto

# Audit only (generate tasks but don't execute)
./scripts/autonomous_coding.sh --mode audit-only

# Execute only (run existing tasks)
./scripts/autonomous_coding.sh --mode execute-only

# Custom settings
./scripts/autonomous_coding.sh --max-iterations 5 --approval-mode on-request
```

**What it does:**

1. Identifies subsystems with confidence < 0.80
2. Runs architectural analysis (AGENT.md) to generate new tasks
3. Executes tasks (AGENT.EXECUTOR.md) with proper validation
4. Runs tests and validation (ruff, mypy, pytest)
5. Commits successful changes
6. Iterates until work is complete or max iterations reached

### 2. `quick_audit.sh` - Fast Analysis

Quick script for immediate analysis of the worst subsystem.

```bash
./scripts/quick_audit.sh
```

**What it does:**

1. Shows current low-confidence subsystems
2. Focuses Codex on the most critical issues
3. Generates 1-2 P0 tasks for immediate attention

## Configuration

The scripts use `.codex/config.toml` for Codex CLI configuration:

```toml
# Key settings
model = "gpt-5-codex"          # Coding-optimized model
approval_policy = "on-request"  # Let AI decide when to ask
sandbox_mode = "workspace-write" # Safe file editing
hide_agent_reasoning = false   # Show/hide AI thinking
```

## Usage Examples

### Start autonomous coding session:

```bash
cd /path/to/rom24-quickmud-python
./scripts/autonomous_coding.sh
```

### Focus on specific subsystem (manual):

```bash
codex "Following AGENT.md, audit the 'resets' subsystem (confidence 0.38, correctness:fails). Generate specific P0 tasks to fix the most critical ROM parity gaps."
```

### Execute existing tasks:

```bash
codex "Following AGENT.EXECUTOR.md, execute the highest priority P0 tasks from PYTHON_PORT_PLAN.md. Focus on small, reviewable changes."
```

## Safety Features

- **Sandboxed execution**: Changes limited to project directory
- **Git integration**: Checks for clean working directory
- **Validation**: Runs ruff, mypy, pytest before committing
- **Approval modes**: From full-auto to requiring approval for each action
- **Logging**: Detailed logs in `log/autonomous_coding_*.log`

## Troubleshooting

**Codex not found:**

```bash
npm install -g @openai/codex
# or
brew install codex
```

**Authentication issues:**

```bash
codex  # Re-run authentication
```

**Permission errors:**

```bash
chmod +x scripts/*.sh
```

**Git working directory not clean:**

```bash
git add . && git commit -m "save work"
# or
git stash
```

## Integration with VS Code

You can also run these workflows directly in VS Code:

1. Open terminal in VS Code
2. Run the scripts from the integrated terminal
3. Use Codex CLI directly: `codex "follow AGENT.md workflow"`

## Advanced Usage

### Custom Codex Commands

Run specific agent workflows directly:

```bash
# Analysis phase
codex exec "Following AGENT.md, analyze all subsystems with confidence < 0.80 and generate architectural tasks"

# Execution phase
codex exec "Following AGENT.EXECUTOR.md, implement up to 4 P0/P1 tasks from PYTHON_PORT_PLAN.md"

# Focused work
codex exec "Fix the 'resets' subsystem correctness:fails issue by implementing proper LastObj/LastMob state tracking"
```

### Batch Processing

Process multiple subsystems:

```bash
for subsystem in resets movement_encumbrance help_system; do
  codex exec "Following AGENT.md, audit $subsystem subsystem and generate 2 P0 tasks"
done
```

## Monitoring Progress

Check progress after runs:

```bash
# Show confidence scores
grep -A1 "confidence" PYTHON_PORT_PLAN.md

# Show open tasks
grep "^- \[P[012]\]" PYTHON_PORT_PLAN.md

# Show completed tasks
grep "^- ✅" PYTHON_PORT_PLAN.md

# View latest log
tail -f log/autonomous_coding_*.log
```
