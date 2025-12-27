# Validation Scripts

Automated tools for validating QuickMUD functionality and ROM C parity.

## 🛠️ Scripts

### validate_mobprogs.py
Validates MobProgs in ROM area files.

**Usage**:
```bash
# Validate all area files
python3 scripts/validation/validate_mobprogs.py area/*.are

# Verbose output
python3 scripts/validation/validate_mobprogs.py area/midgaard.are --verbose

# Test execution (smoke test)
python3 scripts/validation/validate_mobprogs.py area/*.are --test-execute
```

**Features**:
- Validates all 16 trigger types
- Checks if/endif pairing
- Validates movement commands (mpgoto, mptransfer)
- Smoke test execution
- Detailed error reporting

### validate_area_parity.py
Validates area file ROM C compatibility.

**Usage**:
```bash
# Validate area file
python3 scripts/validation/validate_area_parity.py area/midgaard.are
```

## 📊 Output

Validation scripts provide:
- Summary statistics (total mobs, programs, errors)
- Detailed error messages with line numbers
- Warning messages for suspicious patterns
- Usage statistics (e.g., % programs using movement)

**Report Storage**: Test baselines and validation reports are stored in `reports/` subfolder:
- `test_baseline_2025-10-05.txt` - Original test baseline for comparison

## 🔗 Related

- **Documentation**: See [docs/validation/](../../docs/validation/)
- **Parity Tools**: See [scripts/parity/](../parity/)
- **Tests**: See [tests/integration/](../../tests/integration/)

## ✅ Status

All validation scripts operational and tested.
