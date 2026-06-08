# ROM 2.4 QuickMUD Development Skill

A comprehensive Claude Desktop skill for developing and maintaining the QuickMUD ROM 2.4b Python port.

## Skill Purpose

This skill enables AI assistants to effectively work on QuickMUD, a modern Python port of the ROM 2.4b6 MUD (Multi-User Dungeon) engine with 100% ROM C behavioral parity.

## Key Capabilities

### ROM Parity Verification
- Implement ROM 2.4b C features with exact behavioral parity
- Reference ROM C source code (in `src/` directory) for ground truth
- Use ROM-specific RNG (`rng_mm.number_*`), math (`c_div`, `c_mod`), and enums
- Write differential tests against ROM C golden outputs

### Code Standards
- Follow strict Python type hints with `from __future__ import annotations`
- Use ROM C source references in docstrings (e.g., `# ROM C: src/fight.c:567-783`)
- Maintain 80%+ test coverage with pytest
- Run `ruff` for linting and `mypy` for type checking on select modules

### Testing Requirements
- **Unit Tests** (`tests/test_*.py`): Component-level testing
- **Integration Tests** (`tests/integration/`): End-to-end player workflows
- **Command Tests** (`test_all_commands.py`): Validate all 287 commands
- All new features must include tests before claiming completion

### Documentation Requirements
- Update `CHANGELOG.md` for all user-facing changes
- Reference relevant parity documents:
  - `docs/parity/ROM_PARITY_FEATURE_TRACKER.md` - Feature implementation status
  - `docs/validation/MOBPROG_TESTING_GUIDE.md` - MobProg testing
  - `docs/validation/MOB_PARITY_TEST_PLAN.md` - Mob behavior tests
  - `docs/validation/PLAYER_PARITY_TEST_PLAN.md` - Player behavior tests

### Project Structure
```
rom24-quickmud-python/
├── mud/                    # Core MUD engine
│   ├── combat/            # Combat system
│   ├── commands/          # Player commands
│   ├── models/            # Data models
│   ├── net/               # Networking (telnet/SSH)
│   └── spawning/          # Mob/object spawning
├── tests/                 # Test suite
│   └── integration/       # End-to-end tests
├── area/                  # World area files
├── docs/                  # Documentation
│   ├── parity/           # ROM C parity tracking
│   └── validation/       # Testing guides
├── scripts/              # Utility scripts
│   ├── parity/          # Parity analysis tools
│   └── validation/      # Validation tools
└── src/                  # Original ROM C source (reference)
```

## Common Tasks

### Implementing ROM Features
1. Check `docs/parity/ROM_PARITY_FEATURE_TRACKER.md` for priority
2. Reference ROM C source code in `src/`
3. Implement with exact ROM semantics (RNG, math, enums)
4. Write tests with ROM C golden outputs
5. Update feature tracker and CHANGELOG.md

### Running Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/test_combat.py

# Integration tests
pytest tests/integration/ -v

# Command validation
python3 test_all_commands.py

# With coverage
pytest --cov=mud --cov-report=term --cov-fail-under=80
```

### Code Quality Checks
```bash
# Lint
ruff check .
ruff format --check .

# Type check (strict modules only)
mypy mud/net/ansi.py mud/security/hash_utils.py --follow-imports=skip
```

## ROM C Parity Rules

### Critical Rules
- **Never use `random.*`** in combat/affects - use `rng_mm.number_*` family
- **Never use `//` or `%`** - use `c_div()`/`c_mod()` for C integer semantics
- **Always use enums** - NEVER hardcode flag values (e.g., `PlayerFlag.AUTOLOOT`)
- **Comment ROM sources** - Reference specific ROM C files and line numbers

### Example
```python
# ❌ WRONG
damage = random.randint(1, 10)  # Wrong RNG
armor_class = player.level // 2  # Wrong division
PLR_AUTOLOOT = 0x0010  # Hardcoded flag

# ✅ CORRECT
from mud.util.rng_mm import number_range
from mud.util.math import c_div
from mud.models.constants import PlayerFlag

# ROM C: src/fight.c:197-259
damage = number_range(1, 10)  # ROM RNG
armor_class = c_div(player.level, 2)  # C division
if player.act & PlayerFlag.AUTOLOOT:  # Use enum
```

