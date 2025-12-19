# QuickMUD Development Guide for AI Agents

## Build/Lint/Test Commands
```bash
# Run all tests (200+ tests, ~16s)
pytest

# Run single test file
pytest tests/test_combat.py

# Run specific test function
pytest tests/test_combat.py::test_rescue_checks_group_permission

# Run tests matching keyword
pytest -k "movement"

# Run with coverage (CI requirement: ≥80%)
pytest --cov=mud --cov-report=term --cov-fail-under=80

# Lint with ruff
ruff check .
ruff format --check .

# Type check with mypy (strict on specific modules)
mypy mud/net/ansi.py mud/security/hash_utils.py --follow-imports=skip
```

## Code Style Guidelines

**Imports:** `from __future__ import annotations` first; stdlib, third-party, local (alphabetical within groups)  
**Types:** Strict annotations throughout; use `TYPE_CHECKING` guard for circular imports  
**Naming:** `snake_case` functions/vars, `PascalCase` classes, `UPPER_CASE` constants, `_prefix` for private  
**Docstrings:** Required for public functions; include ROM C source references for parity code  
**Error handling:** Defensive programming with try/except; specific exceptions where possible  
**Formatting:** Line length 120 (ruff/black), double quotes, 4-space indent

## ROM Parity Rules (CRITICAL)
- **RNG:** Use `rng_mm.number_*` family, NEVER `random.*` in combat/affects  
- **Math:** Use `c_div`/`c_mod` for C integer semantics, NEVER `//` or `%`  
- **Comments:** Reference ROM C sources (e.g., `# mirroring ROM src/fight.c:one_hit`)  
- **Tests:** Golden files derived from ROM behavior; assert exact C semantics  
- See `port.instructions.md` for exhaustive parity rules

## Test Fixtures (from conftest.py)
```python
movable_char_factory(name, room_vnum, points=100)  # Test character with movement
movable_mob_factory(vnum, room_vnum, points=100)   # Test mob with movement  
object_factory(proto_kwargs)                       # Object without placement
place_object_factory(room_vnum, vnum=..., proto_kwargs=...)  # Object in room
portal_factory(room_vnum, to_vnum, closed=False)   # Portal object
ensure_can_move(entity, points=100)                # Setup movement fields
```

## CI Workflow
Pre-commit hooks run `black`, `ruff --fix`, and fixture lint. CI runs: help data drift check, ruff/flake8 lint, mypy type check (select modules), pytest with 80% coverage, telnet tests (Linux only). All must pass.
