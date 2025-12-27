# Area File Parity: Best Practices

**For**: Developers and builders maintaining QuickMUD area files  
**Goal**: Maintain perfect parity between ROM .are files and Python JSON files

---

## Data Architecture

### File Formats

QuickMUD supports **two area file formats**:

| Format | Location | Use | Primary? |
|--------|----------|-----|----------|
| **ROM .are** | `area/*.are` | Canonical source, ROM C compatible | ✅ YES |
| **JSON** | `data/areas/*.json` | Runtime format, easier editing | NO |

### Data Flow

```
ROM C *.are files (CANONICAL)
        ↓
  convert_enhanced.py (one-time or regenerate)
        ↓
   *.json files (DERIVED)
        ↓
  area_loader.py / json_loader.py (runtime)
        ↓
    Area objects in registries
```

**Key Principle**: `.are` files are the **source of truth**. JSON files are derived artifacts.

---

## Workflow Guidelines

### 1. Editing Existing Areas

**Always follow this sequence**:

```bash
# 1. Edit the .are file (NOT the JSON)
vim area/midgaard.are

# 2. Regenerate JSON from .are
python convert_enhanced.py

# 3. Validate parity
python scripts/validate_area_parity.py

# 4. Test in-game
python -m mud socketserver
# (connect and verify changes)

# 5. Commit both files
git add area/midgaard.are data/areas/midgaard.json
git commit -m "Update Midgaard: [description]"
```

**❌ NEVER**:
- Edit JSON files directly
- Commit .are without regenerating JSON
- Skip validation step

---

### 2. Creating New Areas

```bash
# 1. Create .are file in area/ directory
cp area/template.are area/myarea.are
vim area/myarea.are

# 2. Add to area.lst
echo "myarea.are" >> area/area.lst

# 3. Generate JSON
python convert_enhanced.py area/myarea.are data/areas/myarea.json

# 4. Validate
python scripts/validate_area_parity.py

# 5. Test load
pytest tests/test_area_loader.py -k myarea

# 6. Commit
git add area/myarea.are area/area.lst data/areas/myarea.json
git commit -m "Add new area: myarea"
```

---

### 3. Batch Regeneration (After Major Changes)

If `.are` files were bulk-edited:

```bash
# Regenerate all JSON files
python convert_enhanced.py

# Validate all areas
python scripts/validate_area_parity.py

# Run full test suite
pytest tests/test_area_loader.py
pytest tests/test_reset_handler.py
```

---

## Validation Workflow

### Pre-Commit Validation

**ALWAYS run before committing**:

```bash
# Quick validation
python scripts/validate_area_parity.py

# Expected output:
# ✅ ALL CHECKS PASSED - Area files have perfect parity!
```

### CI/CD Integration

Add to `.github/workflows/tests.yml`:

```yaml
- name: Validate area file parity
  run: python scripts/validate_area_parity.py
```

---

## Troubleshooting Common Issues

### Issue 1: Reset Count Mismatch

**Symptom**: `Reset count mismatch - .are=X vs JSON=Y`

**Cause**: JSON file is stale or conversion failed

**Fix**:
```bash
python convert_enhanced.py area/problematic.are data/areas/problematic.json
python scripts/validate_area_parity.py
```

---

### Issue 2: Reset Argument Mismatch

**Symptom**: `Reset #N mismatch - .are={...} vs JSON={...}`

**Cause**: Manual JSON edit or conversion bug

**Fix**:
```bash
# Option A: Regenerate from .are (recommended)
python convert_enhanced.py area/file.are data/areas/file.json

# Option B: Fix .are file if it's wrong
vim area/file.are
python convert_enhanced.py area/file.are data/areas/file.json
```

---

### Issue 3: Vnum Range Mismatch

**Symptom**: `Vnum range mismatch - .are=(X,Y) vs JSON=(A,B)`

**Cause**: Incomplete conversion or corrupt JSON

**Fix**:
```bash
# Delete corrupt JSON and regenerate
rm data/areas/file.json
python convert_enhanced.py area/file.are data/areas/file.json
```

---

### Issue 4: Area Name Mismatch

