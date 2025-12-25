# Fast Development Workflow Options

**Problem**: Manually switching between "execute AGENT.md" and "execute AGENT.EXECUTOR.md" in browser Codex is slow.

**Solutions**: 3 options, from fastest to most controlled.

---

## 🚀 **Option 1: Fully Automated Loop (FASTEST)**

Use the existing `scripts/autonomous_coding.sh` to run everything automatically:

```bash
cd /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python

# Run autonomous loop (will iterate until done or max iterations)
./scripts/autonomous_coding.sh
```

### **What It Does**:

1. Validates test infrastructure
2. Analyzes confidence scores (AGENT.md)
3. Identifies incomplete subsystems
4. Generates tasks automatically
5. Executes tasks (AGENT.EXECUTOR.md)
6. Validates with tests
7. Commits changes
8. **Repeats** until done or max iterations

### **Configuration**:

Edit `agent/constants.yaml` to control behavior:

```yaml
MAX_TASKS_PER_RUN: 4
MAX_FILES_TOUCHED: 12
MAX_ITERATIONS: 10 # How many AGENT.md → AGENT.EXECUTOR.md cycles
```

### **Pros**:

- ✅ Completely hands-off
- ✅ Runs continuously
- ✅ Auto-commits with good messages
- ✅ Logs everything

### **Cons**:

- ⚠️ Less control over what gets changed
- ⚠️ Need to review commits afterward
- ⚠️ Requires Codex CLI installed (`npm install -g @openai/codex`)

---

## ⚡ **Option 2: Quick Audit Script (BALANCED)**

Run quick focused audits on specific subsystems:

```bash
cd /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python

# Audit the worst subsystem
./scripts/quick_audit.sh
```

### **What It Does**:

1. Shows low-confidence subsystems
2. Focuses on the worst one
3. Runs targeted Codex audit
4. Generates specific tasks
5. **Stops** (you decide whether to execute)

### **Pros**:

- ✅ Faster than manual
- ✅ More control (review before execute)
- ✅ Focused on highest priority

### **Cons**:

- ⚠️ Still need to manually run executor
- ⚠️ One subsystem at a time

---

## 🎯 **Option 3: Combined Command (RECOMMENDED)**

Create a simple wrapper that runs both agents in sequence:

```bash
# Create quick wrapper script
cat > run_agent_cycle.sh << 'EOF'
#!/bin/bash
set -e

echo "🔍 Phase 1: Running AGENT.md (analysis)..."
codex execute "AGENT.md" --approve-all

echo ""
echo "🔧 Phase 2: Running AGENT.EXECUTOR.md (implementation)..."
codex execute "AGENT.EXECUTOR.md" --approve-all

echo ""
echo "✅ Cycle complete!"
EOF

chmod +x run_agent_cycle.sh

# Run it
./run_agent_cycle.sh
```

### **What It Does**:

1. Runs AGENT.md (generates tasks)
2. Immediately runs AGENT.EXECUTOR.md (executes tasks)
3. One command = one full cycle

### **Pros**:

- ✅ Simple, predictable
- ✅ One cycle per command
- ✅ Easy to review between cycles
- ✅ No complex setup

### **Cons**:

- ⚠️ Still need to run multiple times
- ⚠️ Manual iteration

---

## 🔄 **Option 4: Loop Version of Combined Command**

Make it iterate automatically:

```bash
cat > run_agent_loop.sh << 'EOF'
#!/bin/bash
set -e

MAX_CYCLES=${1:-5}  # Default 5 cycles, or pass as argument

for i in $(seq 1 $MAX_CYCLES); do
    echo ""
    echo "=========================================="
    echo "🔄 CYCLE $i of $MAX_CYCLES"
    echo "=========================================="

    echo "🔍 Running AGENT.md..."
    codex execute "AGENT.md" --approve-all || break

    echo ""
    echo "🔧 Running AGENT.EXECUTOR.md..."
    codex execute "AGENT.EXECUTOR.md" --approve-all || break

    echo ""
    echo "✅ Cycle $i complete!"

    # Check if done
    if git diff --quiet; then
        echo "✅ No changes - likely complete!"
        break
    fi

    # Brief pause
    sleep 2
done

echo ""
echo "=========================================="
echo "🎉 Completed $i cycles"
echo "=========================================="
EOF

chmod +x run_agent_loop.sh

# Run 5 cycles
./run_agent_loop.sh 5

# Or run 10 cycles
./run_agent_loop.sh 10
```

### **Pros**:

- ✅ Runs multiple cycles automatically
- ✅ Stops if no changes (done)
- ✅ Simple and transparent
- ✅ Easy to stop (Ctrl+C)

### **Cons**:

- ⚠️ Uses `--approve-all` (less oversight)

---

## 🎨 **Option 5: VS Code Tasks (BEST FOR LOCAL)**

