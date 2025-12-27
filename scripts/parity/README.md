# Parity Analysis Scripts

Tools for analyzing and tracking ROM C parity in QuickMUD.

## 🛠️ Scripts

### test_data_gatherer.py
Gathers test coverage and parity data for all subsystems.

**Usage**:
```bash
# Generate parity report
python3 scripts/parity/test_data_gatherer.py

# Updates PROJECT_COMPLETION_STATUS.md with confidence scores
```

**Features**:
- Calculates subsystem confidence scores
- Tracks test coverage
- Identifies parity gaps
- Updates completion status

### parity_analyzer.py
Analyzes ROM C to Python mapping and identifies gaps.

**Usage**:
```bash
# Analyze parity gaps
python3 scripts/parity/parity_analyzer.py
```

### function_mapper.py
Maps ROM C functions to Python implementations.

**Usage**:
```bash
# Generate function mapping
python3 scripts/parity/function_mapper.py
```

### confidence_tracker.py
Tracks confidence scores over time for subsystems.

**Usage**:
```bash
# Update confidence tracking
python3 scripts/parity/confidence_tracker.py
```

### differential_tester.py
Compares QuickMUD Python output with ROM C output.

**Usage**:
```bash
# Run differential tests
python3 scripts/parity/differential_tester.py
```

### division_auditor.py
Audits C integer division vs Python division for parity.

**Usage**:
```bash
# Audit division operations
python3 scripts/parity/division_auditor.py
```

### find_mappings.py
Finds mappings between ROM C source files and Python modules.

**Usage**:
```bash
# Find C to Python mappings
python3 scripts/parity/find_mappings.py
```

### verify_unmapped.py
Identifies unmapped ROM C functions.

**Usage**:
```bash
# Find unmapped functions
python3 scripts/parity/verify_unmapped.py
```

## 📊 Reports Generated

These scripts generate:
- Parity gap analyses
- Function coverage reports
- Confidence score tracking
- Differential test results

**Report Storage**: Generated reports are stored in `reports/` subfolder:
- `parity_gap_report.txt` - Detailed parity gap analysis
- `division_audit_report.txt` - C integer division audit
- `confidence_history.json` - Historical confidence scores
- `strategic_recommendations.json` - Strategic improvement recommendations

## 🔗 Related

- **Documentation**: See [docs/parity/](../../docs/parity/)
- **Validation**: See [scripts/validation/](../validation/)
- **Status**: See [PROJECT_COMPLETION_STATUS.md](../../PROJECT_COMPLETION_STATUS.md)

## ✅ Usage Pattern

Typical workflow:
1. Run `test_data_gatherer.py` to update confidence scores
2. Run `parity_analyzer.py` to identify gaps
3. Run `function_mapper.py` to see C to Python mappings
4. Implement missing functionality
5. Run validation scripts to verify
6. Re-run `test_data_gatherer.py` to confirm improvement
