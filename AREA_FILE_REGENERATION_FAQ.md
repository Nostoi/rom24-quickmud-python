# Area File Regeneration - FAQ

## ❓ Do we need to regenerate .are files?

### ❌ NO - Never regenerate .are files!

**Data Flow** (one direction only):

```
.are files (SOURCE OF TRUTH - CANONICAL)
    ↓ (convert_enhanced.py)
JSON files (DERIVED - generated from .are)
    ↓ (area_loader.py / json_loader.py)
Game runtime (Area objects)
```

### Key Principles

1. **`.are` files are the canonical source** - These are the original ROM 2.4 format
2. **JSON files are derived artifacts** - Generated FROM .are files
3. **Flow is one-way**: .are → JSON (never JSON → .are)
4. **Always edit .are**, then regenerate JSON

---

## ✅ What SHOULD be regenerated?

### Regenerate JSON files when:

1. **After editing .are files**:
   ```bash
   vim area/midgaard.are
   python convert_enhanced.py  # Regenerate JSON
   ```

2. **After fixing discrepancies** (like ofcol.are):
   ```bash
   python convert_enhanced.py area/ofcol.are data/areas/ofcol.json
   ```

3. **After bulk .are edits**:
   ```bash
   python convert_enhanced.py  # Regenerate all JSON
   ```

---

## 🔧 Pre-Commit Hook Added

### What was added to `.pre-commit-config.yaml`:

```yaml
- id: validate-area-parity
  name: Validate ROM .are and JSON area file parity
  entry: python3 scripts/validate_area_parity.py
  language: system
  pass_filenames: false
  files: ^(area/.*\.are|data/areas/.*\.json)$
```

### When it runs:

- **Triggers**: When you commit changes to `area/*.are` or `data/areas/*.json`
- **Validation**: Checks that .are and JSON files match
- **Fails if**: Discrepancies found (forces you to regenerate JSON)

### Example workflow:

```bash
# 1. Edit .are file
vim area/midgaard.are

# 2. Regenerate JSON
python convert_enhanced.py

# 3. Commit (pre-commit hook validates automatically)
git add area/midgaard.are data/areas/midgaard.json
git commit -m "Update Midgaard janitor limit"
# → Hook runs validate_area_parity.py
# → If parity OK: commit succeeds
# → If parity broken: commit fails, shows errors
```

---

## 🚨 Current Parity Issues

### Issues found (from validation):

1. **ofcol.are** - JSON conversion failed (0 resets vs 12)
   ```bash
   python convert_enhanced.py area/ofcol.are data/areas/ofcol.json
   ```

2. **canyon.are** - Reset #6 argument mismatch
   ```bash
   # Check original .are intent
   grep "9202" area/canyon.are
   # Fix .are or JSON as appropriate
   python convert_enhanced.py area/canyon.are data/areas/canyon.json
   ```

### Fix before committing:

```bash
# Fix critical issue
python convert_enhanced.py area/ofcol.are data/areas/ofcol.json

# Validate all areas
python scripts/validate_area_parity.py

# Should show 100% parity (0 failures)
```

---

## 📋 Quick Reference

| Scenario | Action | Command |
|----------|--------|---------|
| Edit .are file | Regenerate JSON | `python convert_enhanced.py` |
| Add new .are | Generate JSON | `python convert_enhanced.py area/new.are data/areas/new.json` |
| Fix JSON errors | Regenerate from .are | `python convert_enhanced.py area/file.are data/areas/file.json` |
| Validate parity | Run validation | `python scripts/validate_area_parity.py` |
| Bulk regeneration | Regenerate all | `python convert_enhanced.py` |

### ❌ Never do this:

- Edit JSON files directly
- Generate .are from JSON
- Commit .are without regenerating JSON
- Skip validation before committing

### ✅ Always do this:

- Edit .are files (source of truth)
- Regenerate JSON after .are edits
- Validate with `scripts/validate_area_parity.py`
- Commit both .are and JSON together

---

## 🎯 Summary

**Your question**: "Do we need to regenerate .are files?"

**Answer**: 
- ❌ **NO** - Never regenerate .are files
- ✅ **YES** - Always regenerate JSON files (from .are)
- 🔧 **Pre-commit hook** - Now validates parity automatically
- 📊 **Current status** - 97% parity, need to fix ofcol.are

**Next step**:
```bash
# Fix the 1 critical issue
python convert_enhanced.py area/ofcol.are data/areas/ofcol.json
python scripts/validate_area_parity.py  # Should show 100% parity
```
