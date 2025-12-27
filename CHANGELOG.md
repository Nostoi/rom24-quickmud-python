# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.0] - 2025-12-27

### Added

- **GitHub Release Creator Skill**: Comprehensive Claude Desktop skill for automated release management
  - Added `.claude/skills/github-release-creator/` with complete release automation tooling
  - Python script for automated release creation (`create_release.py`)
  - Shell scripts for release validation and creation
  - Changelog extraction utilities
  - Complete documentation with usage examples and workflows
  - GitHub CLI integration for professional release management
  - Support for semantic versioning, draft releases, and pre-releases

## [2.3.1] - 2025-12-27

### Added

- **Comprehensive Test Planning Documentation**:
  - Created `docs/validation/MOB_PARITY_TEST_PLAN.md` - Complete testing strategy for ROM 2.4b mob behaviors
    - 22 spec_fun behaviors (guards, dragons, casters, thieves)
    - 30+ ACT flag behaviors (aggressive, wimpy, scavenger, sentinel)
    - Damage modifiers (immunities, resistances, vulnerabilities)
    - Mob memory and tracking systems
    - Group assist mechanics
    - Wandering/movement AI
  - Created `docs/validation/PLAYER_PARITY_TEST_PLAN.md` - Complete testing strategy for player-specific behaviors
    - Information display commands (score, worth, whois)
    - Auto-settings (autoassist, autoloot, autogold, autosac, autosplit)
    - Conditions system (hunger, thirst, drunk, full)
    - Player flags and reputation (KILLER, THIEF)
    - Prompt customization
    - Title/description management
    - Trust/security levels
    - Player visibility states (AFK, wizinvis, incognito)
- **Claude Desktop Skill Support**:
  - Added `SKILL.md` - Comprehensive skill documentation for AI assistants
  - Added `.claude/skills/skill-creator/` - Anthropic's skill-creator tool
    - Skill validation scripts
    - Skill packaging utilities
    - Best practices documentation

### Changed

- **Test Organization**: Created clear roadmap for implementing 180+ behavioral tests
  - 6 major mob test areas (P0-P3 priority matrix)
  - 8 major player test areas (P0-P3 priority matrix)
  - 4-phase implementation roadmap for each
  - Complete test templates with ROM C references

### Documentation

- Documented 100+ specific test cases with ROM C source references
- Added implementation effort estimates and player impact assessments
- Created comprehensive testing guides for future development

## [2.3.0] - 2025-12-26

### Added

- **MobProg 100% ROM C Parity Achievement**: All 4 critical trigger hookups complete
  - `mp_give_trigger` integrated in do_give command
  - `mp_hprct_trigger` integrated in combat damage system
  - `mp_death_trigger` integrated in character death handling
  - `mp_speech_trigger` already integrated (verified)
- MobProg movement command validation in area file validator
- Comprehensive MobProg testing documentation (5 guides)
- Enhanced `validate_mobprogs.py` with movement command validation
- Organized validation and parity documentation structure

### Changed

- **Documentation Reorganization**: Created proper folder structure
  - Moved 10 documentation files to `docs/validation/` and `docs/parity/`
  - Moved 10 scripts to `scripts/validation/` and `scripts/parity/`
  - Moved 5 report files to appropriate `reports/` subfolders
  - Created 6 README files documenting folder contents
- Updated all cross-references in documentation to use new paths
- Enhanced validation scripts with movement command checks

### Fixed

- Integration test issues with Object creation and trigger signatures
- Syntax error in validate_mobprogs.py output formatting

## [2.2.1] - Previous Release

### Added

- Complete weapon special attacks system with ROM 2.4 parity (WEAPON_VAMPIRIC, WEAPON_POISON, WEAPON_FLAMING, WEAPON_FROST, WEAPON_SHOCKING)

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.3.0] - 2025-09-15

### Added

- Complete fighting state management with ROM 2.4 parity
- Character immortality protection following IS_IMMORTAL macro
- Level constants (MAX_LEVEL, LEVEL_IMMORTAL) matching ROM source

### Changed

### Deprecated

### Removed

### Fixed

- Character position initialization defaults to STANDING instead of DEAD
- Fighting state damage application and position updates
- Immortal character survival logic in combat system
- Combat defense order to match ROM 2.4 C source (shield_block → parry → dodge)

### Security

## [1.2.0] - 2025-09-15

### Added

- Complete telnet server with multi-user support
- Working shop system with buy/sell/list commands
- 132 skill system with handler stubs
- JSON-based world loading with 352 resets in Midgaard
- Admin commands (teleport, spawn, ban management)
- Communication system (say, tell, shout, socials)
- OLC building system for room editing
- pytest-timeout plugin for proper test timeouts

### Changed

- Achieved 100% test success rate (200/200 tests)
- Full test suite completes in ~16 seconds
- Modern async/await telnet server architecture
- SQLAlchemy ORM with migrations
- Comprehensive test coverage across all subsystems
- Memory efficient JSON area loading
- Optimized command processing pipeline
- Robust error handling throughout

### Fixed

- Character position initialization (STANDING vs DEAD)
- Hanging telnet tests resolved
- Enhanced error handling and null room safety
- Character creation now allows immediate command execution

## [0.1.1] - 2025-09-14

### Added

- Initial ROM 2.4 Python port foundation
- Basic world loading and character system
- Core command framework
- Database integration with SQLAlchemy

### Changed

- Migrated from legacy C codebase to pure Python
- JSON world data format for easier editing
- Modern Python packaging structure

## [0.1.0] - 2025-09-13

### Added

- Initial project structure
- Basic MUD framework
- ROM compatibility layer
- Core game loop implementation

[Unreleased]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.1...v1.2.0
[0.1.1]: https://github.com/Nostoi/rom24-quickmud-python/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Nostoi/rom24-quickmud-python/releases/tag/v0.1.0
