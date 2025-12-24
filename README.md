# QuickMUD - A Modern ROM 2.4 Python Port

[![PyPI version](https://badge.fury.io/py/quickmud.svg)](https://badge.fury.io/py/quickmud)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-200%2F200%20passing-brightgreen.svg)](https://github.com/Nostoi/rom24-quickmud-python)

**QuickMUD is a modern Python port of the legendary ROM 2.4b6 MUD engine**, derived from ROM 2.4b6, Merc 2.1 and DikuMUD. This is a complete rewrite that brings the classic text-based MMORPG experience to modern Python with async networking, JSON world data, and comprehensive testing.

## 🎮 What is a MUD?

A "[Multi-User Dungeon](https://en.wikipedia.org/wiki/MUD)" (MUD) is a text-based MMORPG that runs over telnet. ROM is renowned for its fast-paced combat system and rich player interaction. ROM was also the foundation for [Carrion Fields](http://www.carrionfields.net/), one of the most acclaimed MUDs ever created.

## ✨ Key Features

- **🚀 Modern Python Architecture**: Fully async/await networking with SQLAlchemy ORM
- **📡 Multiple Connection Options**: Telnet, WebSocket, and SSH server support
- **🗺️ JSON World Loading**: Easy-to-edit world data with 352+ room resets
- **🏪 Complete Shop System**: Buy, sell, and list items with working economy
- **⚔️ ROM Combat System**: Classic ROM combat mechanics and skill system
- **👥 Social Features**: Say, tell, shout, and 100+ social interactions
- **🛠️ Admin Commands**: Teleport, spawn, ban management, and OLC building
- **📊 100% Test Coverage**: 200+ tests ensure reliability and stability

## 📦 Installation

### For Players & Server Operators

```bash
pip install quickmud
```

### Quick Start

Run a QuickMUD server:

**Telnet Server (port 5000):**
```bash
python3 -m mud socketserver
# or
mud socketserver
```

**WebSocket Server (port 8000):**
```bash
python3 -m mud websocketserver
# or
mud websocketserver
```

**SSH Server (port 2222):**
```bash
python3 -m mud sshserver
# or
mud sshserver
```

All servers provide:
- ✓ Game tick running at 4 Hz
- ✓ Time advancement
- ✓ Mob AI active

Connect to the server:

**Via Telnet:**
```bash
telnet localhost 5000
```

**Via SSH:**
```bash
ssh -p 2222 player@localhost
# Note: SSH username/password are ignored; MUD authentication happens after connection
```

## 🏗️ For Developers

## 🏗️ For Developers

### Development Installation

```bash
git clone https://github.com/Nostoi/rom24-quickmud-python.git
cd rom24-quickmud-python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[dev]
```

### Running Tests

```bash
pytest  # Run all 200 tests (should complete in ~16 seconds)
```

### Development Server

```bash
python -m mud  # Start development server
```

## 🎯 Project Status

- **Version**: 1.2.0 (Production Ready)
- **Test Coverage**: 200/200 tests passing (100% success rate)
- **Performance**: Full test suite completes in ~16 seconds
- **Compatibility**: Python 3.10+, cross-platform

## 🏛️ Architecture

- **Async Networking**: Modern async/await with Telnet, WebSocket, and SSH servers
- **SQLAlchemy ORM**: Robust database layer with migrations
- **JSON World Data**: Human-readable area files with full ROM compatibility
- **Modular Design**: Clean separation of concerns (commands, world, networking)
- **Type Safety**: Comprehensive type hints throughout codebase

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) and feel free to submit pull requests.

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration](docs/configuration.md)
- [World Building](docs/world-building.md)
- [API Reference](docs/api.md)

---

**Experience the classic MUD gameplay with modern Python reliability!** 🐍✨

For a fully reproducible environment, use the pinned requirements files generated with [pip-tools](https://github.com/jazzband/pip-tools):

```bash
pip install -r requirements-dev.txt
```

To update the pinned dependencies:

```bash
pip-compile requirements.in
pip-compile requirements-dev.in
```

Tools like [Poetry](https://python-poetry.org/) provide a similar workflow if you prefer that approach.

Run tests with:

```bash
pytest
```

### Publishing

To release a new version to PyPI:

1. Update the version in `pyproject.toml`.
2. Commit and tag:

```bash
git commit -am "release: v1.2.3"
git tag v1.2.3
git push origin main --tags
```

The GitHub Actions workflow will build and publish the package when the tag is pushed.

## Python Architecture

Game systems are implemented in Python modules:

- `mud/net` provides asynchronous telnet and websocket servers.
- `mud/game_loop.py` drives the tick-based update loop.
- `mud/commands` contains the command dispatcher and handlers.
- `mud/combat` and `mud/skills` implement combat and abilities.
- `mud/persistence.py` handles saving characters and world state.

Start the server with:

```sh
python -m mud runserver
```

## Docker Image

Build and run the Python server with Docker:

```bash
docker build -t quickmud .
docker run -p 5000:5000 quickmud
```

Or use docker-compose to rebuild on changes and mount the repository:

```bash
docker-compose up
```

Connect via:

```bash
telnet localhost 5000
```

## Data Models

The `mud/models` package defines dataclasses used by the game engine.
They mirror the JSON schemas in `schemas/` and supply enums and registries
for loading and manipulating area, room, object, and character data.

## Enhancement Opportunities

While the ROM 2.4 Python port provides a fully functional MUD with all major subsystems implemented, several areas offer opportunities for enhanced ROM parity and improved gameplay features. These partially implemented or simplified systems can be extended by future developers:

### Combat System Enhancements

- **Defense Stubs**: Basic defense calculations are implemented, but advanced ROM defense mechanics (dodge, parry, shield block) use simplified formulas that could be enhanced for full ROM parity
- **Special Attacks**: Core combat works, but special weapon attacks and combat maneuvers could be expanded
- **Damage Types**: Basic damage handling exists, but ROM's complex damage type interactions are simplified

### Skills and Spells System

- **Learning Percentages**: Skills can be learned and used, but the ROM skill improvement system with practice-based learning is partially implemented
- **Spell Components**: Basic spell casting works, but material component requirements and consumption are simplified
- **Skill Prerequisites**: Some skill dependencies and class restrictions could be more comprehensive

### Movement and Encumbrance

- **Weight Limits**: Basic encumbrance exists, but ROM's detailed weight penalties on movement and combat are simplified
- **Movement Lag**: Character movement works, but lag/wait state handling for movement restrictions could be enhanced
- **Terrain Effects**: Room sector types affect movement, but detailed terrain penalties are basic

### World Reset System

- **Reset Semantics**: Areas reset properly, but complex ROM reset conditions and dependencies are simplified
- **Population Limits**: Basic mob/object limits work, but advanced population control algorithms could be improved
- **Reset Timing**: Reset schedules function, but fine-grained timing controls are basic

### Economy and Shops

- **Shop Inventory**: Basic buying/selling works, but advanced shop inventory management and restocking is simplified
- **Economic Balance**: Price calculations exist, but ROM's complex economic balancing factors are basic
- **Barter System**: Simple transactions work, but advanced bartering mechanics could be enhanced

### Security and Authentication

- **Ban System**: Basic IP banning exists, but comprehensive ban management (subnet, time-based, etc.) is partial
- **Account Security**: Basic login security works, but advanced password policies and account protection could be enhanced
- **Admin Controls**: Core admin commands exist, but comprehensive administrative tools are basic

### Persistence and Data Integrity

- **Save Validation**: Character saving works, but comprehensive data validation and corruption detection is basic
- **Backup Systems**: Basic persistence exists, but automated backup and recovery systems could be enhanced
- **Data Migration**: Save/load works, but tools for data format migration and upgrades are minimal

### Communication Systems

- **Channel Management**: Basic channels work, but advanced channel administration and moderation tools are simplified
- **Tell System**: Private messaging works, but features like message history and blocking are basic
- **Emote System**: Basic emotes exist, but custom emote creation and management could be enhanced

### Builder Tools (OLC)

- **Online Creation**: Basic OLC exists, but comprehensive online building tools with validation are partial
- **Area Management**: Area editing works, but advanced area management and version control is basic
- **Builder Security**: Basic builder permissions exist, but comprehensive security and audit trails are simplified

### Performance and Monitoring

- **Metrics Collection**: Basic logging exists, but comprehensive performance monitoring and metrics are minimal
- **Resource Management**: Basic resource handling works, but advanced memory and CPU optimization could be enhanced
- **Diagnostics**: Error handling exists, but comprehensive diagnostic and debugging tools are basic

### Development Guidelines for Contributors

When enhancing these systems:

1. **ROM Parity First**: Always reference the original ROM 2.4 C sources in `src/` for canonical behavior
2. **Test Coverage**: Add comprehensive tests in `tests/` with golden files derived from ROM behavior
3. **Backward Compatibility**: Ensure changes don't break existing save files or area data
4. **Documentation**: Update relevant docs in `doc/` and inline code documentation
5. **Performance**: Consider the impact on the main game loop and player experience
6. **Configuration**: Make enhancements configurable where possible to support different playstyles

Each enhancement should maintain the MUD's core functionality while adding the specific ROM behaviors that make the game authentic to the original experience.
