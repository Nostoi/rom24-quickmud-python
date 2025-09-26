# Integration Test Framework for ROM 2.4 Port Completion

## Framework Overview

This framework addresses the architectural gaps identified in the final 10-15% of ROM 2.4 to Python port completion. It focuses on cross-subsystem interactions, timing dependencies, and ROM parity validation.

## Test Categories

### 1. Cross-Subsystem Integration Tests

#### Reset-Movement Integration

- **Test**: Player moves while area reset is in progress
- **Validation**: LastObj/LastMob state remains consistent
- **Files**: `tests/integration/test_reset_movement.py`

#### Combat-Update Loop Integration

- **Test**: Combat rounds with wait/daze decrements on PULSE_VIOLENCE
- **Validation**: ROM tick cadence maintained
- **Files**: `tests/integration/test_combat_timing.py`

#### Board-Persistence Integration

- **Test**: Note composition survives save/load cycles
- **Validation**: Per-character board state and last-read tracking
- **Files**: `tests/integration/test_board_persistence.py`

### 2. Timing-Sensitive Scenario Tests

#### Game Loop Sequencing

- **Test**: Violence → Time → Weather → Reset pulse order
- **Validation**: Matches ROM update_handler sequence
- **Files**: `tests/integration/test_game_loop_sequence.py`

#### Movement Cascading

- **Test**: Leader movement with charmed followers
- **Validation**: Auto-look, visibility checks, follower standing
- **Files**: `tests/integration/test_movement_cascading.py`

### 3. ROM Parity Golden Tests

#### Reset State Tracking

- **Test**: ROM reset commands against C codebase behavior
- **Golden Data**: Extracted from src/db.c reset_room function
- **Files**: `tests/golden/test_reset_parity.py`

#### Command Interpretation

- **Test**: Abbreviation resolution matches ROM cmd_table order
- **Golden Data**: ROM str_prefix behavior
- **Files**: `tests/golden/test_command_parity.py`

## Implementation Strategy

### Directory Structure

```
tests/
├── integration/
│   ├── __init__.py
│   ├── test_reset_movement.py
│   ├── test_combat_timing.py
│   ├── test_board_persistence.py
│   ├── test_game_loop_sequence.py
│   └── test_movement_cascading.py
├── golden/
│   ├── __init__.py
│   ├── test_reset_parity.py
│   ├── test_command_parity.py
│   └── data/
│       ├── rom_reset_sequences.json
│       └── rom_command_abbreviations.json
└── performance/
    ├── __init__.py
    ├── test_reset_performance.py
    └── test_movement_performance.py
```

### Test Execution Strategy

#### Continuous Integration

- Run integration tests on every agent execution
- Golden tests run on subsystem completion validation
- Performance tests run weekly

#### Test Data Management

- Golden data extracted from C codebase analysis
- Integration scenarios based on actual ROM gameplay patterns
- Performance baselines from original ROM benchmarks

## Success Criteria

### Integration Test Coverage

- **Target**: 100% coverage of cross-subsystem interactions
- **Validation**: All 7 incomplete subsystems pass integration tests
- **Measurement**: pytest --cov reports for integration/ directory

### Parity Validation

- **Target**: 95% match with ROM C codebase behavior
- **Validation**: Golden tests pass with tolerance < 5%
- **Measurement**: Confidence scores above 0.85 for all subsystems

### Performance Compliance

- **Target**: Performance within 10% of ROM C performance
- **Validation**: Reset operations complete within ROM timing bounds
- **Measurement**: Benchmark tests against C baseline

## Key Implementation Files

### Core Integration Test Base

- `tests/integration/base.py`: Shared fixtures and utilities
- `tests/integration/rom_fixtures.py`: ROM-specific test data
- `tests/integration/timing_utils.py`: Pulse and timing helpers

### Golden Test Data Extraction

- `scripts/extract_rom_golden_data.py`: Extract C behavior patterns
- `scripts/validate_golden_data.py`: Verify extracted data accuracy
- `data/rom_baselines/`: Stored ROM behavior patterns

This framework directly addresses the task-completion disconnect by testing the **integration between completed individual tasks**, ensuring architectural coherence across the entire system.
