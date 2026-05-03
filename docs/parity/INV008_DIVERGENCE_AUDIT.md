# INV-008 Divergence Audit: JSON vs DB Persistence Paths

**Date:** 2026-05-03  
**Scope:** `mud/persistence.py` (JSON path) vs `mud/account/account_manager.py` + `mud/db/models.py` (DB path)  
**Status:** Read-only audit — no code modified.

---

## 1. Field Inventory — JSON Path (`PlayerSave` dataclass, `mud/persistence.py`)

### `PlayerSave` (top-level player record)

- `name` (str) — character name
- `level` (int) — current level
- `race` (int) — race index (into race_table)
- `ch_class` (int) — class index
- `clan` (int) — clan id
- `sex` (int) — current sex (may differ from true_sex via polymorph)
- `trust` (int) — immortal trust level (override level for command access)
- `security` (int) — OLC security level (from PCData)
- `invis_level` (int) — wizinvis level (immortal visibility threshold)
- `incog_level` (int) — incognito level
- `hit` (int) — current HP
- `max_hit` (int) — current max HP (after affects)
- `mana` (int) — current mana
- `max_mana` (int) — current max mana
- `move` (int) — current movement points
- `max_move` (int) — current max movement
- `perm_hit` (int) — permanent base HP (from PCData.perm_hit, before affects)
- `perm_mana` (int) — permanent base mana
- `perm_move` (int) — permanent base movement
- `gold` (int) — gold coins carried
- `silver` (int) — silver coins carried
- `exp` (int) — experience points
- `practice` (int) — practice sessions available
- `train` (int) — training sessions available
- `played` (int) — total played time in seconds (accumulated + session delta)
- `lines` (int) — terminal lines (scroll setting)
- `logon` (int) — Unix timestamp of last logon (for session time calculation)
- `prompt` (str | None) — custom prompt string
- `prefix` (str | None) — command prefix string
- `title` (str | None) — character title (from PCData)
- `bamfin` (str | None) — immortal poofin message (from PCData)
- `bamfout` (str | None) — immortal poofout message (from PCData)
- `saving_throw` (int) — saving throw modifier
- `alignment` (int) — alignment (-1000 to +1000)
- `hitroll` (int) — hit roll bonus
- `damroll` (int) — damage roll bonus
- `wimpy` (int) — wimpy threshold (flee below this HP)
- `points` (int) — creation points spent (from PCData)
- `true_sex` (int) — biological sex (before polymorph)
- `last_level` (int) — level at last remort (from PCData)
- `position` (int) — current position (standing/sitting/sleeping/fighting etc.)
- `armor` (list[int], 4) — AC values: pierce/bash/slash/magic
- `perm_stat` (list[int], 5) — permanent stats: str/int/wis/dex/con
- `mod_stat` (list[int], 5) — stat modifiers from affects
- `conditions` (list[int], 4) — drunk/full/thirst/hunger values
- `act` (int) — act bitfield (PlayerFlag bits including COLOUR, AUTOLOOT, etc.)
- `affected_by` (int) — AffectFlag bitfield (sanctuary, flying, charm, etc.)
- `comm` (int) — comm channel bitfield (channels on/off)
- `wiznet` (int) — wiznet flags bitfield (immortal notification channels)
- `log_commands` (bool) — whether to log this char's commands (immortal tool)
- `newbie_help_seen` (bool) — whether the newbie help popup was shown
- `room_vnum` (int | None) — room to restore into (with limbo/temple fallback)
- `inventory` (list[ObjectSave]) — carried objects (see ObjectSave)
- `equipment` (dict[str, ObjectSave]) — worn objects keyed by slot name
- `aliases` (dict[str, str]) — command aliases
- `skills` (dict[str, int]) — skill name → learned percent (0–100)
- `groups` (list[str]) — known skill groups
- `board` (str) — last note board the character read
- `last_notes` (dict[str, float]) — per-board last-read timestamp
- `colours` (dict[str, list[int]]) — ANSI colour configuration (from PCData colour fields)
- `pet` (PetSave | None) — charmed/pet follower snapshot (see PetSave)
- `pfile_version` (int) — schema version for AffectFlag bit migration (0=legacy, 1=ROM-canonical)

