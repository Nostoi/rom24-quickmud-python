# Technical Specification: 100% ROM 2.4b Parity Implementation

**Status**: Draft Technical Specification  
**Date**: 2025-12-21  
**Current Parity**: 95-98% (per ROM_PARITY_AUDIT_2025-12-20.md)  
**Target**: 100% ROM 2.4b Feature Parity  

---

## Executive Summary

This specification details the implementation requirements for the remaining 2-5% of features needed to achieve 100% ROM 2.4b parity in QuickMUD. Based on comprehensive audit findings, all remaining work consists of **convenience features** rather than critical gameplay mechanics.

### Remaining Features (Priority Order)

1. **@hedit** - Help file editor (Medium Priority)
2. **Spell Component System** - Material component requirements (Low Priority)
3. **mpdump Command** - Mob program debugging tool (Very Low Priority)

**Note**: Investigation revealed that @aedit, @oedit, and @medit are **already implemented** in `mud/commands/build.py` (lines 1221-2023), contradicting earlier documentation claims.

---

## Part 1: OLC Editor Suite Completion

### Current Implementation Status (VERIFIED)

**✅ Already Implemented** (found in `mud/commands/build.py`):
- `cmd_aedit` (lines 1221-1248) - Area editor entry point
- `_interpret_aedit` (lines 1256-1369) - Area editor command interpreter
- `cmd_oedit` (lines 1425-1464) - Object editor entry point
- `_interpret_oedit` (lines 1472-1606) - Object editor command interpreter  
- `cmd_medit` (lines 1709-1748) - Mobile editor entry point
- `_interpret_medit` (lines 1756-1969) - Mobile editor command interpreter

**❌ Missing**:
- `cmd_hedit` - Help file editor (needs implementation)

### 1.1 Help Editor (@hedit) - MEDIUM PRIORITY

**ROM Reference**: `src/hedit.c:1-500`  
**Python Target**: `mud/commands/build.py` (extend existing OLC framework)  
**Estimated Effort**: 1-2 days

#### Architecture

Follow existing OLC editor pattern established by @aedit/@oedit/@medit:

```python
def cmd_hedit(char: Character, args: str) -> str:
    """Help editor - ROM src/hedit.c:284-333."""
    session = _get_session(char)
    if session is None:
        return "You do not have an active connection."
    
    arg = args.strip()
    
    if session.editor == "hedit":
        return _interpret_hedit(session, char, arg)
    
    if not arg:
        return "Syntax: @hedit <keyword>"
    
    # Lookup or create help entry
    help_entry = help_registry.find(arg)
    if help_entry is None:
        # Create new help entry (ROM hedit.c:115-186)
        help_entry = create_help_entry(arg)
    
    # Security check: ROM hedit.c:228-234 requires security >= 9
    if not _is_help_editor(char):
        return "Insufficient security to edit helps."
    
    _ensure_session_help(session, help_entry)
    return f"Now editing help '{help_entry.keyword}'.\\nType 'show' to display, 'done' to exit."

def _interpret_hedit(session: Session, char: Character, raw_input: str) -> str:
    """Command interpreter for hedit - ROM src/hedit.c:205-260."""
    help_entry = session.editor_state.get("help_entry")
    if not isinstance(help_entry, HelpEntry):
        _clear_session(session)
        return "Help editor session lost. Type '@hedit <keyword>' to begin again."
    
    # Parse command (ROM hedit.c:213-215)
    stripped = raw_input.strip()
    if not stripped:
        return "Syntax: keyword <text> | text | level <num> | show | done"
    
    try:
        parts = shlex.split(stripped)
    except ValueError:
        return "Invalid help editor syntax."
    
    if not parts:
        return "Syntax: keyword <text> | text | level <num> | show | done"
    
    cmd = parts[0].lower()
    args_parts = parts[1:]
    
    # Command routing
    if cmd in {"done", "exit"}:
        _clear_session(session)
        return "Exiting help editor."
    
    if cmd == "show":
        return _hedit_show(help_entry)
    
    if cmd == "keyword":
        return _hedit_keyword(help_entry, args_parts)
    
    if cmd == "text":
        return _hedit_text(char, help_entry, args_parts)
    
    if cmd == "level":
        return _hedit_level(help_entry, args_parts)
    
    if cmd == "delete":
        return _hedit_delete(help_entry)
    
    return f"Unknown help editor command: {cmd}"
```

