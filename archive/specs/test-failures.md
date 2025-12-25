# Failed Github Action Tests

## Test (3.10)

### Lint with Ruff
Run # Check if ruff is available and run it
  # Check if ruff is available and run it
  if command -v ruff &> /dev/null; then
    ruff check .
  else
    echo "Ruff not available, skipping linting"
  fi
  shell: /usr/bin/bash -e {0}
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.10.18/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.10.18/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.18/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.18/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.18/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.10.18/x64/lib
F401 `.json_area_loader.load_all_areas_from_json` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
 --> mud/loaders/__init__.py:2:31
  |
1 | from .area_loader import load_area_file
2 | from .json_area_loader import load_all_areas_from_json
  |                               ^^^^^^^^^^^^^^^^^^^^^^^^
3 | from pathlib import Path
  |
help: Use an explicit re-export: `load_all_areas_from_json as load_all_areas_from_json`

F401 [*] `mud.models.area_json.AreaJson` imported but unused
 --> mud/loaders/json_area_loader.py:7:34
  |
5 | from typing import Dict, Any
6 |
7 | from mud.models.area_json import AreaJson
  |                                  ^^^^^^^^
8 | from mud.models.json_io import load_dataclass
9 | from mud.models.area import Area
  |
help: Remove unused import: `mud.models.area_json.AreaJson`

F401 [*] `mud.models.json_io.load_dataclass` imported but unused
  --> mud/loaders/json_area_loader.py:8:32
   |
 7 | from mud.models.area_json import AreaJson
 8 | from mud.models.json_io import load_dataclass
   |                                ^^^^^^^^^^^^^^
 9 | from mud.models.area import Area
10 | from mud.models.room import Room, Exit, ExtraDescr
   |
help: Remove unused import: `mud.models.json_io.load_dataclass`

F401 [*] `..models.obj.Affect` imported but unused
65 |     area.resets = []
66 |     office.contents.clear()
   |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:26
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                          ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:49
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                 ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:71
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                                       ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:115:23
    |
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
115 |     area = office.area; assert area is not None
    |                       ^
116 |     area.resets = []
117 |     office.contents.clear()
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:26
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                          ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:49
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                 ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:71
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                                       ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:134:21
    |
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
134 |     area = room.area; assert area is not None
    |                     ^
135 |     # Narrow to controlled resets only
136 |     area.resets = []
    |

F401 [*] `mud.world.create_test_character` imported but unused
 --> tests/test_world.py:2:41
  |
1 | import pytest
2 | from mud.world import initialize_world, create_test_character, move_character, look
  |                                         ^^^^^^^^^^^^^^^^^^^^^
3 | from mud.registry import room_registry, area_registry
4 | from mud.loaders import load_all_areas
  |
help: Remove unused import: `mud.world.create_test_character`

Found 104 errors.
[*] 23 fixable with the `--fix` option (7 hidden fixes can be enabled with the `--unsafe-fixes` option).
Error: Process completed with exit code 1.

### Test (3.11)
Run # Check if ruff is available and run it
F401 `.json_area_loader.load_all_areas_from_json` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
 --> mud/loaders/__init__.py:2:31
  |
1 | from .area_loader import load_area_file
2 | from .json_area_loader import load_all_areas_from_json
  |                               ^^^^^^^^^^^^^^^^^^^^^^^^
3 | from pathlib import Path
  |
help: Use an explicit re-export: `load_all_areas_from_json as load_all_areas_from_json`

F401 [*] `mud.models.area_json.AreaJson` imported but unused
 --> mud/loaders/json_area_loader.py:7:34
  |
5 | from typing import Dict, Any
6 |
7 | from mud.models.area_json import AreaJson
  |                                  ^^^^^^^^
8 | from mud.models.json_io import load_dataclass
9 | from mud.models.area import Area
  |
help: Remove unused import: `mud.models.area_json.AreaJson`

F401 [*] `mud.models.json_io.load_dataclass` imported but unused
  --> mud/loaders/json_area_loader.py:8:32
   |
 7 | from mud.models.area_json import AreaJson
 8 | from mud.models.json_io import load_dataclass
   |                                ^^^^^^^^^^^^^^
 9 | from mud.models.area import Area
10 | from mud.models.room import Room, Exit, ExtraDescr
   |
help: Remove unused import: `mud.models.json_io.load_dataclass`

F401 [*] `..models.obj.Affect` imported but unused
65 |     area.resets = []
66 |     office.contents.clear()
   |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:26
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                          ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:49
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                 ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:71
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                                       ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:115:23
    |
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
115 |     area = office.area; assert area is not None
    |                       ^
116 |     area.resets = []
117 |     office.contents.clear()
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:26
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                          ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:49
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                 ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:71
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                                       ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:134:21
    |
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
134 |     area = room.area; assert area is not None
    |                     ^
135 |     # Narrow to controlled resets only
136 |     area.resets = []
    |