Total: **51 fields** on PlayerSave itself.

### `ObjectSave` (inventory/equipment item)

- `vnum` (int) — object prototype vnum
- `wear_slot` (str | None) — slot name string (legacy key)
- `wear_loc` (int) — WearLocation enum value (canonical)
- `level` (int) — object level
- `timer` (int) — decay timer
- `cost` (int) — cost in silver
- `value` (list[int], 5) — item-type-specific values (weapon dice, container size, etc.)
- `extra_flags` (int) — extra flag bitfield (glowing, humming, nodrop, etc.)
- `condition` (int | str | None) — item condition
- `enchanted` (bool) — whether item has been enchanted (affects affect display)
- `item_type` (str | None) — item type string
- `contains` (list[ObjectSave]) — nested items (for containers)
- `affects` (list[ObjectAffectSave]) — item-specific affect modifiers

### `ObjectAffectSave` (affect on an object)

- `where` (int) — TO_OBJECT/TO_AFFECTS/TO_IMMUNE/etc.
- `type` (int) — skill slot number
- `level` (int) — affect level
- `duration` (int) — duration in ticks
- `location` (int) — APPLY_* location
- `modifier` (int) — stat modifier amount
- `bitvector` (int) — AffectFlag bits

### `PetSave` (charmed mob follower)

- `vnum` (int) — mob prototype vnum (ROM fwrite_pet)
- `name` (str) — pet name
- `short_descr` (str | None) — short description if custom
- `long_descr` (str | None) — long description if custom
- `description` (str | None) — full description if custom
- `race` (str | None) — race name if differs from prototype
- `clan` (str | None) — clan name if set
- `sex` (int) — sex
- `level` (int | None) — level if differs from prototype
- `hit` (int) — current HP
- `max_hit` (int) — max HP
- `mana` (int) — current mana
- `max_mana` (int) — max mana
- `move` (int) — current movement
- `max_move` (int) — max movement
- `gold` (int) — gold carried
- `silver` (int) — silver carried
- `exp` (int) — experience
- `act` (int | None) — act bitfield if differs from prototype
- `affected_by` (int | None) — affected_by bitfield if differs
- `comm` (int | None) — comm bitfield if set
- `position` (int) — position (FIGHTING converted to STANDING per ROM)
- `saving_throw` (int | None) — saving throw
- `alignment` (int | None) — alignment if differs from prototype
- `hitroll` (int | None) — hitroll if differs
- `damroll` (int | None) — damroll if differs from prototype damage bonus
- `armor` (list[int], 4) — AC values
- `perm_stat` (list[int], 5) — permanent stats
- `mod_stat` (list[int], 5) — stat modifiers
- `affects` (list[PetAffectSave]) — active affects

### `PetAffectSave` (affect on a pet)

- `skill_name` (str) — skill name (used to look up slot)
- `where` (int) — affect where
- `level` (int) — affect level
- `duration` (int) — duration in ticks
- `modifier` (int) — stat modifier
- `location` (int) — APPLY_* location
- `bitvector` (int) — AffectFlag bits

---

## 2. Field Inventory — DB Path (`Character` model, `mud/db/models.py`)

All columns on the `characters` table:

- `id` (Integer, PK) — surrogate database key, not a ROM C concept
- `name` (String, unique) — character name
- `password_hash` (String) — bcrypt/argon2 password hash (mirrors ROM PCData.pwd)
- `level` (Integer) — current level
- `hp` (Integer) — current HP (**note:** stored as `hp`, not `hit`; does not store current mana or move)
- `room_vnum` (Integer) — room to restore into
- `race` (Integer) — race index
- `ch_class` (Integer) — class index
- `sex` (Integer) — current sex
- `true_sex` (Integer) — biological sex
- `alignment` (Integer) — alignment
- `act` (Integer) — act flag bitfield
- `hometown_vnum` (Integer) — hometown room vnum (new-character default room)
- `perm_stats` (String) — JSON-encoded list of 5 permanent stat values
- `size` (Integer) — character size (race-derived but can be modified)
- `form` (Integer) — character form bitfield (race-derived)
- `parts` (Integer) — body parts bitfield (race-derived)
- `imm_flags` (Integer) — immunity flags
- `res_flags` (Integer) — resistance flags
- `vuln_flags` (Integer) — vulnerability flags
- `practice` (Integer) — practice sessions available
- `train` (Integer) — training sessions available
- `perm_hit` (Integer) — permanent base HP
- `perm_mana` (Integer) — permanent base mana
- `perm_move` (Integer) — permanent base movement
- `default_weapon_vnum` (Integer) — default weapon prototype vnum (creation choice)
- `newbie_help_seen` (Boolean) — newbie help popup seen flag
- `creation_points` (Integer) — creation points spent
- `creation_groups` (String) — JSON-encoded list of initial skill groups chosen at creation
- `creation_skills` (String) — JSON-encoded initial skill map (appears unused in save_character)

