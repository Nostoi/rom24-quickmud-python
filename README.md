QuickMUD is derived from ROM 2.4b6, Merc 2.1 and DikuMUD
==============

## Introduction

QuickMUD / ROM is a "[multi-user dungeon](https://en.wikipedia.org/wiki/MUD)", a text-based MMORPG. ROM is well-known for its fast-paced and exciting combat system. It also happens to be the initial codebase for [Carrion Fields](http://www.carrionfields.net/), the greatest MUD of all time.
The legacy C engine has been fully replaced by a pure Python 3 codebase.
All game logic now lives in the `mud/` package and game data is loaded
from JSON files under `data/`.

## Installation

### Users

```bash
pip install quickmud
```

Run the server with:

```bash
mud runserver
```

### Developers

```bash
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
# or for a reproducible environment
pip install -r requirements-dev.txt
```

Run tests with:

```bash
pytest
```

## Building and publishing

Build a wheel and source distribution:

```bash
python -m build
```

Upload the artifacts to PyPI:

```bash
twine upload dist/*
```


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

See other READMEs in the repo for full historical information and licenses.

## Data Models

The `mud/models` package defines dataclasses used by the game engine.
They mirror the JSON schemas in `schemas/` and supply enums and registries
for loading and manipulating area, room, object, and character data.

