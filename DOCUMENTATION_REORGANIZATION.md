# Documentation and Scripts Reorganization

**Date**: 2025-12-26  
**Status**: ✅ Complete

---

## 📂 New Folder Structure

### Documentation Folders

#### `docs/validation/`
MobProg validation and testing documentation:
- `MOBPROG_TESTING_GUIDE.md` - Comprehensive testing methodology
- `MOBPROG_TESTING_SUMMARY.md` - Executive summary
- `MOBPROG_COMPLETION_PLAN.md` - Implementation plan
- `MOBPROG_COMPLETION_REPORT.md` - Completion report
- `MOBPROG_MOVEMENT_VALIDATION.md` - Movement command validation
- `README.md` - Folder overview

#### `docs/parity/`
ROM C parity tracking documentation:
- `ROM_PARITY_FEATURE_TRACKER.md` - Feature-by-feature parity tracking
- `ROM_C_PARITY_MAPPING.md` - C to Python mapping
- `ROM_HEADER_FILES_AUDIT.md` - ROM C header analysis
- `AREA_PARITY_REPORT.md` - Area file compatibility
- `AREA_PARITY_BEST_PRACTICES.md` - Area development best practices
- `README.md` - Folder overview

### Scripts Folders

#### `scripts/validation/`
Validation and testing scripts:
- `validate_mobprogs.py` - MobProg validation for area files
- `validate_area_parity.py` - Area file ROM C compatibility check
- `README.md` - Usage guide
- `reports/` - Generated validation reports and test baselines

#### `scripts/parity/`
Parity analysis and tracking tools:
- `test_data_gatherer.py` - Subsystem confidence tracking
- `parity_analyzer.py` - ROM C gap analysis
- `function_mapper.py` - C to Python function mapping
- `confidence_tracker.py` - Historical confidence tracking
- `differential_tester.py` - Python vs C output comparison
- `division_auditor.py` - Integer division parity check
- `find_mappings.py` - Find C to Python mappings
- `verify_unmapped.py` - Identify unmapped functions
- `README.md` - Tool descriptions
- `reports/` - Generated parity analysis reports

---

## 🔄 Updated References

### Main Documentation Files
- ✅ `README.md` - Updated parity badge and documentation links
- ✅ `AGENTS.md` - Updated all ROM_PARITY_FEATURE_TRACKER.md references

### Validation Documentation
- ✅ All MobProg docs updated with relative paths
- ✅ Cross-references between docs/validation/ files maintained
- ✅ Links to scripts/validation/ updated

---

## 📖 Quick Reference

### Viewing Documentation

**Parity Status**:
```bash
# Primary parity tracking document
cat docs/parity/ROM_PARITY_FEATURE_TRACKER.md

# Area-specific parity
cat docs/parity/AREA_PARITY_REPORT.md
```

**Validation Guides**:
```bash
# MobProg testing guide
cat docs/validation/MOBPROG_TESTING_GUIDE.md

# MobProg completion report
cat docs/validation/MOBPROG_COMPLETION_REPORT.md
```

### Running Scripts

**Validation**:
```bash
# Validate MobProgs in area files
python3 scripts/validation/validate_mobprogs.py area/*.are --verbose

# Validate area parity
python3 scripts/validation/validate_area_parity.py area/midgaard.are
```

**Parity Analysis**:
```bash
# Update subsystem confidence scores
python3 scripts/parity/test_data_gatherer.py

# Analyze parity gaps
python3 scripts/parity/parity_analyzer.py

# Map C functions to Python
python3 scripts/parity/function_mapper.py
```

---

## ✅ Benefits of New Organization

### 1. **Clear Separation of Concerns**
- Validation docs separate from parity tracking
- Scripts organized by purpose

### 2. **Better Discoverability**
- README files in each folder explain contents
- Related files grouped together

### 3. **Easier Navigation**
- Documentation in `docs/`
- Scripts in `scripts/`
- Logical subfolder structure

### 4. **Maintainability**
- Clear ownership of documentation types
- Easier to update related files together

---

## 🔗 Key Links

| Resource | Location |
|----------|----------|
| **Parity Tracker** | [docs/parity/ROM_PARITY_FEATURE_TRACKER.md](docs/parity/ROM_PARITY_FEATURE_TRACKER.md) |
| **MobProg Testing** | [docs/validation/MOBPROG_TESTING_GUIDE.md](docs/validation/MOBPROG_TESTING_GUIDE.md) |
| **Validate MobProgs** | [scripts/validation/validate_mobprogs.py](scripts/validation/validate_mobprogs.py) |
| **Parity Analysis** | [scripts/parity/test_data_gatherer.py](scripts/parity/test_data_gatherer.py) |
| **Validation Docs** | [docs/validation/README.md](docs/validation/README.md) |
| **Parity Docs** | [docs/parity/README.md](docs/parity/README.md) |

---

## 📋 Files Moved

### Documentation (10 files)
- ✅ 5 MobProg files → `docs/validation/`
- ✅ 5 Parity files → `docs/parity/`

### Scripts (10 files)
- ✅ 2 Validation scripts → `scripts/validation/`
- ✅ 8 Parity scripts → `scripts/parity/`

### Created (4 files)
- ✅ `docs/validation/README.md`
- ✅ `docs/parity/README.md`
- ✅ `scripts/validation/README.md`
- ✅ `scripts/parity/README.md`

### Report Files Moved (5 files)
- ✅ `parity_gap_report.txt` → `scripts/parity/reports/`
- ✅ `division_audit_report.txt` → `scripts/parity/reports/`
- ✅ `confidence_history.json` → `scripts/parity/reports/`
- ✅ `strategic_recommendations.json` → `scripts/parity/reports/`
- ✅ `test_baseline_2025-10-05.txt` → `scripts/validation/reports/`

### Report Folders Created (2 folders + READMEs)
- ✅ `scripts/parity/reports/` + README.md
- ✅ `scripts/validation/reports/` + README.md

---

**Total Changes**: 24 files organized, 6 READMEs created, 5 reports moved, all references updated ✅