**Symptom**: `Name mismatch - .are='None' vs JSON=''`

**Expected For**: Special areas (group.are, rom.are, social.are)

**Fix**: No action needed (expected behavior)

---

## Advanced Topics

### Custom Conversion Options

`convert_enhanced.py` supports options:

```bash
# Convert single file
python convert_enhanced.py area/myarea.are data/areas/myarea.json

# Convert all (default)
python convert_enhanced.py

# Verbose output
python convert_enhanced.py --verbose

# Force overwrite
python convert_enhanced.py --force
```

### Validation Options

```bash
# Verbose output (show all checks)
python scripts/validate_area_parity.py --verbose

# Custom directories
python scripts/validate_area_parity.py \
  --area-dir custom/areas \
  --json-dir custom/json
```

---

## ROM C Parity Rules

### Mob Resets (M command)

```
M <flag> <mob_vnum> <global_limit> <room_vnum> <room_limit>
```

**Critical**: `global_limit` and `room_limit` must match exactly

**Example**:
```
M 0 3061   5 3006  5    * janitor
   ^       ^      ^
   |       |      |
   vnum    global room
           limit  limit
```

### Object Resets (O, E, G, P commands)

All arguments (arg1-arg4) must match exactly.

### Door Resets (D command)

Door states and locks must match.

### Randomization Resets (R command)

Room exit counts must match.

---

## Integration with Game Systems

### Runtime Loading

QuickMUD loads areas in this priority:

1. **JSON (default)**: `use_json=True` → loads `data/areas/*.json`
2. **Fallback**: `use_json=False` → loads `area/*.are`

**Recommendation**: Always keep JSON in sync with .are for consistency.

### Area Registry

Loaded areas are stored in:
- `area_registry` - Area metadata
- `room_registry` - All rooms
- `mob_registry` - Mob prototypes
- `obj_registry` - Object prototypes

### Reset System

Resets are executed by `mud/spawning/reset_handler.py` using data from `Area.resets[]`.

---

## Testing Strategy

### Unit Tests

```bash
# Test area loader
pytest tests/test_area_loader.py

# Test specific area
pytest tests/test_area_loader.py -k test_midgaard_area_loads
```

### Integration Tests

```bash
# Test reset system
pytest tests/test_reset_handler.py

# Test mob spawning
pytest tests/test_mob_spawning.py
```

### Manual Testing

```bash
# Start server
python -m mud socketserver

# Connect and test
telnet localhost 5000

# In-game commands
goto 3001
look
stat area
areas
```

---

## Monitoring and Maintenance

### Regular Validation

**Recommended**: Run validation weekly or after bulk edits

```bash
# Weekly validation
python scripts/validate_area_parity.py > parity_report_$(date +%Y%m%d).txt
```

### Git Hooks

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Validating area file parity..."
python scripts/validate_area_parity.py
if [ $? -ne 0 ]; then
    echo "❌ Area parity check failed! Run:"
    echo "   python convert_enhanced.py"
    echo "   python scripts/validate_area_parity.py"
    exit 1
fi
```

---

## Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| Regenerate all JSON | `python convert_enhanced.py` |
| Validate parity | `python scripts/validate_area_parity.py` |
| Test area loader | `pytest tests/test_area_loader.py` |
| Start server | `python -m mud socketserver` |

### File Locations

| Type | Path |
|------|------|
| ROM .are files | `area/*.are` |
| JSON files | `data/areas/*.json` |
| Conversion script | `convert_enhanced.py` |
| Validation script | `scripts/validate_area_parity.py` |
| Area loader | `mud/loaders/area_loader.py` |
| JSON loader | `mud/loaders/json_loader.py` |

---

## Conclusion

**Golden Rules**:

1. ✅ **Always edit .are files** (never JSON directly)
2. ✅ **Regenerate JSON after .are edits**
3. ✅ **Validate before committing**
4. ✅ **Test in-game after changes**
5. ✅ **Commit both .are and JSON together**

Following these practices ensures **100% ROM parity** and prevents data corruption.

---

**Questions?** See `AREA_PARITY_REPORT.md` for detailed validation results.