Plus the relationship:
- `objects` (list[ObjectInstance]) — via ObjectInstance FK (location string only, no item state)

Total: **29 columns** (30 counting `id`). The `ObjectInstance` table only stores `prototype_vnum` and a `location` string — no timer, value[], extra_flags, condition, enchanted, or item affects.

---

## 3. Divergence Table

| ROM C concept | JSON path | DB path | Notes |
|---|---|---|---|
| Character name | ✅ | ✅ | |
| Password hash | ❌ | ✅ | JSON path has no auth at all |
| Level | ✅ | ✅ | |
| Race | ✅ | ✅ | |
| Class (ch_class) | ✅ | ✅ | |
| Sex | ✅ | ✅ | |
| True sex | ✅ | ✅ | |
| Alignment | ✅ | ✅ | |
| Act bitfield | ✅ | ✅ | |
| Current HP | ✅ | ✅ (as `hp`) | |
| Current mana | ✅ | ❌ | DB never saves/restores current mana |
| Current move | ✅ | ❌ | DB never saves/restores current movement |
| Max HP | ✅ | ❌ | DB only has perm_hit; max_hit is not persisted |
| Max mana | ✅ | ❌ | DB only has perm_mana |
| Max move | ✅ | ❌ | DB only has perm_move |
| Perm HP (perm_hit) | ✅ | ✅ | |
| Perm mana (perm_mana) | ✅ | ✅ | |
| Perm move (perm_move) | ✅ | ✅ | |
| Gold | ✅ | ❌ | |
| Silver | ✅ | ❌ | |
| Experience (exp) | ✅ | ❌ | |
| Practice sessions | ✅ | ✅ | |
| Train sessions | ✅ | ✅ | |
| Played time (seconds) | ✅ | ❌ | |
| Logon timestamp | ✅ | ❌ | |
| Terminal lines | ✅ | ❌ | |
| Prompt string | ✅ | ❌ | |
| Command prefix | ✅ | ❌ | |
| Title (PCData.title) | ✅ | ❌ | |
| Bamfin / bamfout | ✅ | ❌ | |
| Saving throw | ✅ | ❌ | |
| Hitroll | ✅ | ❌ | |
| Damroll | ✅ | ❌ | |
| Wimpy threshold | ✅ | ❌ | |
| Creation points | ✅ | ✅ | |
| Position | ✅ | ❌ | |
| AC array (4 values) | ✅ | ❌ | |
| Perm stat array (5 values) | ✅ | ✅ (as JSON string) | |
| Mod stat array (5 values) | ✅ | ❌ | |
| Conditions (drunk/full/thirst/hunger) | ✅ | ❌ | |
| Affected_by bitfield | ✅ | ❌ | |
| Comm bitfield | ✅ | ❌ | |
| Wiznet flags | ✅ | ❌ | |
| Log commands flag | ✅ | ❌ | |
| Newbie help seen | ✅ | ✅ | |
| Trust level | ✅ | ❌ | |
| Security (OLC) | ✅ | ❌ | |
| Invis level | ✅ | ❌ | |
| Incog level | ✅ | ❌ | |
| Last level (remort) | ✅ | ❌ | |
| True sex (PCData) | ✅ | ✅ | |
| Room vnum (restore location) | ✅ | ✅ | |
| Hometown vnum | ❌ | ✅ | JSON path never persists this |
| Clan | ✅ | ❌ | |
| Size | ❌ | ✅ | JSON path never persists size |
| Form bitfield | ❌ | ✅ | JSON path never persists form |
| Parts bitfield | ❌ | ✅ | JSON path never persists parts |
| Imm flags | ❌ | ✅ | |
| Res flags | ❌ | ✅ | |
| Vuln flags | ❌ | ✅ | |
| Inventory (full item state) | ✅ | ⚠️ partial | DB stores prototype_vnum + location only; no timer, value[], extra_flags, condition, enchanted, or item affects |
| Equipment (full item state) | ✅ | ⚠️ partial | Same: no item state beyond prototype_vnum |
| Object affects (enchants etc.) | ✅ | ❌ | |
| Container contents (nested items) | ✅ | ❌ | |
| Character affects (spells on char) | ✅ | ❌ | |
| Skills (learned percent per skill) | ✅ | ❌ (creation_skills exists but unused in save) | Only `creation_skills` column exists; not populated by save_character |
| Skill groups | ✅ | ⚠️ partial | `creation_groups` saves initial groups chosen at char creation; runtime `group_known` not updated |
| Aliases | ✅ | ❌ | |
| Note board / last read timestamps | ✅ | ❌ | |
| Colour table (ANSI config) | ✅ | ❌ | |
| Pet (charmed follower) | ✅ | ❌ | |
| Default weapon vnum | ❌ | ✅ | |
| Password hash | ❌ | ✅ | |
| Pfile schema version | ✅ | ❌ | |