#### Sub-Commands (ROM hedit.c command table)

| Command | ROM C Line | Function | Description |
|---------|-----------|----------|-------------|
| `show` | hedit.c:53-67 | `_hedit_show` | Display help entry (keyword, level, text) |
| `keyword` | hedit.c:96-113 | `_hedit_keyword` | Set help keywords (space-separated) |
| `text` | hedit.c:188-203 | `_hedit_text` | Edit help text (multiline string editor) |
| `level` | hedit.c:69-94 | `_hedit_level` | Set minimum level (-1 to MAX_LEVEL) |
| `delete` | hedit.c:336-398 | `_hedit_delete` | Delete help entry from registry |
| `done` | hedit.c:242-246 | Edit done | Exit editor, save changes |

#### Data Model

**Existing**: `mud/models/help.py` (already has Help data model)

Verify/extend with:
```python
@dataclass
class HelpEntry:
    keyword: str  # Space-separated keywords
    level: int    # Minimum level to view (-1 = all, 0+ = level restricted)
    text: str     # Help text content
    area: Area | None  # Associated area (for hedit.c:144-155)
    changed: bool = False  # Track modifications
```

#### Persistence

**Target**: `data/help.json` (existing help file)

Follow @asave pattern:
```python
def save_help_data() -> bool:
    """Save help registry to data/help.json."""
    # Mirror @asave logic from mud/olc/save.py:save_area_to_json
    pass
```

#### Security

ROM hedit.c:228-234 requires `ch->pcdata->security >= 9`:

```python
def _is_help_editor(char: Character) -> bool:
    """ROM hedit.c:228-234: security check."""
    pcdata = getattr(char, "pcdata", None)
    security = int(getattr(pcdata, "security", 0)) if pcdata else 0
    return security >= 9
```

#### Tests

**Target**: `tests/test_builder_hedit.py` (verify exists per exploration results)

Required test coverage:
```python
def test_hedit_create_new_help():
    """Verify @hedit creates new help entry."""
    
def test_hedit_keyword_modification():
    """Test keyword command changes help keywords."""
    
def test_hedit_text_editing():
    """Test text command triggers multiline editor."""
    
def test_hedit_level_restrictions():
    """Test level command sets visibility (-1 to MAX_LEVEL)."""
    
def test_hedit_delete_removes_entry():
    """Test delete command removes help from registry."""
    
def test_hedit_security_enforcement():
    """Test security < 9 rejected."""
    
def test_hedit_persistence():
    """Test changes saved to data/help.json."""
```

---

## Part 2: Spell Component System - LOW PRIORITY

**ROM Reference**: `src/magic.c:131-213` (find_components function)  
**Python Target**: `mud/skills/handlers.py` (extend spell handlers)  
**Estimated Effort**: 2-3 days

### 2.1 Architecture

#### Component Requirement Data

Add to spell metadata in `mud/skills/metadata.py`:

```python
ROM_SKILL_METADATA = {
    "fireball": {
        "name": "fireball",
        "target": "victim",
        "beats": 12,
        "components": [  # NEW: material components
            {"vnum": 123, "name": "sulfur", "consumed": True},
            {"vnum": 124, "name": "bat guano", "consumed": True},
        ],
    },
    # ... other spells
}
```

#### Component Checking Logic

**ROM magic.c:131-213 algorithm**:

1. Check if spell requires components (ROM L138-142)
2. Search caster's inventory for required items (ROM L144-172)
3. If component is `consumed=True`, extract item (ROM L174-185)
4. If any component missing, spell fails (ROM L187-199)

