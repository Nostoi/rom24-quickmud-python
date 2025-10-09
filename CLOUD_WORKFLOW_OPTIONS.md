# Cloud-Based Workflow Options (No Shell Scripts!)

**Problem**: Shell scripts like `run_agent_loop.sh` don't work in cloud-based GitHub Copilot.

**Solution**: Use **GitHub Copilot's built-in features** that work natively in the browser!

---

## 🎯 **Best Options for Cloud Codex**

### **Option 1: GitHub Copilot Edits (RECOMMENDED)** ⭐

**GitHub Copilot Edits** is a built-in feature that works across multiple files in one session - perfect for iterating on your agents!

#### **How to Use It**:

1. **Open Copilot Edits** in VS Code:

   - Press `Cmd+Shift+I` (Mac) or `Ctrl+Shift+I` (Windows)
   - Or click the "Copilot Edits" icon in the sidebar
   - Or use Command Palette: `Cmd+Shift+P` → "GitHub Copilot: Open Edits"

2. **Start an Edit Session**:

   ```
   Read AGENT.md and execute all the tasks it generates.
   Then read AGENT.EXECUTOR.md and implement those tasks.
   ```

3. **Review & Accept Changes**:

   - Copilot will make changes across multiple files
   - Review each change in the diff view
   - Accept or reject individually or all at once

4. **Iterate**:

   - After accepting, give it a new prompt:

   ```
   Now read AGENT.md again and execute the next set of tasks.
   Then read AGENT.EXECUTOR.md and implement those tasks.
   ```

5. **Repeat** until project is complete!

#### **Pros**:

- ✅ Works in cloud Codex (no shell scripts!)
- ✅ Multi-file editing in one session
- ✅ Shows all changes before applying
- ✅ Can iterate multiple cycles
- ✅ Built-in to GitHub Copilot

#### **Cons**:

- ⚠️ Need to manually trigger each cycle
- ⚠️ More manual than automated scripts

---

### **Option 2: GitHub Copilot Agent Mode** 🤖

**Agent mode** is even more powerful - it can run terminal commands, create tests, and iterate autonomously!

#### **How to Use It**:

1. **Open Agent Mode**:

   - In VS Code, open Copilot Chat
   - Select **"Agent"** from the dropdown at the top
   - Or use Command Palette: `Cmd+Shift+P` → "GitHub Copilot: Start Agent Mode"

2. **Give it a Comprehensive Task**:

   ```
   I have two agent files: AGENT.md (analyzes code and generates tasks)
   and AGENT.EXECUTOR.md (executes those tasks).

   I want you to:
   1. Read and execute AGENT.md to analyze the project and generate tasks
   2. Then read and execute AGENT.EXECUTOR.md to implement those tasks
   3. Run tests to validate the changes
   4. Repeat this cycle until the project reaches 80% completion

   The project is a ROM 2.4 MUD port to Python. Current status is in
   PYTHON_PORT_PLAN.md. Work on incomplete subsystems (confidence < 0.80).
   ```

3. **Agent Will**:

   - Read your files
   - Execute commands
   - Make multi-file changes
   - Run tests
   - **Ask for approval** at key stages

4. **Review & Approve**:
   - Agent will pause and ask for your approval
   - Review changes before approving
   - Agent continues after approval

#### **Pros**:

- ✅ Most powerful option
- ✅ Can run terminal commands
- ✅ Can execute tests automatically
- ✅ Multi-step planning and execution
- ✅ Works in cloud Codex

#### **Cons**:

- ⚠️ Requires approval at each stage (safety feature)
- ⚠️ May need guidance if it gets stuck

---

### **Option 3: Copilot Chat with @workspace** 💬

For simpler, more controlled iterations:

#### **How to Use It**:

1. **Open Copilot Chat**: `Cmd+Shift+I` or click chat icon

2. **Use @workspace for Context**:

   ```
   @workspace Read AGENT.md and tell me what tasks it generates for
   the lowest confidence subsystem in PYTHON_PORT_PLAN.md
   ```

3. **Then Execute**:

   ```
   @workspace Now implement those tasks according to AGENT.EXECUTOR.md
   ```

4. **Iterate**:
   ```
   @workspace Check PYTHON_PORT_PLAN.md again and find the next
   incomplete subsystem. Generate and implement tasks for it.
   ```

#### **Pros**:

- ✅ Simple and straightforward
- ✅ Full control over each step
- ✅ Works in cloud Codex
- ✅ Good for learning how agents work

#### **Cons**:

- ⚠️ Most manual option
- ⚠️ Need to prompt for each action

---

## 🚀 **Recommended Workflow for Your Situation**

Since you're using **cloud-based Codex** and manually switching is slow, here's the best approach:

### **Phase 1: Use Copilot Edits for Rapid Iteration**

```markdown
1. Open Copilot Edits (Cmd+Shift+I)

2. Prompt:
   "Read AGENT.md and execute all analysis tasks to identify
   incomplete subsystems in PYTHON_PORT_PLAN.md. Then read
   AGENT.EXECUTOR.md and implement the highest priority tasks
   for the worst subsystem."

3. Review and accept changes

4. Repeat with new prompt:
   "Continue with the next incomplete subsystem"

5. Iterate 5-10 times until significant progress
```

### **Phase 2: Use Agent Mode for Complex Multi-Step Work**

```markdown
When you hit a complex subsystem (like combat or skills_spells):

1. Switch to Agent Mode

2. Prompt:
   "I need you to fully implement the 'combat' subsystem according
   to AGENT.md and AGENT.EXECUTOR.md. This requires:

   - Analyzing ROM 2.4 C sources
   - Implementing Python equivalents
   - Creating tests
   - Validating against golden data

   Work autonomously but ask for approval before major changes."

3. Agent will work through multiple steps with approvals

4. Review and approve at checkpoints
```

