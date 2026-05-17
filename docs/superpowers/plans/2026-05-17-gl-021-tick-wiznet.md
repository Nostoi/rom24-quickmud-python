# GL-021 Tick Wiznet Parity Plan

**Goal:** Close `GL-021` by verifying and, if needed, implementing ROM `src/update.c:update_handler` point-pulse `wiznet("TICK!")` behavior in Python `mud/game_loop.py`.

**ROM source of truth:** `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/src/update.c:1183-1191`

**Python target:** `/Users/markjedrzejczyk/dev/projects/rom24-quickmud-python/mud/game_loop.py:1349`

**Impact analysis:** GitNexus `impact(game_tick)` after reindex reports `LOW` risk, no indexed upstream breakage.

## Steps

- [ ] Add a focused regression test for point-pulse ordering:
  - on point pulse, emit `wiznet("TICK!", ..., WIZ_TICKS, ...)`
  - emit before `time_tick` / `weather_tick` / `char_update` / `obj_update`
- [ ] Implement the minimal ROM-faithful change in `mud/game_loop.py`
- [ ] Run the focused point-pulse and wiznet slices
- [ ] Update parity docs and session docs to remove the deferment
- [ ] Re-run an adjacent broader game-loop slice if the focused tests pass

## Verification commands

```bash
./venv/bin/python -m pytest -q tests/test_game_loop.py -k 'tick_wiznet or regen_tick'
./venv/bin/python -m pytest -q tests/test_wiznet.py -k 'ticks or requires_specific_flag'
./venv/bin/python -m pytest -q tests/test_game_loop.py tests/integration/test_update_c_parity.py tests/test_wiznet.py -k 'tick or wiznet or regen'
```