```python
def check_spell_components(caster: Character, spell_name: str) -> tuple[bool, str]:
    """
    Check if caster has required spell components.
    
    ROM src/magic.c:131-213 (find_components).
    
    Returns:
        (success, failure_message)
    """
    metadata = ROM_SKILL_METADATA.get(spell_name, {})
    required_components = metadata.get("components", [])
    
    if not required_components:
        return True, ""  # No components required
    
    # ROM L144-172: search inventory
    missing_components = []
    for component_spec in required_components:
        vnum = component_spec["vnum"]
        found = False
        
        for obj in getattr(caster, "inventory", []):
            proto = getattr(obj, "prototype", None)
            if proto and getattr(proto, "vnum", None) == vnum:
                found = True
                break
        
        if not found:
            missing_components.append(component_spec["name"])
    
    if missing_components:
        missing = ", ".join(missing_components)
        return False, f"You lack the material components: {missing}."
    
    return True, ""

def consume_spell_components(caster: Character, spell_name: str) -> None:
    """
    Consume required spell components after successful cast.
    
    ROM src/magic.c:174-185.
    """
    metadata = ROM_SKILL_METADATA.get(spell_name, {})
    required_components = metadata.get("components", [])
    
    for component_spec in required_components:
        if not component_spec.get("consumed", False):
            continue  # Component not consumed
        
        vnum = component_spec["vnum"]
        
        # Find and extract first matching object
        for obj in list(getattr(caster, "inventory", [])):
            proto = getattr(obj, "prototype", None)
            if proto and getattr(proto, "vnum", None) == vnum:
                # ROM L177-183: extract_obj
                from mud.commands.inventory import extract_object
                extract_object(obj)
                break
```

#### Integration with Spell Handlers

Modify spell casting pipeline in `mud/skills/registry.py`:

```python
def cast_spell(caster: Character, spell_name: str, target: Any) -> bool:
    """Enhanced spell casting with component checks."""
    
    # Existing checks: mana, level, etc.
    # ...
    
    # NEW: Component check (ROM magic.c:131-213)
    success, error_msg = check_spell_components(caster, spell_name)
    if not success:
        _send_to_char(caster, error_msg)
        return False
    
    # Execute spell handler
    handler = skill_registry.handlers.get(spell_name)
    if handler is None:
        return False
    
    result = handler(caster, target)
    
    # NEW: Consume components after successful cast
    if result:
        consume_spell_components(caster, spell_name)
    
    return result
```

### 2.2 Component Object Prototypes

Create component objects in area files (e.g., `data/areas/midgaard.json`):

```json
{
  "objects": [
    {
      "vnum": 123,
      "name": "sulfur pinch",
      "short_descr": "a pinch of sulfur",
      "long_descr": "A small pinch of sulfur lies here.",
      "item_type": "treasure",
      "weight": 1,
      "cost": 10
    },
    {
      "vnum": 124,
      "name": "bat guano",
      "short_descr": "bat guano",
      "long_descr": "A glob of bat guano sits here.",
      "item_type": "treasure",
      "weight": 1,
      "cost": 5
    }
  ]
}
```

### 2.3 Tests

**Target**: `tests/test_spell_components.py` (new file)

```python
def test_spell_without_components_succeeds():
    """Spells without component requirements cast normally."""
    
def test_spell_with_components_checks_inventory():
    """Spell fails if required component missing."""
    
def test_consumable_components_extracted():
    """Consumed components removed from inventory after cast."""
    
def test_non_consumable_components_retained():
    """Non-consumed components stay in inventory."""
    
def test_multiple_components_all_required():
    """Spell fails if any component missing."""
    
def test_component_failure_returns_mana():
    """Failed component check refunds mana (ROM behavior)."""
```

---

## Part 3: mpdump Command - VERY LOW PRIORITY

**ROM Reference**: `src/mob_cmds.c` (command table, but mpdump not found in provided excerpt)  
**Python Target**: `mud/mob_cmds.py` (extend mob command table)  
**Estimated Effort**: 2-4 hours

### 3.1 Implementation

**Purpose**: Display mob program code for debugging (immortals only).