---

## 📋 **Specific Prompts to Use**

### **For Initial Audit**:

```
@workspace Read AGENT.md and execute a discovery audit on all
subsystems in PYTHON_PORT_PLAN.md. Identify the 5 subsystems
with lowest confidence scores and generate specific tasks for each.
```

### **For Implementation**:

```
Using the tasks from AGENT.md, read AGENT.EXECUTOR.md and
implement all P0 tasks for the combat subsystem. Make sure to:
- Update PYTHON_PORT_PLAN.md with progress
- Add tests for new functionality
- Follow port.instructions.md rules
```

### **For Iteration**:

```
Check the updated PYTHON_PORT_PLAN.md and identify the next
incomplete subsystem (confidence < 0.80). Generate and implement
tasks for it following the same pattern.
```

### **For Validation**:

```
Run pytest and analyze test results for the subsystems we just
worked on. Update confidence scores in PYTHON_PORT_PLAN.md based
on test coverage and pass rates.
```

---

## ⚡ **Quick Start Guide**

### **Right Now (5 minutes)**:

1. **Open Copilot Edits**: `Cmd+Shift+I`

2. **Paste this prompt**:

   ```
   Read AGENT.md and analyze PYTHON_PORT_PLAN.md to find the
   subsystem with the lowest confidence score. Generate detailed
   tasks for improving it. Then read AGENT.EXECUTOR.md and
   implement those tasks across the necessary files.
   ```

3. **Review changes** - Copilot will show diffs

4. **Accept changes** - Click "Accept All" or review individually

5. **Repeat** - Give it the prompt again for the next subsystem

### **Time Savings**:

- Manual switching: 30-40 minutes for 10 cycles
- Copilot Edits: **5-10 minutes** for same work ⚡
- Agent Mode: **3-5 minutes** (more autonomous) 🚀

---

## 🎨 **Advanced Techniques**

### **Batch Multiple Cycles**:

```
Read AGENT.md and AGENT.EXECUTOR.md. Then execute 5 complete
cycles of:
1. Analyze incomplete subsystems
2. Generate tasks
3. Implement tasks
4. Update plan

Work on subsystems in order of priority (lowest confidence first).
Ask for approval after every 2 cycles.
```

### **Focused Deep Work**:

```
Focus exclusively on the 'combat' subsystem for the next hour.
1. Read all ROM 2.4 C sources for combat (src/fight.c, src/handler.c)
2. Analyze current Python implementation in mud/combat/
3. Identify all gaps according to AGENT.md
4. Implement missing features per AGENT.EXECUTOR.md
5. Create comprehensive tests
6. Update PYTHON_PORT_PLAN.md with new confidence score
```

### **Test-Driven Iteration**:

```
For each subsystem with confidence < 0.80:
1. Read the C source code references in PYTHON_PORT_PLAN.md
2. Create golden test cases from ROM behavior
3. Implement Python code until tests pass
4. Update confidence scores
Continue until all subsystems reach 0.80+
```

---

## 🛡️ **Safety & Best Practices**

1. **Always review changes** before accepting in Edits mode
2. **Use Agent Mode** for complex multi-step work (it asks for approval)
3. **Save frequently** - Edits can be undone with `Cmd+Z`
4. **Use git branches** for safety:
   ```
   @terminal git checkout -b agent-work
   ```
5. **Validate after each cycle**:
   ```
   @terminal pytest -q
   @terminal ruff check .
   ```

---

## 📊 **Monitoring Progress**

### **After Each Cycle, Ask**:

```
@workspace How many subsystems in PYTHON_PORT_PLAN.md have
confidence >= 0.80 now? Show me the current completion percentage.
```

### **Check Test Results**:

```
@terminal pytest --collect-only -q | tail -1
@terminal python3 scripts/test_data_gatherer.py --all | grep confidence
```

### **Review Commits**:

```
@terminal git log --oneline -10
```

---

## 🎯 **Your Next Steps**

**Immediate (Right Now)**:

1. Open Copilot Edits: `Cmd+Shift+I`
2. Paste the "Quick Start" prompt above
3. Review and accept changes
4. Repeat 5 times

**Short-term (This Session)**:

1. Use Edits for 5-10 subsystem improvements
2. Switch to Agent Mode for complex subsystems
3. Validate with tests
4. Commit progress

**Long-term (This Week)**:

1. Get project to 50% completion (6 more subsystems)
2. Focus Agent Mode on combat and skills_spells
3. Reach 60-70% completion
4. Beta-quality MUD

---

## 🔗 **References**

- [GitHub Copilot Edits Documentation](https://docs.github.com/en/copilot/using-github-copilot/copilot-edits)
- [GitHub Copilot Agent Mode Guide](https://github.blog/ai-and-ml/github-copilot/mastering-github-copilot-when-to-use-ai-agent-mode/)
- [Multi-file Editing with Copilot](https://devblogs.microsoft.com/visualstudio/iterate-across-multiple-files-more-efficiently-with-github-copilot-edits-preview/)

---

## 💡 **Bottom Line**

**You don't need shell scripts!**

GitHub Copilot Edits and Agent Mode are **built-in features** that work in cloud Codex and are actually **better** than shell scripts because:

✅ Multi-file editing in one session  
✅ Visual diff review before accepting  
✅ Can run tests and terminal commands  
✅ More powerful AI capabilities  
✅ No installation or setup needed

**Just open Copilot Edits (`Cmd+Shift+I`) and start working!** 🚀
