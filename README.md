# QuickMUD - A Modern ROM 2.4 Python Port

[![Version](https://img.shields.io/badge/version-2.14.173-blue.svg)](https://github.com/Nostoi/rom24-quickmud-python)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-5894%20passing-brightgreen.svg)](https://github.com/Nostoi/rom24-quickmud-python)
[![ROM 2.4b Parity](https://img.shields.io/badge/ROM%202.4b%20Parity-parity%20beta-blue.svg)](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md)
[![ROM C Audit](https://img.shields.io/badge/ROM%20C%20Audit-43%2F43%20audited-success.svg)](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md)
[![Integration Tests](https://img.shields.io/badge/integration%20tests-1000%2B-brightgreen.svg)](tests/integration/)

**QuickMUD is a modern Python port of the legendary ROM 2.4b6 MUD engine**, derived from ROM 2.4b6, Merc 2.1 and DikuMUD. This is a complete rewrite that brings the classic text-based MMORPG experience to modern Python with async networking and JSON world data. The engine is **feature-complete and playable** — all 255 ROM commands, combat, spells, and world systems are implemented and green. Parity fidelity is in a **beta hardening phase**: high confidence on audited + test-covered surfaces, with a systematic methodology (per-file audits → cross-file invariants → differential harness) closing the remaining behavioral tail.

## 🎮 What is a MUD?

A "[Multi-User Dungeon](https://en.wikipedia.org/wiki/MUD)" (MUD) is a text-based MMORPG that runs over telnet. ROM is renowned for its fast-paced combat system and rich player interaction. ROM was also the foundation for [Carrion Fields](http://www.carrionfields.net/), one of the most acclaimed MUDs ever created.

## ✨ Key Features

- **🎯 Parity beta**: feature-complete and playable; all 255 ROM commands implemented; parity fidelity is systematically hardened surface-by-surface via per-file audits, cross-file invariant tests, and a live differential harness against the original C engine
- **🚀 Modern Python Architecture**: Fully async/await networking with SQLAlchemy ORM
- **📡 Multiple Connection Options**: Telnet, WebSocket, and SSH server support
- **🗺️ JSON World Loading**: Easy-to-edit world data with 352+ room resets
- **🏪 Complete Shop System**: Buy, sell, and list items with working economy
- **⚔️ ROM Combat System**: Classic ROM combat mechanics and skill system
- **👥 Social Features**: Say, tell, shout, and 100+ social interactions
- **🛠️ Admin Commands**: Teleport, spawn, ban management, and OLC building
- **📊 Comprehensive Testing**: 5,886 passing tests across unit, integration, and command-registry suites
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

**Stage: parity beta** — feature-complete and playable; parity fidelity is being
systematically hardened toward ROM-exact behavioral equivalence.

- **Version**: 2.14.173
- **Playability**: ✅ All 255 ROM commands implemented. Combat, spells, skills,
  movement, shops, mob programs, OLC building, and admin tools work and pass their
  tests. You can run a server and play today.
- **Parity confidence**: high on audited + test-covered surfaces; moderate on the
  uncovered tail (surfaces not yet reached by the differential harness). "Parity beta"
  means: the engine behaves like ROM on everything we've checked; there may be
  edge-case divergences we haven't checked yet. The standard stages (alpha/beta/GA)
  measure feature completeness — for a port the meaningful axis is *parity confidence*,
  not whether features exist.
- **ROM C Source Audit**: ✅ **43 / 43 files audited** — every applicable ROM C file
  has a completed audit document (3 intentional N/A: `recycle.c`, `mem.c`, `imc.c`).
  Per-file audits confirm *what was reviewed*; they don't by themselves certify
  bit-for-bit behavioral parity. See
  [`docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md).
- **Cross-file Invariants**: ✅ **25 / 25 enforced** — contracts that span modules
  (message delivery, prompt clamping, registry membership, same-room combat,
  death/reconnect ordering, RNG determinism, persistence coherence, room-flag survival)
  are each locked by a dedicated regression test. This layer catches the class of bug
  that per-file audits structurally miss.
- **Differential harness**: ✅ live — the original ROM 2.4b6 C engine and the Python
  port are run through identical scripted scenarios and their observable state is
  diffed. Any behavioral divergence surfaces mechanically rather than requiring a
  hand-written assertion. Coverage is growing; uncovered surfaces are the remaining
  parity-confidence gap.
- **Test Suite**: ✅ **5,807 passed, 4 skipped** (full `pytest` run, ~150s parallel).
  Unit, integration, command-registry, and differential-harness layers.
- **Active focus**: Class 11 dynamic differential widening — all deterministic
  OLC-created mobprog trigger types (`entry`, `greet`, `speech`, `act`, `bribe`,
  `give`, `fight`/`hpcnt`, `surr`, `kill`/`death`, `exit`, `exall`, `grall`) are
  now covered end-to-end through the MEdit → `spawn_mob` → runtime dispatch path.
  RNG-locked triggers (`random`, `delay`) are deferred pending seed-alignment work.
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

The parity verification stack has four layers — consult all four, not just the first:

| Layer | What it measures | Document |
|-------|-----------------|----------|
| Per-file audit | Every ROM C function has a Python equivalent | [ROM C subsystem tracker](docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md) |
| Cross-file invariants | Contracts spanning modules (message delivery, registry, RNG, identity, …) | [Cross-file invariants tracker](docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md) — 25 enforced |
| Divergence class roster | Structural C↔Python gaps (async, int-math, pointer identity, …) | [Divergence class roster](docs/parity/DIVERGENCE_CLASS_ROSTER.md) |
| Differential harness | C engine vs Python port, identical scenarios, state diffed | [Diff harness findings](tools/diff_harness/FINDINGS.md) |

- [ROM parity verification guide](docs/ROM_PARITY_VERIFICATION_GUIDE.md) — methodology, confidence tiers, when to use each layer
- [ROM 2.4b6 Parity Certification](docs/ROM_2.4B6_PARITY_CERTIFICATION.md) — historical document; predates cross-file invariants methodology

### User Documentation
- [User Guide](docs/USER_GUIDE.md) - Player and server operator documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrator and immortal documentation  
- [Builder Migration Guide](docs/BUILDER_MIGRATION_GUIDE.md) - For ROM builders transitioning to QuickMUD

### Developer Documentation
- [ROM Parity Feature Tracker](docs/parity/ROM_PARITY_FEATURE_TRACKER.md) - Feature-level parity backlog
- [Integration Test Coverage Tracker](docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md) - Coverage by gameplay system
- [ROM API Reference](docs/ROM_API_COMPLETION_REPORT.md) - ROM C-compatible public API
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

QuickMUD implements the full ROM 2.4b6 gameplay surface and has broad, documented
audit coverage of the original C codebase. It is **feature-complete and running on a
green test suite**, and is in an active **verification trust-rebuild phase** rather than
claiming finished, certified parity. "Implemented" below means the system exists and
passes its current tests; it does not assert bit-for-bit behavioral parity, which is
being hardened gap-by-gap (see **Project Status** above).

### ✅ Implemented Systems

- **Combat Engine**: Complete ROM combat mechanics with THAC0, damage calculations, and weapon special attacks
- **Skills & Spells**: All ROM skills and spells with correct formulas and targeting
- **Character System**: Classes, races, advancement, equipment, and encumbrance
- **World System**: Area loading, room resets, mob/object spawning, and JSON world data
- **Shop Economy**: Buy/sell with pricing formulas, shop restocking, and inventory management  
- **Communication**: Say, tell, shout, channels, and 100+ social interactions
- **Mob Programs**: Complete trigger system with conditional logic and ROM API; all deterministic OLC-created trigger types verified end-to-end
- **OLC Building**: Area/room/mob/object/help editors with save/load functionality
- **Admin Tools**: Teleport, spawn, ban management, wiznet, and debug commands
- **Networking**: Async telnet, WebSocket, and SSH servers with game tick integration

### 📈 Quality Metrics

- **Test Suite**: 5,886 passing, 4 skipped on the latest full run.
- **Audit Coverage**: every ROM 2.4b6 gameplay subsystem has a completed audit
  document (combat, skills, spells, movement, communication, world/db, save/load,
  mob programs, 255/255 commands). Audit completion means *reviewed and documented*,
  not *certified bug-free* — verification rigor is still being hardened.
- **ROM C Source Audit**: 43 of 43 applicable ROM files have an audit document, plus
  3 intentional N/A files. `handler.c` affects system now 100% complete (11/11
  functions, including `affect_join` — 2026-06-08).
- **Cross-file Invariants**: 25 of 25 enforced by dedicated regression tests.
- **Open gaps**: a small, tracked backlog of identified divergences is being closed
  one test-first commit at a time.

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