---

## 4. Caller Surface

### Production call sites — `mud/account/account_manager.py` (`load_character` / `save_character`)

| File | Line | Function/context |
|---|---|---|
| `mud/net/connection.py` | 1535 | `load_character(chosen_name)` — on login, after password accepted |
| `mud/net/connection.py` | 1625 | `load_character(...)` — on character re-entry after disconnect |
| `mud/net/connection.py` | 1885 | `load_character(...)` — on character re-entry (second path) |
| `mud/net/connection.py` | 741 | `save_character(char)` — on character deletion / quit |
| `mud/net/connection.py` | 1788 | `save_character(char)` — on logout |
| `mud/net/connection.py` | 2036 | `save_character(char)` — on logout (second path) |
| `mud/combat/engine.py` | 1067 | `save_character(attacker)` — called on PC death (`raw_kill`) |
| `mud/advancement.py` | 229 | `save_character(char)` — called on level-up |
| `mud/commands/character.py` | 75 | `save_character(ch)` — called by `do_password` after password change |
| `mud/commands/session.py` | 30 | `save_character(ch)` — called by `do_save` (player-initiated) |
| `mud/commands/session.py` | 52 | `save_character(ch)` — called by `do_quit` |
| `mud/commands/admin_commands.py` | 3 | imported as `save_player_file` — immortal admin save |
| `mud/game_loop.py` | 516 | `save_character(character)` — periodic autosave tick |
| `mud/game_loop.py` | 532 | `save_character(character)` — periodic autosave tick (second path) |
| `mud/game_loop.py` | 761 | `save_character(candidate)` — idle timeout save |

### Test call sites — `mud/account/account_manager.py` (DB path)

| File | Lines | Context |
|---|---|---|
| `tests/integration/test_character_creation_runtime.py` | 14, 64, 244–254 | Full creation+load cycle; DB round-trip test |
| `tests/test_inventory_persistence.py` | 1, 15, 22, 24 | DB inventory save/load round-trip |
| `tests/test_account_auth.py` | 16–17, 1161 | Auth flow; load by name |
| `tests/test_advancement.py` | 174 | Monkeypatched save on level-up |
| `tests/test_connection_motd.py` | 100, 104 | Monkeypatched save on MOTD |
| `tests/test_game_loop.py` | 461, 484 | Monkeypatched autosave |
| `tests/test_networking_telnet.py` | 134, 165 | Monkeypatched load in connection tests |

### Call sites — `mud/persistence.py` (JSON path)

All production call sites import from `mud.account.account_manager`. The JSON path is called directly **only from tests** and internally (`save_world` / `load_world` which are not called by any production module).

