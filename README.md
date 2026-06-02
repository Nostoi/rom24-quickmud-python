# QuickMUD - A Modern ROM 2.4 Python Port

[![Version](https://img.shields.io/badge/version-2.12.55-blue.svg)](https://github.com/Nostoi/rom24-quickmud-python)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-5281%20passing-brightgreen.svg)](https://github.com/Nostoi/rom24-quickmud-python)
[![ROM 2.4b Parity](https://img.shields.io/badge/ROM%202.4b%20Parity-revalidation%20in%20progress-orange.svg)](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md)
[![ROM C Audit](https://img.shields.io/badge/ROM%20C%20Audit-40%2F40%20audited-success.svg)](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md)
[![Integration Tests](https://img.shields.io/badge/integration%20tests-1000%2B-brightgreen.svg)](tests/integration/)

**QuickMUD is a modern Python port of the legendary ROM 2.4b6 MUD engine**, derived from ROM 2.4b6, Merc 2.1 and DikuMUD. This is a complete rewrite that brings the classic text-based MMORPG experience to modern Python with async networking and JSON world data. The engine currently has a green suite and broad ROM audit coverage, but **parity trust rebuild / revalidation is in progress** after live bugs exposed gaps in observable-behavior verification.

## 🎮 What is a MUD?

A "[Multi-User Dungeon](https://en.wikipedia.org/wiki/MUD)" (MUD) is a text-based MMORPG that runs over telnet. ROM is renowned for its fast-paced combat system and rich player interaction. ROM was also the foundation for [Carrion Fields](http://www.carrionfields.net/), one of the most acclaimed MUDs ever created.

## ✨ Key Features

- **🎯 ROM parity trust rebuild in progress**: audit coverage is broad, but user-visible command/session surfaces are being revalidated against stricter ROM-exact tests
- **🚀 Modern Python Architecture**: Fully async/await networking with SQLAlchemy ORM
- **📡 Multiple Connection Options**: Telnet, WebSocket, and SSH server support
- **🗺️ JSON World Loading**: Easy-to-edit world data with 352+ room resets
- **🏪 Complete Shop System**: Buy, sell, and list items with working economy
- **⚔️ ROM Combat System**: Classic ROM combat mechanics and skill system
- **👥 Social Features**: Say, tell, shout, and 100+ social interactions
- **🛠️ Admin Commands**: Teleport, spawn, ban management, and OLC building
- **📊 Comprehensive Testing**: 5,256 passing tests across unit, integration, and command-registry suites
- **🔧 ROM C-Compatible API**: Public API wrappers for external tools and scripts (27 functions)

## 📦 Installation

### For Players & Server Operators

```bash
pip install quickmud
```

### Quick Start

Run a QuickMUD server:

**Telnet Server (port 5001):**
```bash
python3 -m mud socketserver
# or
mud socketserver
```

> **⚠️ macOS Users:** Port 5000 is used by macOS AirPlay Receiver (Monterey+). QuickMUD defaults to port 5001 to avoid conflicts. To use a different port: `python3 -m mud socketserver --port 4000`

**WebSocket Server (port 8000):**
```bash
python3 -m mud websocketserver
# or
mud websocketserver
```

> **WebSocket dependency note:** browser WebSocket clients require Uvicorn to
> have a supported WebSocket implementation available. If `/ws` upgrade requests
> fail, install one of:
> ```bash
> ./venv/bin/python -m pip install websockets
> # or
> ./venv/bin/python -m pip install 'uvicorn[standard]'
> ```

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
telnet localhost 5001
```

**Via SSH:**
```bash
ssh -p 2222 player@localhost
# Note: SSH username/password are ignored; MUD authentication happens after connection
```

## 🌐 Web Interface

QuickMUD includes a WebSocket server, but the browser interface lives in a
separate companion project so this engine repo can remain the canonical,
ROM-faithful Python backend.

Recommended layout:

```text
~/dev/projects/
  rom24-quickmud-python/
  quickmud-web-client/
```

The browser client should connect to:

```text
ws://127.0.0.1:8000/ws
```

### Browser Client Setup

From the companion `quickmud-web-client` repo:

```bash
cd ~/dev/projects/quickmud-web-client
npm install
npm run dev:all
```

That workflow:

- starts this QuickMUD engine's WebSocket server
- starts the frontend development server
- opens the browser client against the local `/ws` endpoint

The browser client is intended to follow the same ANSI, account login, account
creation, character selection, and in-game command flow as telnet/SSH rather
than using a browser-only shortcut login path.

### Companion Repo

The web interface is intended to live in a separate repository named
`quickmud-web-client`. Keep that project focused on browser UX, terminal
rendering, reconnect behavior, and login flow while leaving gameplay and ROM
parity logic in this backend repo.

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
pytest  # Run the full suite
pytest tests/integration/ -v  # Run the integration suite
```

### Development Server

```bash
python -m mud  # Start development server
```

## 🎯 Project Status

- **Version**: 2.12.55
- **ROM 2.4b Gameplay Parity**: ⚠️ **broadly audited, currently being revalidated** —
  combat, skills, spells, movement, communication, world/db, save/load, mob programs,
  and all 255 ROM commands are implemented, but some previously “verified” user-visible surfaces were only smoke-tested and are being rechecked with ROM-exact assertions.
- **ROM C Source Audit**: ✅ **100% audit-bound coverage** — 40 of 40 applicable ROM C files are audited, with
  3 additional ROM files intentionally N/A (`recycle.c`, `mem.c`, `imc.c`). See
  [`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md).
- **Cross-file Invariants**: ✅ **25/25 enforced** — message delivery, prompt clamping, registry membership,
  same-room combat, death/connection behavior, RNG determinism, persistence coherence, and room-flag
  survival (`.are`→JSON→runtime) are locked by dedicated tests.
- **Test Suite**: ✅ **5306 passed, 4 skipped**. Three layers — unit (`tests/test_*.py`),
  integration (`tests/integration/`), and command-registry (`test_all_commands.py`).
- **Active focus**: trust rebuild — replacing weak smoke assertions with ROM-exact output, boundary, and runtime-path tests on the highest-risk user-visible surfaces.
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

### Verification Status
- [ROM C subsystem tracker](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md) - canonical audit surface
- [ROM parity verification guide](docs/ROM_PARITY_VERIFICATION_GUIDE.md) - current verification standard
- [ROM 2.4b6 Parity Certification](ROM_2.4B6_PARITY_CERTIFICATION.md) - historical certification document; claims are being revalidated

### User Documentation
- [User Guide](docs/USER_GUIDE.md) - Player and server operator documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrator and immortal documentation  
- [Builder Migration Guide](docs/BUILDER_MIGRATION_GUIDE.md) - For ROM builders transitioning to QuickMUD

### Developer Documentation
- [ROM Parity Feature Tracker](docs/parity/ROM_PARITY_FEATURE_TRACKER.md) - Detailed parity status
- [ROM API Reference](ROM_API_COMPLETION_REPORT.md) - ROM C-compatible public API
- [Installation Guide](docs/installation.md)
- [Configuration](docs/configuration.md)
- [World Building](docs/world-building.md)
- [API Reference](docs/api.md)
- Companion browser client: `quickmud-web-client` (separate repo)

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
- `mud/account/` and `mud/db/` handle character persistence and account state.

Start the server with:

```sh
python -m mud runserver
```

## Docker Image

Build and run the Python server with Docker:

```bash
docker build -t quickmud .
docker run -p 5001:5001 quickmud
```

Or use docker-compose to rebuild on changes and mount the repository:

```bash
docker-compose up
```

Connect via:

```bash
telnet localhost 5001
```

## Data Models

The `mud/models` package defines dataclasses used by the game engine.
They mirror the JSON schemas in `schemas/` and supply enums and registries
for loading and manipulating area, room, object, and character data.

## Project Completeness

QuickMUD is a **production-ready ROM 2.4b MUD** with ✅ **100% behavioral parity** to the original ROM 2.4b6 C codebase:

### ✅ Fully Implemented Systems

- **Combat Engine**: Complete ROM combat mechanics with THAC0, damage calculations, and weapon special attacks
- **Skills & Spells**: All ROM skills and spells with correct formulas and targeting
- **Character System**: Classes, races, advancement, equipment, and encumbrance
- **World System**: Area loading, room resets, mob/object spawning, and JSON world data
- **Shop Economy**: Buy/sell with pricing formulas, shop restocking, and inventory management  
- **Communication**: Say, tell, shout, channels, and 100+ social interactions
- **Mob Programs**: Complete trigger system with conditional logic and ROM API
- **OLC Building**: Area/room/mob/object/help editors with save/load functionality
- **Admin Tools**: Teleport, spawn, ban management, wiznet, and debug commands
- **Networking**: Async telnet, WebSocket, and SSH servers with game tick integration

### 📈 Quality Metrics

- **Test Suite**: 4,934 passing, 4 skipped on the last full recertification.
- **Behavioral Parity**: 100% of ROM 2.4b6 gameplay subsystems audited (combat,
  skills, spells, movement, communication, world/db, save/load, mob programs,
  255/255 commands).
- **ROM C Source Audit**: 40 of 40 applicable ROM files audited, plus 3 intentional N/A files.
- **Cross-file Invariants**: 25 of 25 enforced by dedicated regression tests.

### 🔧 Advanced Features

For developers interested in extending QuickMUD beyond ROM 2.4b:

- **Modern Architecture**: Async/await networking, SQLAlchemy ORM, type hints
- **JSON World Data**: Human-readable area files (easier editing than ROM .are format)
- **Multiple Protocols**: Telnet, WebSocket, SSH connection options
- **ROM API Wrapper**: 27 public API functions for external tools and scripts
- **Comprehensive Testing**: Golden file tests derived from ROM C behavior
- **Documentation**: User guides, admin guides, and builder migration guides

### 📚 For Contributors

See [ROM_PARITY_FEATURE_TRACKER.md](docs/parity/ROM_PARITY_FEATURE_TRACKER.md) for detailed feature status and [AGENTS.md](AGENTS.md) for AI-assisted development workflows.

**Development Guidelines**:

1. **ROM Parity First**: Reference original ROM 2.4 C sources in `src/` for canonical behavior
2. **Test Coverage**: Add tests in `tests/` with golden files derived from ROM behavior  
3. **Backward Compatibility**: Don't break existing save files or area data
4. **Documentation**: Update relevant docs and inline code documentation
5. **Performance**: Consider impact on the main game loop and player experience

---

**Experience authentic ROM 2.4 gameplay with modern Python reliability!** 🐍✨
