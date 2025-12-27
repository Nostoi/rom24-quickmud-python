# ROM C Parity Documentation

This folder contains documentation tracking QuickMUD's parity with ROM 2.4b C codebase.

## 📚 Contents

### Archived Parity Documents
Located in [../../archive/parity/](../../archive/parity/):
- ROM_PARITY_FEATURE_TRACKER.md - Comprehensive feature tracking
- ROM_C_PARITY_MAPPING.md - C to Python mapping
- ROM_HEADER_FILES_AUDIT.md - ROM C header file analysis
- COMMAND_PARITY_AUDIT.md - Command implementation audit
- Various parity achievement reports

### Area Parity
Located in [../../archive/parity/](../../archive/parity/):
- AREA_PARITY_REPORT.md - Area file compatibility reports
- AREA_PARITY_BEST_PRACTICES.md - Best practices for area development

## 🎯 Purpose

These documents track:
- Feature-by-feature ROM C parity
- Implementation status and gaps
- Mapping between ROM C and QuickMUD Python
- Historical parity milestones

## 🔗 Related Resources

- **Scripts**: See [scripts/parity/](../../scripts/parity/) for parity analysis tools
- **Validation**: See [docs/validation/](../validation/) for validation documentation
- **Tests**: See [tests/](../../tests/) for parity verification tests

## ✅ Current Status

**Overall ROM C Parity**: ~83.1% function coverage
- **MobProgs**: 100% (31/31 commands, 16/16 triggers)
- **Combat**: 100% (all core mechanics implemented)
- **Movement**: 100% (basic + follower mechanics)
- **Commands**: 115/181 player commands (63.5%)

See [PROJECT_COMPLETION_STATUS.md](../../PROJECT_COMPLETION_STATUS.md) for detailed subsystem breakdown.