F401 [*] `mud.world.create_test_character` imported but unused
 --> tests/test_world.py:2:41
  |
1 | import pytest
2 | from mud.world import initialize_world, create_test_character, move_character, look
  |                                         ^^^^^^^^^^^^^^^^^^^^^
3 | from mud.registry import room_registry, area_registry
4 | from mud.loaders import load_all_areas
  |
help: Remove unused import: `mud.world.create_test_character`

Found 104 errors.
[*] 23 fixable with the `--fix` option (7 hidden fixes can be enabled with the `--unsafe-fixes` option).
Error: Process completed with exit code 1.

## Test (3.12)
### Lint with Ruff
Run # Check if ruff is available and run it
  # Check if ruff is available and run it
  if command -v ruff &> /dev/null; then
    ruff check .
  else
    echo "Ruff not available, skipping linting"
  fi
  shell: /usr/bin/bash -e {0}
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.12.11/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.11/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.11/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.11/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.11/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.11/x64/lib
F401 `.json_area_loader.load_all_areas_from_json` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
 --> mud/loaders/__init__.py:2:31
  |
1 | from .area_loader import load_area_file
2 | from .json_area_loader import load_all_areas_from_json
  |                               ^^^^^^^^^^^^^^^^^^^^^^^^
3 | from pathlib import Path
  |
help: Use an explicit re-export: `load_all_areas_from_json as load_all_areas_from_json`

F401 [*] `mud.models.area_json.AreaJson` imported but unused
 --> mud/loaders/json_area_loader.py:7:34
  |
5 | from typing import Dict, Any
6 |
7 | from mud.models.area_json import AreaJson
  |                                  ^^^^^^^^
8 | from mud.models.json_io import load_dataclass
9 | from mud.models.area import Area
  |
help: Remove unused import: `mud.models.area_json.AreaJson`

F401 [*] `mud.models.json_io.load_dataclass` imported but unused
  --> mud/loaders/json_area_loader.py:8:32
   |
 7 | from mud.models.area_json import AreaJson
 8 | from mud.models.json_io import load_dataclass
   |                                ^^^^^^^^^^^^^^
 9 | from mud.models.area import Area
10 | from mud.models.room import Room, Exit, ExtraDescr
   |
help: Remove unused import: `mud.models.json_io.load_dataclass`

F401 [*] `..models.obj.Affect` imported but unused
65 |     area.resets = []
66 |     office.contents.clear()
   |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:26
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                          ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:49
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                 ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:112:71
    |
110 |     # Build a controlled sequence: two desks (3130) into Captain's Office (3142),
111 |     # then put a key (3123) into each using P after each O.
112 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                                       ^
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:115:23
    |
113 |     initialize_world('area/area.lst')
114 |     office = room_registry[3142]
115 |     area = office.area; assert area is not None
    |                       ^
116 |     area.resets = []
117 |     office.contents.clear()
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:26
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                          ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:49
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                 ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:131:71
    |
130 | def test_reset_GE_limits_and_shopkeeper_inventory_flag():
131 |     room_registry.clear(); area_registry.clear(); mob_registry.clear(); obj_registry.clear()
    |                                                                       ^
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
    |

E702 Multiple statements on one line (semicolon)
   --> tests/test_spawning.py:134:21
    |
132 |     initialize_world('area/area.lst')
133 |     room = room_registry[3001]
134 |     area = room.area; assert area is not None
    |                     ^
135 |     # Narrow to controlled resets only
136 |     area.resets = []
    |

F401 [*] `mud.world.create_test_character` imported but unused
 --> tests/test_world.py:2:41
  |
1 | import pytest
2 | from mud.world import initialize_world, create_test_character, move_character, look
  |                                         ^^^^^^^^^^^^^^^^^^^^^
3 | from mud.registry import room_registry, area_registry
4 | from mud.loaders import load_all_areas
  |
help: Remove unused import: `mud.world.create_test_character`

Found 104 errors.
[*] 23 fixable with the `--fix` option (7 hidden fixes can be enabled with the `--unsafe-fixes` option).
Error: Process completed with exit code 1.

### Test with PyTest
Run pytest --tb=short --timeout=30
  pytest --tb=short --timeout=30
  shell: /usr/bin/bash -e {0}
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.12.11/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.11/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.11/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.11/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.11/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.11/x64/lib
============================= test session starts ==============================
platform linux -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
rootdir: /home/runner/work/rom24-quickmud-python/rom24-quickmud-python
configfile: pyproject.toml
plugins: timeout-2.4.0, anyio-4.10.0, cov-7.0.0
timeout: 30.0s
timeout method: signal
timeout func_only: False
collected 200 items