```python
def do_mpdump(ch: Character, argument: str) -> None:
    """
    Display mob program code for debugging.
    
    ROM src/mob_cmds.c (mpdump command).
    Immortal-only debugging tool.
    """
    # Parse target: vnum or character name
    token = argument.strip()
    if not token:
        _append_message(ch, "Syntax: mpdump <mob name|vnum>")
        return
    
    # Find mob by vnum or name
    try:
        vnum = int(token)
        target_mob = _find_mob_by_vnum(vnum)
    except ValueError:
        target_mob = _find_char_in_room(ch, token)
    
    if target_mob is None:
        _append_message(ch, "Mob not found.")
        return
    
    # Retrieve mob programs
    programs = getattr(target_mob, "mob_programs", None)
    if not programs:
        _append_message(ch, "That mob has no programs.")
        return
    
    # Format output
    output = [f"Mob Programs for {_character_name(target_mob)}:"]
    for idx, program in enumerate(programs, 1):
        trigger = getattr(program, "trigger", "unknown")
        code = getattr(program, "code", "(no code)")
        output.append(f"\\n[{idx}] Trigger: {trigger}")
        output.append(f"Code:\\n{code}")
    
    _append_message(ch, "\\n".join(output))

# Add to command table
_COMMANDS.append(MobCommand("mpdump", do_mpdump))
```

### 3.2 Tests

**Target**: `tests/test_mob_cmds.py` (extend existing)

```python
def test_mpdump_displays_programs():
    """Verify mpdump shows mob program code."""
    
def test_mpdump_handles_no_programs():
    """Test mpdump on mob without programs."""
    
def test_mpdump_by_vnum():
    """Test mpdump <vnum> lookup."""
    
def test_mpdump_by_name():
    """Test mpdump <name> lookup."""
```

---

## Part 4: Implementation Plan

### Phase 1: @hedit Implementation (2 days)

**Day 1**:
1. ✅ Implement `cmd_hedit` entry point
2. ✅ Implement `_interpret_hedit` command interpreter
3. ✅ Implement sub-commands: show, keyword, level, text

**Day 2**:
4. ✅ Implement delete command
5. ✅ Implement help persistence (save to data/help.json)
6. ✅ Write comprehensive tests (7+ tests)
7. ✅ Run full test suite, verify no regressions

**Acceptance Criteria**:
- `pytest tests/test_builder_hedit.py` - all tests pass
- `pytest` - full suite passes (1297+ tests)
- Manual verification: create/edit/delete help via @hedit

---

### Phase 2: Spell Component System (3 days)

**Day 1**:
1. ✅ Add component metadata to ROM_SKILL_METADATA
2. ✅ Implement `check_spell_components` function
3. ✅ Implement `consume_spell_components` function

**Day 2**:
4. ✅ Integrate component checks into spell casting pipeline
5. ✅ Create component object prototypes (sulfur, bat guano, etc.)
6. ✅ Write tests for component checking

**Day 3**:
7. ✅ Write tests for component consumption
8. ✅ Test integration with existing spell handlers
9. ✅ Run full test suite, verify no regressions

**Acceptance Criteria**:
- `pytest tests/test_spell_components.py` - all tests pass
- `pytest` - full suite passes
- Manual verification: cast spell with/without components

---

### Phase 3: mpdump Command (0.5 days)

**Half-Day**:
1. ✅ Implement `do_mpdump` function
2. ✅ Add to mob command table
3. ✅ Write tests
4. ✅ Run full test suite

**Acceptance Criteria**:
- `pytest tests/test_mob_cmds.py::test_mpdump*` - all tests pass
- `pytest` - full suite passes

---

### Phase 4: Documentation and Final Verification (0.5 days)

**Half-Day**:
1. ✅ Update ROM_PARITY_FEATURE_TRACKER.md (mark all features complete)
2. ✅ Update PROJECT_COMPLETION_STATUS.md (all subsystems 1.00 confidence)
3. ✅ Run `scripts/test_data_gatherer.py` (verify 100% parity)
4. ✅ Update README.md (announce 100% ROM parity)