| File | Lines | Context |
|---|---|---|
| `tests/integration/test_pet_persistence.py` | 84, 87, 170, 173, 237, 240, 286, 289, 333, 336, 374, 448, 451, 501, 504 | Full pet save/load round-trips; tests the JSON path |
| `tests/integration/test_save_load_parity.py` | 136, 139, 195–196, 257–258, 300–301, 359, 385, 394, 430, 433, 461, 475, 526–527 | JSON path parity tests |
| `tests/integration/test_tables_001_affect_migration.py` | 72, 88, 116, 137, 151, 165, 167, 176 | AffectFlag migration tests (JSON path only) |
| `tests/test_persistence.py` | 19, 21, 35–36, 104, 106, 140, 142, 157, 159, 178, 180, 198, 200, 219, 221 | JSON path unit tests |
| `tests/test_player_save_format.py` | 139–172, 199–202, 207–441, 626–712, 748–750 | JSON format-level tests |
| `tests/test_wiznet.py` | 180–181 | wiznet flag round-trip (JSON path) |
| `tests/test_affects.py` | 447–448 | affect bitfield round-trip (JSON path) |
| `tests/test_boards.py` | 290, 300 | board/last_notes round-trip (JSON path) |
| `tests/test_commands.py` | 190, 192 | alias persistence (JSON path) |
| `tests/test_logging_admin.py` | 142, 145 | log_commands round-trip (JSON path) |

---

## 5. Recommendation

### Paragraph 1 — Field parity comparison

The **JSON path** (`mud/persistence.py`) persists **51 top-level player fields** plus full nested state for inventory objects (13 fields each including timer, value[], extra_flags, condition, enchanted, affects), equipment, container nesting, character affects, pet state (30+ fields), skills (full learned map), aliases, colour table, wiznet flags, comm flags, affected_by, conditions (hunger/thirst), note board timestamps, and pfile schema versioning. The **DB path** (`mud/db/models.py` + `account_manager.py`) persists **29 columns**, of which several are creation-time metadata rarely updated (creation_groups, default_weapon_vnum, hometown_vnum, size, form, parts, imm/res/vuln_flags). Counting fields that meaningfully represent a character's **runtime state**, the DB path persists roughly 18 live-game fields versus the JSON path's 51+. Production behaviors lost today because the DB path is live: current mana and movement are not saved (restored from perm values on every login); exp, gold, silver are not saved (reset to 0 on crash/restart); hitroll, damroll, saving throw, AC, wimpy, position, mod_stat, comm, affected_by, wiznet, and conditions are not saved; the full skill learned-percent map is not saved post-creation; aliases, colour config, prompt, title, bamfin/bamfout, played time, and logon timestamp are not saved; pet companions are lost on logout; item timer/value/condition/enchant/affects on inventory and equipment are lost; container contents are lost.

### Paragraph 2 — Recommended end-state

Adopt **(c) the hybrid path**: keep the DB row for authentication and account identity (password_hash, name, id), but write and read **all gameplay state** through the JSON file at the same lifecycle points currently used by the DB path. Concretely: on login, `net/connection.py` calls the JSON `load_character` after the DB auth check passes (the DB row is only consulted for password verification); on logout/quit/death/autosave, the JSON `save_character` is called instead of the DB one. The `mud/account/account_manager.py` module becomes a thin auth+dispatch layer: `authenticate(name, password)` hits the DB; `load_character` delegates to `persistence.load_character`; `save_character` delegates to `persistence.save_character`. This requires: (1) adding `password_hash` persistence to the JSON path (one field on `PlayerSave`; already present in `PCData.pwd` at runtime), (2) ensuring the DB row is created/updated only for auth fields (name, password_hash) and never for gameplay fields, (3) migrating existing DB-only characters to JSON format before cutover (a one-time script: read DB row, write JSON file with the fields that exist, accept that missing fields restore from ROM defaults). The JSON path is already the more complete and more tested implementation — it has 15+ integration test files exercising it directly, covers AffectFlag migration, pet persistence, condition arrays, colour config, and affect bitvectors that the DB path has never touched. The deprecation comment at the top of `persistence.py` reflects a decision that predates this audit and is contradicted by the actual field coverage. Reversing that decision by making the JSON path primary (under a thin DB auth shim) is the lowest-risk path to full ROM parity without a large schema migration.
