# Validation Test Reports

This folder contains test baseline reports and validation outputs.

## 📊 Report Files

### test_baseline_2025-10-05.txt
**Purpose**: Original test baseline from October 2025  
**Use**: Compare current test results against historical baseline  
**Contents**:
- Test counts and pass rates
- Subsystem test coverage
- Known issues at baseline date

## 🔄 Generating New Baselines

To create a new test baseline:
```bash
cd /Users/markjedrzejczyk/dev/projects/rom24-quickmud-python

# Run full test suite and save output
pytest -v > scripts/validation/reports/test_baseline_$(date +%Y-%m-%d).txt 2>&1

# Or with coverage
pytest --cov=mud --cov-report=term > scripts/validation/reports/test_baseline_$(date +%Y-%m-%d).txt 2>&1
```

## 📊 MobProg Validation Reports

To generate MobProg validation reports:
```bash
# Validate all areas
python3 scripts/validation/validate_mobprogs.py area/*.are --verbose \
  > scripts/validation/reports/mobprog_validation_$(date +%Y-%m-%d).txt

# Validate specific area
python3 scripts/validation/validate_mobprogs.py area/midgaard.are --verbose \
  > scripts/validation/reports/midgaard_validation_$(date +%Y-%m-%d).txt
```

## 📅 When to Generate New Reports

Create new baselines/reports:
- **After major feature completion** - Capture improved test state
- **Before releases** - Document pre-release test status
- **Monthly** - Track progress over time
- **After test additions** - Show improved coverage

## 🔍 Comparing Reports

```bash
# Compare current tests to baseline
diff scripts/validation/reports/test_baseline_2025-10-05.txt \
     scripts/validation/reports/test_baseline_$(date +%Y-%m-%d).txt

# Count test improvements
grep "passed" scripts/validation/reports/test_baseline_*.txt
```