tests/test_account_auth.py ....                                          [  2%]
tests/test_admin_commands.py ..                                          [  3%]
tests/test_advancement.py ....                                           [  5%]
tests/test_affects.py .............                                      [ 11%]
tests/test_agent_interface.py ..                                         [ 12%]
tests/test_ansi.py .                                                     [ 13%]
tests/test_are_conversion.py ..                                          [ 14%]
tests/test_area_counts.py .                                              [ 14%]
tests/test_area_exits.py .                                               [ 15%]
tests/test_area_loader.py ..                                             [ 16%]
tests/test_area_specials.py ..                                           [ 17%]
tests/test_bans.py ...                                                   [ 18%]
tests/test_boards.py .                                                   [ 19%]
tests/test_building.py .                                                 [ 19%]
tests/test_combat.py ........                                            [ 23%]
tests/test_combat_defenses_prob.py ...                                   [ 25%]
tests/test_combat_thac0.py ..                                            [ 26%]
tests/test_combat_thac0_engine.py .                                      [ 26%]
tests/test_command_abbrev.py ..                                          [ 27%]
tests/test_commands.py .........                                         [ 32%]
tests/test_communication.py ...                                          [ 33%]
tests/test_convert_are_to_json_cli.py .                                  [ 34%]
tests/test_db_seed.py .                                                  [ 34%]
tests/test_defense_flags.py ..                                           [ 35%]
tests/test_encumbrance.py ..                                             [ 36%]
tests/test_enter_portal.py ..                                            [ 37%]
tests/test_game_loop.py ...                                              [ 39%]
tests/test_game_loop_order.py .                                          [ 39%]
tests/test_game_loop_wait_daze.py .                                      [ 40%]
tests/test_hash_utils.py .                                               [ 40%]
tests/test_healer.py ...                                                 [ 42%]
tests/test_help_conversion.py .                                          [ 42%]
tests/test_help_system.py ..                                             [ 43%]
tests/test_imc.py .....                                                  [ 46%]
tests/test_inventory_persistence.py .                                    [ 46%]
tests/test_json_io.py ....                                               [ 48%]
tests/test_json_model_instantiation.py .........                         [ 53%]
tests/test_load_midgaard.py .                                            [ 53%]
tests/test_logging_admin.py .                                            [ 54%]
tests/test_logging_rotation.py ....                                      [ 56%]
tests/test_mobprog.py ..                                                 [ 57%]
tests/test_movement_costs.py ....                                        [ 59%]
tests/test_persistence.py ...                                            [ 60%]
tests/test_player_save_format.py .....                                   [ 63%]
tests/test_reset_levels.py .                                             [ 63%]
tests/test_rng_and_ccompat.py ..                                         [ 64%]
tests/test_rng_dice.py ..                                                [ 65%]
tests/test_runtime_models.py ..........                                  [ 70%]
tests/test_schema_validation.py ...........                              [ 76%]
tests/test_scripted_session.py .                                         [ 76%]
tests/test_shop_conversion.py ..                                         [ 77%]
tests/test_shops.py ....                                                 [ 79%]
tests/test_skill_conversion.py .                                         [ 80%]
tests/test_skill_registry.py .                                           [ 80%]
tests/test_skills.py ..                                                  [ 81%]
tests/test_skills_learned.py .                                           [ 82%]
tests/test_social_conversion.py ..                                       [ 83%]
tests/test_social_placeholders.py ..                                     [ 84%]
tests/test_socials.py ..                                                 [ 85%]
tests/test_spawning.py .......                                           [ 88%]
tests/test_spec_funs.py ....                                             [ 90%]
tests/test_spec_funs_extra.py ..                                         [ 91%]
tests/test_specials_loader_ext.py .                                      [ 92%]
tests/test_telnet_server.py ..                                           [ 93%]
tests/test_time_daynight.py ....                                         [ 95%]
tests/test_time_persistence.py .                                         [ 95%]
tests/test_wiznet.py ......                                              [ 98%]
tests/test_world.py ...                                                  [100%]

=============================== warnings summary ===============================
tests/test_admin_commands.py: 7 warnings
tests/test_building.py: 2 warnings
tests/test_logging_admin.py: 1 warning
tests/test_logging_rotation.py: 2 warnings
tests/test_wiznet.py: 1 warning
  /home/runner/work/rom24-quickmud-python/rom24-quickmud-python/mud/logging/admin.py:14: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    line = f"{datetime.utcnow().isoformat()}Z\t{actor}\t{command}\t{args}\n"

tests/test_logging_rotation.py::test_rotate_on_midnight_tick
  /home/runner/work/rom24-quickmud-python/rom24-quickmud-python/mud/logging/admin.py:30: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    dt = today or datetime.utcnow()

tests/test_logging_rotation.py::test_rotate_on_midnight_tick
  /home/runner/work/rom24-quickmud-python/rom24-quickmud-python/tests/test_logging_rotation.py:50: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    today = datetime.utcnow().strftime('%Y%m%d')

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 200 passed, 15 warnings in 21.64s =======================