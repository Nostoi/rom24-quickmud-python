# Python Architecture

QuickMUD now runs entirely on Python. The legacy C engine has been
replaced by modules under the `mud/` package that operate on JSON
data stored in `data/` and validated by schemas in `schemas/`.

Key components include:

- **Data models** – `mud/models` dataclasses mirror the JSON schemas and
  represent rooms, objects, characters, areas and more.
- **Loaders** – `mud/loaders` reads JSON into runtime models.
- **Networking** – `mud/net` provides the asynchronous telnet server and
  optional websocket server.
- **Game loop** – `mud/game_loop.py` drives ticks for combat, weather and
  area resets.
- **Commands and skills** – `mud/commands`, `mud/combat` and `mud/skills`
  implement player actions and ability handling.
- **Persistence** – `mud/persistence.py` saves player and world state to
  JSON files with atomic writes.

Start the game with:

```sh
python -m mud runserver
```