## Test Fixtures (conftest.py)
```python
movable_char_factory(name, room_vnum, points=100)  # Character with movement
movable_mob_factory(vnum, room_vnum, points=100)   # Mob with movement
object_factory(proto_kwargs)                       # Object without placement
place_object_factory(room_vnum, vnum=..., proto_kwargs=...)  # Object in room
portal_factory(room_vnum, to_vnum, closed=False)   # Portal object
ensure_can_move(entity, points=100)                # Setup movement fields
```

## Autonomous Development Mode

When explicitly directed by user, agent may enter autonomous task completion:

### Activation
- User says "start autonomous mode" or "complete all tasks"
- User specifies scope (P0 only, P0+P1, or all)
- User sets time limit and error handling policy

### Workflow
1. Create comprehensive todo list from task documents
2. Execute tasks sequentially without waiting for approval
3. Fix errors immediately before proceeding
4. Run full test suite after each major task
5. Update documentation (CHANGELOG.md, feature trackers)
6. Stop at time limit or scope completion

### Quality Gates (MANDATORY)
- Run acceptance tests after each task
- Run full test suite (1555+ tests) to catch regressions
- Fix any test failures immediately before proceeding
- Update parity trackers with completion status

## Key Documents

### Primary References
- `AGENTS.md` - Agent development guidelines
- `CHANGELOG.md` - Version history
- `docs/parity/ROM_PARITY_FEATURE_TRACKER.md` - Feature status
- `docs/validation/MOBPROG_TESTING_GUIDE.md` - MobProg testing
- `docs/validation/MOB_PARITY_TEST_PLAN.md` - Mob behavior tests
- `docs/validation/PLAYER_PARITY_TEST_PLAN.md` - Player behavior tests

### Testing Levels
1. **Unit Tests** - Component isolation testing
2. **Integration Tests** - Complete player workflows
3. **Command Tests** - All 287 commands callable
4. **Parity Tests** - Differential testing vs ROM C

## Version Information

**Current Version**: 2.3.1  
**ROM Source**: 2.4b6  
**Python**: 3.10+  
**Test Count**: 1555+ passing  
**Command Count**: 287 total  
**ROM C Functions**: 96.1% coverage  

## Success Criteria

### Feature Complete
- [ ] Tests written with ROM C references
- [ ] All tests passing (no regressions)
- [ ] CHANGELOG.md updated
- [ ] Feature tracker updated
- [ ] Code follows ROM parity rules

### Release Ready
- [ ] Version number updated (pyproject.toml, README.md)
- [ ] CHANGELOG.md has release notes
- [ ] All tests passing (1555+)
- [ ] No lint/type errors
- [ ] Git tag created and pushed

## Example Workflows

### Add New Command
1. Check ROM C source for command implementation
2. Implement in `mud/commands/*.py`
3. Add to command dispatcher
4. Write tests with ROM C golden outputs
5. Update CHANGELOG.md
6. Run test suite

### Fix Bug
1. Write failing test that reproduces bug
2. Reference ROM C behavior
3. Fix implementation
4. Verify test passes
5. Run full test suite
6. Update CHANGELOG.md if user-facing

### Implement Missing Feature
1. Check feature tracker for priority
2. Review ROM C implementation
3. Implement with parity rules
4. Write comprehensive tests
5. Update feature tracker and CHANGELOG.md
6. Run parity validation scripts

## Notes

- Always reference ROM C source code for ground truth
- Never claim "100% parity" without differential testing
- Prefer integration tests for end-to-end validation
- Update all three testing levels when adding features
- Keep ROM C source comments in code for traceability

---

**Skill Version**: 1.0.0  
**Last Updated**: 2025-12-27  
**Maintainer**: Mark Jedrzejczyk
