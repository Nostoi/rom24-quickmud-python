# ROM 2.4 Golden Reference Files

This directory contains golden reference data captured from the original ROM 2.4b C implementation.
These files are used to verify that the Python port produces identical outputs for the same inputs.

## Contents

### RNG Sequences (`rng_*.golden.json`)
- Captured output sequences from the Mitchell-Moore RNG with specific seeds
- Used to verify `rng_mm` produces identical sequences to C `number_mm()`

### Damage Calculations (`damage_*.golden.json`)
- Captured damage values for specific combat scenarios
- Used to verify combat formula parity

### Skill Checks (`skill_*.golden.json`)
- Captured skill check results for specific inputs
- Used to verify skill success/failure thresholds match

### Saving Throws (`saves_*.golden.json`)
- Captured saving throw results
- Used to verify spell resistance calculations

## How to Update Golden Files

If you have access to the C ROM binary:

```bash
# Compile the C ROM with debug output
cd src && make

# Run with specific test scenarios and capture output
./rom -test-rng > ../tests/data/golden/rng_sequence.golden.json
```

## Verification

Run golden file tests with:
```bash
pytest tests/test_golden_reference.py -v
```
