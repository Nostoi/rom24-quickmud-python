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
- **📡 Multi-User Telnet Server**: Handle hundreds of concurrent players
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

```bash
mud runserver
```

The server will start on `localhost:4000`. Connect with any telnet client:

```bash
telnet localhost 4000
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

- **Async Networking**: Modern async/await telnet server
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