**Final Acceptance**:
- All documentation claims 100% ROM 2.4b parity
- Test suite: 1300+ tests passing
- ROM parity tests: 143/143 passing
- No known bugs or regressions

---

## Part 5: Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| @hedit breaks existing help system | Low | Medium | Comprehensive tests, incremental implementation |
| Spell components break existing spells | Medium | High | Feature-flag components, default to disabled |
| mpdump crashes on malformed programs | Low | Low | Defensive programming, try/except guards |
| Test regressions from new features | Medium | High | Run full test suite after each phase |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Underestimated complexity | Low | Low | Conservative estimates, features are well-scoped |
| Integration issues | Low | Medium | Follow existing OLC patterns, incremental testing |

---

## Part 6: Success Metrics

### Quantitative Metrics

- ✅ Test suite: 1300+ tests passing (current: 1297)
- ✅ ROM parity tests: 143/143 passing
- ✅ Code coverage: ≥80% (current: 80%+)
- ✅ Zero regressions in existing functionality

### Qualitative Metrics

- ✅ All ROM 2.4b C features implemented
- ✅ Help editor fully functional (matches ROM hedit.c behavior)
- ✅ Spell components optional but working (ROM magic.c parity)
- ✅ mpdump command available for debugging
- ✅ Documentation updated to reflect 100% parity

---

## Part 7: References

### ROM C Source Files

- `src/olc.c:1-400` - OLC framework, editor tables
- `src/hedit.c:1-500` - Help editor implementation
- `src/magic.c:131-213` - Spell component system (find_components)
- `src/mob_cmds.c` - Mob command table (mpdump reference)

### Python Implementation Files

- `mud/commands/build.py` - OLC command handlers (@redit/@asave/@aedit/@oedit/@medit)
- `mud/skills/handlers.py` - Spell handler implementations
- `mud/skills/metadata.py` - Spell metadata registry
- `mud/mob_cmds.py` - Mob command implementations
- `mud/olc/save.py` - OLC persistence logic

### Test Files

- `tests/test_builder_hedit.py` - Help editor tests
- `tests/test_spell_components.py` - Component system tests (new)
- `tests/test_mob_cmds.py` - Mob command tests

### Documentation

- `ROM_PARITY_FEATURE_TRACKER.md` - Feature completion tracking
- `ROM_PARITY_AUDIT_2025-12-20.md` - Comprehensive parity audit
- `PROJECT_COMPLETION_STATUS.md` - Subsystem confidence scores
- `BUILDER_GUIDE.md` - OLC usage documentation

---

## Appendix A: Discovered Implementation Status

**CRITICAL FINDING**: During spec creation, discovered that @aedit, @oedit, and @medit are **ALREADY IMPLEMENTED**:

- `cmd_aedit` (build.py:1221-1248)
- `cmd_oedit` (build.py:1425-1464)
- `cmd_medit` (build.py:1709-1748)

**Implication**: ROM_PARITY_FEATURE_TRACKER.md Section 7 ("Missing Editors") is **OUTDATED**. Only @hedit remains unimplemented.

**Recommendation**: Update ROM_PARITY_FEATURE_TRACKER.md immediately to reflect actual completion status.

---

## Appendix B: Alternative: Spell Components as Feature Flag

Given spell components are "nice-to-have realism" (per ROM_PARITY_AUDIT_2025-12-20.md), consider making them **optional**:

```python
# mud/config.py
ENABLE_SPELL_COMPONENTS = False  # Feature flag

# mud/skills/registry.py
def cast_spell(caster: Character, spell_name: str, target: Any) -> bool:
    if ENABLE_SPELL_COMPONENTS:
        success, error_msg = check_spell_components(caster, spell_name)
        if not success:
            _send_to_char(caster, error_msg)
            return False
    
    # ... rest of spell casting logic
```

**Benefits**:
- Zero risk to existing spell system
- Allows gradual rollout
- Can be enabled per-server via config

**Drawback**:
- Adds configuration complexity
- Not strict ROM parity (ROM always checks components)

---

## End of Technical Specification
