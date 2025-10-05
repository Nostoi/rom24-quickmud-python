#!/bin/bash
# autonomous_coding.sh - Autonomous coding script using OpenAI Codex CLI with agent files
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLAN_FILE="$PROJECT_ROOT/PYTHON_PORT_PLAN.md"
AGENT_AUDIT="$PROJECT_ROOT/AGENT.md"
AGENT_EXECUTOR="$PROJECT_ROOT/AGENT.EXECUTOR.md"
CONSTANTS_FILE="$PROJECT_ROOT/agent/constants.yaml"

# Logging
LOG_DIR="$PROJECT_ROOT/log"
LOG_FILE="$LOG_DIR/autonomous_coding_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_step() {
    log "${BLUE}[$(date '+%H:%M:%S')] $1${NC}"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

# Check test infrastructure
check_test_infrastructure() {
    log_step "Validating test infrastructure..."
    
    # Check if pytest is available
    if ! command -v pytest &> /dev/null; then
        log_error "pytest not found - test infrastructure not installed"
        exit 1
    fi
    
    # Check if tests can collect
    if ! pytest --collect-only -q > /dev/null 2>&1; then
        log_error "Test collection failed! Infrastructure is broken."
        log_warning "Confidence scores cannot be validated without functional tests."
        log ""
        log "Run this to see details:"
        log "  pytest --collect-only -q"
        log ""
        log "Fix test infrastructure before running agents."
        exit 1
    fi
    
    log_success "Test infrastructure is functional"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Check if Codex CLI is installed
    if ! command -v codex &> /dev/null; then
        log_error "Codex CLI not found. Install it with:"
        log "  npm install -g @openai/codex"
        log "  # or"
        log "  brew install codex"
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
    
    # Check if working directory is clean
    if ! git diff-index --quiet HEAD --; then
        log_warning "Working directory has uncommitted changes"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Parse confidence scores from PYTHON_PORT_PLAN.md
get_low_confidence_subsystems() {
    log_step "Analyzing subsystem confidence scores..."
    
    # PHASE 0: Validate test infrastructure first
    check_test_infrastructure
    
    # Extract subsystems with confidence < 0.80 from STATUS lines
    local low_confidence_systems=()
    
    while IFS= read -r line; do
        if [[ $line =~ STATUS:.*confidence[[:space:]]+([0-9]+\.[0-9]+) ]]; then
            local confidence="${BASH_REMATCH[1]}"
            if (( $(echo "$confidence < 0.80" | bc -l) )); then
                # Find the subsystem name from the previous line
                local subsystem_line=$(grep -B1 "STATUS:" "$PLAN_FILE" | grep "###" | tail -1)
                if [[ $subsystem_line =~ ###[[:space:]]+([a-zA-Z_]+) ]]; then
                    local subsystem="${BASH_REMATCH[1]}"
                    low_confidence_systems+=("$subsystem:$confidence")
                fi
            fi
        fi
    done < "$PLAN_FILE"
    
    printf '%s\n' "${low_confidence_systems[@]}"
}

# Run architectural analysis (AGENT.md)
run_architectural_analysis() {
    log_step "Running architectural analysis (AGENT.md)..."
    
    local low_confidence_systems=($(get_low_confidence_subsystems))
    
    if [ ${#low_confidence_systems[@]} -eq 0 ]; then
        log_success "No subsystems found with confidence < 0.80"
        return 0
    fi
    
    log "Found ${#low_confidence_systems[@]} subsystems needing analysis:"
    for system in "${low_confidence_systems[@]}"; do
        IFS=':' read -r name confidence <<< "$system"
        log "  - $name (confidence: $confidence)"
    done
    
    # Create analysis prompt
    local analysis_prompt="Following the AGENT.md workflow, perform architectural analysis on the ROM 2.4 Python port.

Target subsystems with confidence < 0.80:
$(printf '%s\n' "${low_confidence_systems[@]}" | sed 's/^/- /')

Analyze confidence_tracker.py results, investigate architectural gaps, and generate ROM parity tasks with C/Python/DOC evidence following the task generation pattern in AGENT.md.

Update PYTHON_PORT_PLAN.md with new tasks in the appropriate subsystem blocks."

    # Run Codex with the analysis prompt
    codex exec \
        --sandbox workspace-write \
        --approval-mode on-request \
        --quiet \
        --config "$PROJECT_ROOT/.codex/config.toml" \
        "$analysis_prompt" 2>&1 | tee -a "$LOG_FILE"
    
    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -eq 0 ]; then
        log_success "Architectural analysis completed"
    else
        log_error "Architectural analysis failed with exit code $exit_code"
        return $exit_code
    fi
}

# Run task execution (AGENT.EXECUTOR.md)
run_task_execution() {
    log_step "Running task execution (AGENT.EXECUTOR.md)..."
    
    # Check for open tasks in PYTHON_PORT_PLAN.md
    local open_tasks=$(grep -c "^- \[P[012]\]" "$PLAN_FILE" || true)
    
    if [ "$open_tasks" -eq 0 ]; then
        log_success "No open tasks found for execution"
        return 0
    fi
    
    log "Found $open_tasks open tasks for execution"
    
    # Create execution prompt
    local execution_prompt="Following the AGENT.EXECUTOR.md workflow, implement tasks from PYTHON_PORT_PLAN.md.

Execute up to 4 tasks per run (respecting batch limits from agent/constants.yaml):
- Prioritize P0 tasks first, then P1
- Apply minimal diffs to meet acceptance criteria
- Add/update tests with deterministic RNG
- Validate with ruff, mypy, and pytest
- Mark tasks complete with ✅ and add evidence
- Update NEXT-ACTIONS dashboard if present

Work in small, reviewable diffs and commit changes when successful."

    # Run Codex with the execution prompt
    codex exec \
        --sandbox workspace-write \
        --approval-mode on-request \
        --quiet \
        --config "$PROJECT_ROOT/.codex/config.toml" \
        "$execution_prompt" 2>&1 | tee -a "$LOG_FILE"
    
    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -eq 0 ]; then
        log_success "Task execution completed"
    else
        log_error "Task execution failed with exit code $exit_code"
        return $exit_code
    fi
}

# Run validation tests
run_validation() {
    log_step "Running validation tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run linting
    log "Running ruff check..."
    if ruff check . 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Linting passed"
    else
        log_error "Linting failed"
        return 1
    fi
    
    # Run type checking
    log "Running mypy..."
    if mypy --strict . 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Type checking passed"
    else
        log_warning "Type checking had issues (may be acceptable)"
    fi
    
    # Run tests
    log "Running pytest..."
    if pytest -q 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Tests passed"
    else
        log_error "Tests failed"
        return 1
    fi
    
    log_success "Validation completed"
}

# Main execution workflow
main() {
    log_step "Starting autonomous coding workflow"
    log "Project root: $PROJECT_ROOT"
    log "Log file: $LOG_FILE"
    
    cd "$PROJECT_ROOT"
    
    # Parse command line arguments
    local mode="auto"  # auto, audit-only, execute-only
    local max_iterations=3
    local approval_mode="on-request"  # never, on-request, untrusted
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mode)
                mode="$2"
                shift 2
                ;;
            --max-iterations)
                max_iterations="$2"
                shift 2
                ;;
            --approval-mode)
                approval_mode="$2"
                shift 2
                ;;
            --full-auto)
                approval_mode="never"
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --mode MODE              auto, audit-only, execute-only (default: auto)"
                echo "  --max-iterations N       Maximum iterations (default: 3)"
                echo "  --approval-mode MODE     never, on-request, untrusted (default: on-request)"
                echo "  --full-auto              Same as --approval-mode never"
                echo "  --help                   Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    check_prerequisites
    
    # Main execution loop
    local iteration=1
    while [ $iteration -le $max_iterations ]; do
        log_step "Iteration $iteration/$max_iterations"
        
        case $mode in
            auto)
                if ! run_architectural_analysis; then
                    log_error "Architectural analysis failed, stopping"
                    exit 1
                fi
                
                if ! run_task_execution; then
                    log_error "Task execution failed, stopping"
                    exit 1
                fi
                ;;
            audit-only)
                if ! run_architectural_analysis; then
                    log_error "Architectural analysis failed, stopping"
                    exit 1
                fi
                break
                ;;
            execute-only)
                if ! run_task_execution; then
                    log_error "Task execution failed, stopping"
                    exit 1
                fi
                break
                ;;
        esac
        
        # Check if we have more work to do
        local remaining_work=$(get_low_confidence_subsystems | wc -l)
        local open_tasks=$(grep -c "^- \[P[012]\]" "$PLAN_FILE" || true)
        
        if [ "$remaining_work" -eq 0 ] && [ "$open_tasks" -eq 0 ]; then
            log_success "All work completed!"
            break
        fi
        
        log "Remaining low-confidence subsystems: $remaining_work"
        log "Open tasks: $open_tasks"
        
        ((iteration++))
    done
    
    if ! run_validation; then
        log_error "Final validation failed"
        exit 1
    fi
    
    # Generate summary report
    log_step "Generating summary report..."
    echo
    log "${GREEN}🎉 Autonomous coding session completed!${NC}"
    log "📊 Summary:"
    log "  - Iterations: $iteration/$max_iterations"
    log "  - Mode: $mode"
    log "  - Log file: $LOG_FILE"
    
    # Show git status
    if ! git diff-index --quiet HEAD --; then
        log "📝 Changes made:"
        git diff --stat HEAD | tee -a "$LOG_FILE"
        
        echo
        log "${YELLOW}💡 Next steps:${NC}"
        log "  - Review changes: git diff"
        log "  - Commit changes: git add . && git commit -m 'autonomous coding session'"
        log "  - Check updated plan: less PYTHON_PORT_PLAN.md"
    else
        log "ℹ️  No changes were made to the codebase"
    fi
}

# Handle script interruption
trap 'log_error "Script interrupted"; exit 130' INT TERM

# Run main function with all arguments
main "$@"