If you're using VS Code locally (not just browser Codex), add this to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run AGENT.md",
      "type": "shell",
      "command": "codex execute 'AGENT.md'",
      "group": "build"
    },
    {
      "label": "Run AGENT.EXECUTOR.md",
      "type": "shell",
      "command": "codex execute 'AGENT.EXECUTOR.md'",
      "group": "build"
    },
    {
      "label": "Run Agent Cycle",
      "type": "shell",
      "command": "./scripts/autonomous_coding.sh",
      "group": "build",
      "problemMatcher": []
    }
  ]
}
```

Then use:

- `Cmd+Shift+P` → "Tasks: Run Task" → "Run Agent Cycle"

---

## 📊 **My Recommendations Based on Your Situation**

### **For Maximum Speed** (Browser Codex):

**Use Option 4 (Loop Script)** — Run locally in terminal:

```bash
# One-time setup
cat > run_agent_loop.sh << 'EOF'
#!/bin/bash
set -e
MAX_CYCLES=${1:-5}
for i in $(seq 1 $MAX_CYCLES); do
    echo "🔄 CYCLE $i/$MAX_CYCLES"
    codex execute "AGENT.md" --approve-all || break
    codex execute "AGENT.EXECUTOR.md" --approve-all || break
    git diff --quiet && break
done
EOF
chmod +x run_agent_loop.sh

# Then just run:
./run_agent_loop.sh 10  # Do 10 cycles
```

### **For Safety** (Review changes):

**Use Option 3 (Combined Command)** without `--approve-all`:

```bash
cat > run_agent_cycle.sh << 'EOF'
#!/bin/bash
codex execute "AGENT.md"
codex execute "AGENT.EXECUTOR.md"
EOF
chmod +x run_agent_cycle.sh

./run_agent_cycle.sh  # Run once, review, repeat
```

### **For Fully Hands-Off**:

**Use Option 1 (autonomous_coding.sh)**:

```bash
./scripts/autonomous_coding.sh
# Walk away, check back in 30 minutes
```

---

## ⚡ **Quick Start (Choose One)**

### **Fastest (Hands-off)**:

```bash
cd /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python
./scripts/autonomous_coding.sh
```

### **Balanced (Review each cycle)**:

```bash
# Create simple wrapper
echo '#!/bin/bash
codex execute "AGENT.md"
codex execute "AGENT.EXECUTOR.md"' > cycle.sh
chmod +x cycle.sh

# Run repeatedly
./cycle.sh
./cycle.sh
./cycle.sh
```

### **Automated Loop (10 cycles)**:

```bash
# Create loop
echo '#!/bin/bash
for i in {1..10}; do
  echo "Cycle $i"
  codex execute "AGENT.md" --approve-all
  codex execute "AGENT.EXECUTOR.md" --approve-all
  git diff --quiet && break
done' > loop.sh
chmod +x loop.sh

./loop.sh
```

---

## 🔍 **Monitor Progress**

While any script runs, monitor in another terminal:

```bash
# Watch commits
watch -n 5 'git log --oneline -10'

# Watch test results
watch -n 10 'pytest --collect-only -q | tail -1'

# Watch subsystem progress
watch -n 30 'python3 scripts/test_data_gatherer.py --all 2>&1 | grep confidence'
```

---

## 🛡️ **Safety Tips**

1. **Use a branch**:

   ```bash
   git checkout -b agent-automation
   ```

2. **Set commit limits** in `agent/constants.yaml`:

   ```yaml
   MAX_TASKS_PER_RUN: 2 # Start small
   MAX_FILES_TOUCHED: 5 # Limit blast radius
   ```

3. **Review periodically**:

   ```bash
   # Every few cycles
   git log --oneline -10
   git diff HEAD~5  # Review last 5 commits
   ```

4. **Easy rollback**:

   ```bash
   # Undo last commit
   git reset --hard HEAD~1

   # Undo last 5 commits
   git reset --hard HEAD~5
   ```

---

## 🎯 **Bottom Line**

**For your situation (browser Codex, manual switching)**:

**Best option**: Create `run_agent_loop.sh` and run it locally in terminal:

```bash
# One-time setup (30 seconds)
cat > run_agent_loop.sh << 'EOF'
#!/bin/bash
for i in {1..10}; do
  echo "🔄 Cycle $i"
  codex execute "AGENT.md" --approve-all || break
  codex execute "AGENT.EXECUTOR.md" --approve-all || break
done
EOF
chmod +x run_agent_loop.sh

# Then whenever you want to make progress:
./run_agent_loop.sh  # Runs 10 cycles automatically
```

This is **10x faster** than manual switching and still safe because:

- Stops on errors
- Each cycle is logged
- Easy to review commits
- Can Ctrl+C to stop anytime

**Time savings**: 10 manual cycles ≈ 30-40 minutes → Automated ≈ 3-5 minutes ⚡
