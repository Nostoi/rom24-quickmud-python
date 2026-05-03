# INV-008 Reversal Audit — DB-Canonical Migration

**Date:** 2026-05-03  
**Author:** Claude Code (audit-only pass; no code changes)  
**Context:** INV-008 (closed in v2.7.6) consolidated persistence around the JSON pfile with the DB row demoted to auth-only. This audit documents everything required to *reverse* that direction: make `mud/db/models.py:Character` canonical for ALL player state, and delete the JSON pfile load/save path.

> **Scope of this document:** This is an audit document only. It produces no code changes. Its sole consumer is an implementation subagent that will execute the migration without re-reading source.

---

## 1. Field-by-Field Map: PlayerSave → DB Character Columns

`mud/persistence.py:285-358` defines `PlayerSave`. The `save_character` function (`mud/persistence.py:883-1034`) shows exactly what is round-tripped. Each field is mapped below.

Legend:
- **DB column** — column exists in `mud/db/models.py:Character` (lines 91-132)
- **MISSING** — no DB column; new SQLAlchemy column required
- ROM C reference from `src/save.c` where parity-sensitive

| # | Field | Python Type | DB Column? | DB Name / Type | ROM C Reference | Notes |
|---|-------|------------|------------|----------------|-----------------|-------|
| 1 | `name` | `str` | ✅ | `name: String` | `src/save.c fwrite_char Name` | Primary key for lookup |
| 2 | `password_hash` | `str` | ✅ | `password_hash: String` | `src/save.c fwrite_char Pwd` | Only field currently synced to DB in save |
| 3 | `level` | `int` | ✅ | `level: Integer` | `src/save.c fwrite_char Level` | |
| 4 | `race` | `int` | ✅ | `race: Integer` | `src/save.c fwrite_char Race` | |
| 5 | `ch_class` | `int` | ✅ | `ch_class: Integer` | `src/save.c fwrite_char Class` | |
| 6 | `sex` | `int` | ✅ | `sex: Integer` | `src/save.c fwrite_char Sex` | |
| 7 | `true_sex` | `int` | ✅ | `true_sex: Integer` | `src/save.c fwrite_char TrueSex` | Written by `create_character`; never by `to_orm` |
| 8 | `alignment` | `int` | ✅ | `alignment: Integer` | `src/save.c fwrite_char Align` | |
| 9 | `act` | `int` | ✅ | `act: Integer` | `src/save.c fwrite_char Act` | |
| 10 | `practice` | `int` | ✅ | `practice: Integer` | `src/save.c fwrite_char Prac` | |
| 11 | `train` | `int` | ✅ | `train: Integer` | `src/save.c fwrite_char Train` | |
| 12 | `perm_hit` | `int` | ✅ | `perm_hit: Integer` | `src/save.c fwrite_char HpManaMove` | In `pcdata` on runtime char |
| 13 | `perm_mana` | `int` | ✅ | `perm_mana: Integer` | `src/save.c fwrite_char HpManaMove` | In `pcdata` on runtime char |
| 14 | `perm_move` | `int` | ✅ | `perm_move: Integer` | `src/save.c fwrite_char HpManaMove` | In `pcdata` on runtime char |
| 15 | `newbie_help_seen` | `bool` | ✅ | `newbie_help_seen: Boolean` | Python-only | |
| 16 | `creation_points` | `int` | ✅ | `creation_points: Integer` | Python-only | |
| 17 | `creation_groups` | `list[str]` → JSON-encoded | ✅ | `creation_groups: String` (JSON) | Python-only | Already JSON-encoded via `_encode_creation_groups` |
| 18 | `creation_skills` | `list[str]` → JSON-encoded | ✅ | `creation_skills: String` (JSON) | Python-only | Already JSON-encoded |
| 19 | `perm_stat` | `list[int]` (5) | ✅ (partial) | `perm_stats: String` (JSON array) | `src/save.c fwrite_char Stats` | Written by `create_character`; `to_orm` encodes it; `from_orm` decodes it. Column exists. |
| 20 | `room_vnum` | `int` | ✅ | `room_vnum: Integer` | `src/save.c fwrite_char Room` | Set at creation; never updated on save currently |
| 21 | `size` | `int` | ✅ | `size: Integer` | `src/save.c fwrite_char Size` | Set at creation only |
| 22 | `form` | `int` | ✅ | `form: Integer` | `src/save.c fwrite_char Form` | Set at creation only |
| 23 | `parts` | `int` | ✅ | `parts: Integer` | `src/save.c fwrite_char Parts` | Set at creation only |
| 24 | `imm_flags` | `int` | ✅ | `imm_flags: Integer` | `src/save.c fwrite_char Imm` | Set at creation only |
| 25 | `res_flags` | `int` | ✅ | `res_flags: Integer` | `src/save.c fwrite_char Res` | Set at creation only |
| 26 | `vuln_flags` | `int` | ✅ | `vuln_flags: Integer` | `src/save.c fwrite_char Vul` | Set at creation only |
| 27 | `default_weapon_vnum` | `int` | ✅ | `default_weapon_vnum: Integer` | Python-only | Set at creation only |
| 28 | `hometown_vnum` | `int` | ✅ | `hometown_vnum: Integer` | Python-only | Set at creation only |
| 29 | `hit` | `int` | ✅ (as `hp`) | `hp: Integer` | `src/save.c fwrite_char Hp` | **Column named `hp`, not `hit`** — mismatch to fix in mapping |
| 30 | `max_hit` | `int` | **MISSING** | Proposed: `max_hit: Integer, default=20` | `src/save.c fwrite_char Hp` | |
| 31 | `mana` | `int` | **MISSING** | Proposed: `mana: Integer, default=100` | `src/save.c fwrite_char Mana` | |
| 32 | `max_mana` | `int` | **MISSING** | (derived from `perm_mana` at load; do NOT add — see note below) | — | Derived: `max_mana = perm_mana` (ROM handler.c:607). `from_orm` already does this at line 998. |
| 33 | `move` | `int` | **MISSING** | Proposed: `move: Integer, default=100` | `src/save.c fwrite_char Move` | |
| 34 | `max_move` | `int` | **MISSING** | (derived from `perm_move` at load) | — | Derived: `max_move = perm_move` (ROM handler.c:609). Skip separate column. |
| 35 | `gold` | `int` | **MISSING** | Proposed: `gold: Integer, default=0` | `src/save.c fwrite_char Gold` | |
| 36 | `silver` | `int` | **MISSING** | Proposed: `silver: Integer, default=0` | `src/save.c fwrite_char Silver` | |
| 37 | `exp` | `int` | **MISSING** | Proposed: `exp: Integer, default=0` | `src/save.c fwrite_char Exp` | |
| 38 | `trust` | `int` | **MISSING** | Proposed: `trust: Integer, default=0` | `src/save.c fwrite_char Trust` | Immortal level override |
| 39 | `invis_level` | `int` | **MISSING** | Proposed: `invis_level: Integer, default=0` | `src/save.c fwrite_char Invis` | |
| 40 | `incog_level` | `int` | **MISSING** | Proposed: `incog_level: Integer, default=0` | `src/save.c fwrite_char Incog` | |
| 41 | `saving_throw` | `int` | **MISSING** | Proposed: `saving_throw: Integer, default=0` | `src/save.c fwrite_char Save` | |
| 42 | `hitroll` | `int` | **MISSING** | Proposed: `hitroll: Integer, default=0` | `src/save.c fwrite_char Hitroll` | |
| 43 | `damroll` | `int` | **MISSING** | Proposed: `damroll: Integer, default=0` | `src/save.c fwrite_char Damroll` | |
| 44 | `wimpy` | `int` | **MISSING** | Proposed: `wimpy: Integer, default=0` | `src/save.c fwrite_char Wimpy` | |
| 45 | `position` | `int` | **MISSING** | Proposed: `position: Integer, default=8` (Position.STANDING) | `src/save.c fwrite_char Pos` | |
| 46 | `played` | `int` | **MISSING** | Proposed: `played: Integer, default=0` | `src/save.c fwrite_char Played` | Accumulated seconds played |
| 47 | `logon` | `int` | **MISSING** | Proposed: `logon: Integer, default=0` | `src/save.c fwrite_char Logon` | Unix timestamp of last login |
| 48 | `lines` | `int` | **MISSING** | Proposed: `lines: Integer, default=22` | `src/save.c fwrite_char Lines` | Page length |
| 49 | `prompt` | `str \| None` | **MISSING** | Proposed: `prompt: String, nullable=True` | `src/save.c fwrite_char Prompt` | `from_orm` reads via `getattr(db_char, "prompt", None)` — column missing from model |
| 50 | `prefix` | `str \| None` | **MISSING** | Proposed: `prefix: String, nullable=True` | `src/save.c fwrite_char Prefix` | |
| 51 | `title` | `str \| None` | **MISSING** | Proposed: `title: String, nullable=True` | `src/save.c fwrite_char Title` | In `pcdata.title` at runtime |
| 52 | `bamfin` | `str \| None` | **MISSING** | Proposed: `bamfin: String, nullable=True` | `src/save.c fwrite_char Bamfin` | In `pcdata.bamfin` |
| 53 | `bamfout` | `str \| None` | **MISSING** | Proposed: `bamfout: String, nullable=True` | `src/save.c fwrite_char Bamfout` | In `pcdata.bamfout` |
| 54 | `security` | `int` | **MISSING** | Proposed: `security: Integer, default=0` | `src/save.c fwrite_char Security` | In `pcdata.security` |
| 55 | `points` | `int` | **MISSING** | Proposed: `points: Integer, default=0` | `src/save.c fwrite_char Points` | Creation points spent; in `pcdata.points` |
| 56 | `last_level` | `int` | **MISSING** | Proposed: `last_level: Integer, default=0` | `src/save.c fwrite_char LLev` | In `pcdata.last_level` |
| 57 | `affected_by` | `int` | **MISSING** | Proposed: `affected_by: Integer, default=0` | `src/save.c fwrite_char AffectedBy` | Permanent affect bitvector (not transient spells) |
| 58 | `comm` | `int` | **MISSING** | Proposed: `comm: Integer, default=0` | `src/save.c fwrite_char Comm` | `from_orm` reads via `getattr` — column missing |
| 59 | `wiznet` | `int` | **MISSING** | Proposed: `wiznet: Integer, default=0` | `src/save.c fwrite_char Wiznet` | |
| 60 | `log_commands` | `bool` | **MISSING** | Proposed: `log_commands: Boolean, default=False` | Python-only (PLR_LOG) | |
| 61 | `mod_stat` | `list[int]` (5) | **MISSING** | Proposed: `mod_stat: JSON, default=[]` | `src/save.c fwrite_char ModStat` | Temporary stat modifiers (from equipment/spells); debatable — see note |
| 62 | `armor` | `list[int]` (4) | **MISSING** | Proposed: `armor: JSON, default=[100,100,100,100]` | `src/save.c fwrite_char AC` | AC[pierce/bash/slash/exotic] |
| 63 | `conditions` | `list[int]` (4) | **MISSING** | Proposed: `conditions: JSON, default=[0,48,48,48]` | `src/save.c fwrite_char Cond` | Drunk/full/thirst/hunger |
| 64 | `aliases` | `dict[str, str]` | **MISSING** | Proposed: `aliases: JSON, default={}` | `src/save.c fwrite_char Alias` | |
| 65 | `skills` | `dict[str, int]` | **MISSING** | Proposed: `skills: JSON, default={}` | `src/save.c fwrite_char Skill` (via pcdata.learned) | Merges `char.skills` and `pcdata.learned` |
| 66 | `groups` | `list[str]` | **MISSING** | Proposed: `groups: JSON, default=[]` | `src/save.c fwrite_char Group` | Merges `pcdata.group_known` |
| 67 | `board` | `str` | **MISSING** | Proposed: `board: String, default="general"` | `src/save.c fwrite_char Board` | Last board read |
| 68 | `last_notes` | `dict[str, float]` | **MISSING** | Proposed: `last_notes: JSON, default={}` | `src/save.c fwrite_char Note` | Board-name → last-read timestamp |
| 69 | `colours` | `dict[str, list[int]]` | **MISSING** | Proposed: `colours: JSON, default={}` | ROM QuickMUD extension | 34 colour triplets from `PCDATA_COLOUR_FIELDS` |
| 70 | `pet` | `PetSave \| None` | **MISSING** | Proposed: `pet_state: JSON, nullable=True` | `src/save.c fwrite_pet` / `fread_pet` | Full nested structure — see §3 |
| 71 | `pfile_version` | `int` | **MISSING** | Proposed: `pfile_version: Integer, default=1` | Python-only (TABLES-001) | Governs affect-bit translation on load; must be 1 for DB path |

### Fields the DB row currently has that JSON pfile does NOT round-trip

These columns exist in `mud/db/models.py:Character` (lines 91-132) and are written by `create_character` (`account_service.py:1040-1068`) but never updated by the JSON `save_character` path:

| DB Column | Written by | Updated by JSON save? | Notes |
|-----------|-----------|----------------------|-------|
| `size` | `create_character` | No | Race-derived; unlikely to change post-creation |
| `form` | `create_character` | No | Race-derived |
| `parts` | `create_character` | No | Race-derived |
| `imm_flags` | `create_character` | No | Race-derived |
| `res_flags` | `create_character` | No | Race-derived |
| `vuln_flags` | `create_character` | No | Race-derived |
| `hometown_vnum` | `create_character` | No | Set at creation |
| `default_weapon_vnum` | `create_character` | No | Set at creation |
| `creation_groups` | `create_character` | No | Static after creation |
| `creation_skills` | `create_character` | No | Static after creation |
| `perm_stats` | `create_character` | No | Permanent base stats |

These are "creation-time fixed" fields under ROM semantics — they don't change after character creation. The DB-canonical path makes them durable by default. The implementation subagent should verify each is reflected in `from_orm_full` even if they are not in the save loop.

### Note on `mod_stat`, `affected_by`, and transient state

`mod_stat` (field 61) and `affected_by` (field 57) represent equipment/spell modifiers that are **transient in ROM** — ROM re-applies them from the character's equipped items and active spells on load (`fread_char` does NOT save mod_stat). However the current Python `save_character` does round-trip them. The implementation subagent should **match current behavior** (save and restore them) until a separate audit decides to drop them.

---

## 2. `Character.from_orm` Audit

`mud/models/character.py:960-1061` implements `from_orm`. The following table audits each field it reads, whether the DB column is populated at creation, and whether `to_orm` / save logic writes it.

`to_orm` lives at `mud/models/character.py:1064-1096`.

| Field Read by `from_orm` | DB Column Exists? | Written by `create_character`? | Written by `to_orm`? | Gap? |
|--------------------------|------------------|---------------------------------|---------------------|------|
| `db_char.name` | ✅ | ✅ | ✅ | None |
| `db_char.level` | ✅ | ✅ | ✅ | None |
| `db_char.hp` | ✅ | ✅ | ✅ (as `hp=character.hit`) | None (column named `hp`, not `hit`) |
| `db_char.room_vnum` | ✅ | ✅ | ✅ | **Never updated after creation** — room_vnum drifts unless save writes it |
| `db_char.ch_class` | ✅ | ✅ | ✅ | None |
| `db_char.race` | ✅ | ✅ | ✅ | None |
| `db_char.sex` | ✅ | ✅ | ✅ | None |
| `db_char.alignment` | ✅ | ✅ | ✅ | None |
| `db_char.act` | ✅ | ✅ | ✅ | None |
| `db_char.practice` | ✅ | ✅ | ✅ | None |
| `db_char.train` | ✅ | ✅ | ✅ | None |
| `db_char.perm_hit` | ✅ | ✅ (`perm_hit=100`) | **NOT in `to_orm`** | `to_orm` omits this — load sets `pcdata.perm_hit` then `max_hit`; `to_orm` doesn't persist it |
| `db_char.perm_mana` | ✅ | ✅ | **NOT in `to_orm`** | Same gap as `perm_hit` |
| `db_char.perm_move` | ✅ | ✅ | **NOT in `to_orm`** | Same gap |
| `db_char.size` | ✅ | ✅ | ✅ | None |
| `db_char.form` | ✅ | ✅ | ✅ | None |
| `db_char.parts` | ✅ | ✅ | ✅ | None |
| `db_char.imm_flags` | ✅ | ✅ | ✅ | None |
| `db_char.res_flags` | ✅ | ✅ | ✅ | None |
| `db_char.vuln_flags` | ✅ | ✅ | ✅ | None |
| `db_char.hometown_vnum` | ✅ | ✅ | ✅ | None |
| `db_char.default_weapon_vnum` | ✅ | ✅ | ✅ | None |
| `db_char.newbie_help_seen` | ✅ | ✅ (`False`) | **NOT in `to_orm`** | `to_orm` omits; `from_orm` reads at line 1010 |
| `db_char.creation_points` | ✅ | ✅ | ✅ | None |
| `db_char.creation_groups` | ✅ | ✅ | ✅ | None |
| `db_char.creation_skills` | ✅ | ✅ | ✅ | None |
| `db_char.perm_stats` | ✅ | ✅ | ✅ | None |
| `db_char.true_sex` | ✅ | ✅ | **NOT in `to_orm`** | `to_orm` omits `true_sex`; `from_orm` reads at line 1020 |
| `getattr(db_char, "prompt", None)` | **MISSING** | No | No | `from_orm` uses `getattr` with fallback (line 1026) — column does not exist on model; defaults to hardcoded `"<%hhp %mm %vmv> "` |
| `getattr(db_char, "comm", 0)` | **MISSING** | No | No | `from_orm` reads via `getattr` at line 1032 — column missing; defaults to `CommFlag.PROMPT \| CommFlag.COMBINE` |

**Summary of `to_orm` omissions** (fields `from_orm` reads but `to_orm` never writes):
- `perm_hit`, `perm_mana`, `perm_move` — written at creation but `to_orm` skips them
- `newbie_help_seen` — written at creation only
- `true_sex` — written at creation only; `to_orm` omits
- `prompt`, `comm` — not even DB columns yet; `from_orm` silently defaults

**`to_orm` creates a fresh `DBCharacter()` object** (line 1072) — it is an INSERT helper, not an UPDATE helper. It must NOT be called for the new DB-canonical save path. The implementation needs a separate `update_db_row(session, char, db_char)` function.

---

## 3. New Code Surface Needed

### 3.1 `mud/db/models.py:Character` — Columns to Add

New SQLAlchemy columns (SQLite JSON type supported since SQLAlchemy 1.1; use `from sqlalchemy import JSON`):

```python
# --- Currently missing; needed for DB-canonical save ---
hit: Mapped[int] = mapped_column(Integer, default=20)          # rename: hp→hit, or keep hp and adjust from_orm
max_hit: Mapped[int] = mapped_column(Integer, default=20)      # or derive from perm_hit
mana: Mapped[int] = mapped_column(Integer, default=100)
move: Mapped[int] = mapped_column(Integer, default=100)
gold: Mapped[int] = mapped_column(Integer, default=0)
silver: Mapped[int] = mapped_column(Integer, default=0)
exp: Mapped[int] = mapped_column(Integer, default=0)
trust: Mapped[int] = mapped_column(Integer, default=0)
invis_level: Mapped[int] = mapped_column(Integer, default=0)
incog_level: Mapped[int] = mapped_column(Integer, default=0)
saving_throw: Mapped[int] = mapped_column(Integer, default=0)
hitroll: Mapped[int] = mapped_column(Integer, default=0)
damroll: Mapped[int] = mapped_column(Integer, default=0)
wimpy: Mapped[int] = mapped_column(Integer, default=0)
position: Mapped[int] = mapped_column(Integer, default=8)      # Position.STANDING = 8
played: Mapped[int] = mapped_column(Integer, default=0)
logon: Mapped[int] = mapped_column(Integer, default=0)
lines: Mapped[int] = mapped_column(Integer, default=22)
prompt: Mapped[str | None] = mapped_column(String, nullable=True)
prefix: Mapped[str | None] = mapped_column(String, nullable=True)
title: Mapped[str | None] = mapped_column(String, nullable=True)
bamfin: Mapped[str | None] = mapped_column(String, nullable=True)
bamfout: Mapped[str | None] = mapped_column(String, nullable=True)
security: Mapped[int] = mapped_column(Integer, default=0)
points: Mapped[int] = mapped_column(Integer, default=0)
last_level: Mapped[int] = mapped_column(Integer, default=0)
affected_by: Mapped[int] = mapped_column(Integer, default=0)
comm: Mapped[int] = mapped_column(Integer, default=0)
wiznet: Mapped[int] = mapped_column(Integer, default=0)
log_commands: Mapped[bool] = mapped_column(Boolean, default=False)
pfile_version: Mapped[int] = mapped_column(Integer, default=1)  # TABLES-001
# JSON columns
mod_stat: Mapped[str] = mapped_column(JSON, default=list)
armor: Mapped[str] = mapped_column(JSON, default=lambda: [100, 100, 100, 100])
conditions: Mapped[str] = mapped_column(JSON, default=lambda: [0, 48, 48, 48])
aliases: Mapped[str] = mapped_column(JSON, default=dict)
skills: Mapped[str] = mapped_column(JSON, default=dict)
groups: Mapped[str] = mapped_column(JSON, default=list)
last_notes: Mapped[str] = mapped_column(JSON, default=dict)
colours: Mapped[str] = mapped_column(JSON, default=dict)
pet_state: Mapped[str | None] = mapped_column(JSON, nullable=True)  # replaces PetSave
```

**Count: 39 new columns** (including the JSON blobs).

**Note on `hp` vs `hit`:** The existing column is named `hp` (model line 105) but the runtime field is `char.hit`. The implementation should either: (a) add a new `hit` column and deprecate `hp`, or (b) keep `hp` and update `from_orm`/save to use it consistently. Option (b) is less disruptive — just ensure `save` writes `db_char.hp = char.hit`.

**Note on `ObjectInstance` — CRITICAL:** The current `ObjectInstance` table (lines 79-88 of `models.py`) has only 4 columns: `prototype_vnum`, `location` (string), `character_id`, and PK. It **cannot** store:
- `value[5]` (item properties — e.g. weapon dice, container capacity, potion spell)
- `extra_flags`, `wear_loc`, `level`, `timer`, `cost`, `condition`, `enchanted`, `item_type`
- nested `contains[]` (container contents)
- per-object `affects[]`

This means the current `load_objects_for_character` (`mud/models/conversion.py:9-24`) restores only the prototype — all per-instance overrides are lost. The new DB-canonical path must either:

**Option A (recommended): JSON blob on Character** — Add `inventory_state: JSON` and `equipment_state: JSON` columns to `Character`. Serialize/deserialize using the existing `_serialize_object` / `_deserialize_object` logic from `mud/persistence.py:410-473`. This is the lowest-friction path since the logic already exists.

**Option B: Extend `ObjectInstance`** — Add all required columns to `ObjectInstance` with a self-referential `parent_id` for `contains`. More normalized but a larger schema migration.

**Recommendation: Option A.** Add two JSON columns (`inventory_state`, `equipment_state`) to `Character` and reuse the persistence serializers. The `ObjectInstance` table can be kept for historical reasons or dropped once migration is complete.

### 3.2 `mud/account/account_manager.py:save_character`

**Current behavior (lines 77-106):** Calls `_persistence.save_character(character)` (writes JSON), then optionally syncs `password_hash` to DB. Does NOT write any gameplay state to DB.

**New behavior:** Must write the full character state to the DB row. Replace the current body with:

```python
def save_character(character: Character) -> None:
    """Persist character to DB (DB-canonical path)."""
    session = None
    try:
        session = SessionLocal()
        db_char = session.query(DBCharacter).filter_by(name=character.name).first()
        if db_char is None:
            return  # Character must exist — creation path handles inserts
        _update_db_row(session, character, db_char)
        session.commit()
    except Exception as e:
        print(f"[ERROR] save_character failed for {character.name}: {e}")
    finally:
        if session:
            session.close()
```

Where `_update_db_row(session, char, db_char)` writes all 71 fields from §1. Note that `to_orm` **must not be reused** here — it constructs a new object (INSERT semantics), while save needs UPDATE semantics.

**Fields `save_character` currently writes to DB (today):** Only `password_hash` (line 100), and only conditionally. All other fields — 69 out of 71 in the field map — are gaps.

### 3.3 `mud/account/account_manager.py:load_character`

**Current behavior (lines 35-71):** Tries `_persistence.load_character(char_name)` (JSON), falls back to `from_orm`.

**New behavior:** Delete the JSON delegation. Keep only the DB path. Also expand `from_orm` into `from_orm_full` (or extend existing `from_orm`) to read all the new columns. The character_registry append must remain (INV-003 — see §7).

Simplified new body:

```python
def load_character(char_name: str, _ignored: str | None = None) -> Character | None:
    session = None
    try:
        session = SessionLocal()
        db_char = session.query(DBCharacter).filter(DBCharacter.name == char_name).first()
        if db_char is None:
            return None
        char = from_orm_full(db_char)  # new full-field version
        if char is not None:
            if char not in character_registry:
                character_registry.append(char)  # INV-003
        return char
    except Exception as e:
        print(f"[ERROR] Failed to load character {char_name} from DB: {e}")
        return None
    finally:
        if session:
            session.close()
```

### 3.4 `mud/persistence.py` — Recommendation

**Keep as a migration-only debug-export tool; do NOT delete immediately.** Rationale:

1. `data/players/*.json` pfiles may exist in production. If the JSON load path is deleted before a one-time migration script runs, those characters are silently inaccessible.
2. `mud/persistence.py` also owns `save_time_info` / `load_time_info` (`TIME_FILE = data/time.json`, lines 1216-1249) and `save_world` / `load_world` (lines 1180-1201). These are NOT player-state and should be retained (possibly moved to a separate `mud/time_persistence.py` to avoid confusion).
3. The TABLES-001 affect-bit migration logic (`translate_legacy_affect_bits`, lines 864-877) must be run against existing pfiles as part of the one-time migration script. It must not be lost.

**Recommended disposition:**
- Strip `save_character` and `load_character` from `mud/persistence.py` after Phase 2 (once migration script confirms all pfiles are migrated to DB).
- Rename the file to `mud/time_persistence.py` and keep only `TimeSave`, `save_time_info`, `load_time_info`.
- Write a standalone `scripts/migrate_pfiles_to_db.py` that: reads each `data/players/*.json`, runs `_upgrade_legacy_save` (TABLES-001 bit translation), and upserts the full DB row.

---

## 4. Caller Surface

### Production callers of `mud.persistence` (must migrate)

```
grep -rn "from mud.persistence|import mud.persistence|from mud import persistence" mud/
```

Result: **1 production caller**
- `mud/account/account_manager.py:28` — `import mud.persistence as _persistence`
  - Line 52: `_persistence.load_character(char_name)`
  - Line 85: `_persistence.save_character(character)`

These two call sites ARE the migration target. Replacing them with the DB-only implementation in §3.2 and §3.3 is the entirety of the production change.

**Other game-loop save call sites** (via `account_manager.save_character`, which is already the indirection layer):
- `mud/game_loop.py:516` — `save_character(character)` (connection close)
- `mud/game_loop.py:532` — `save_character(character)` (game shutdown)
- `mud/game_loop.py:761` — `save_character(candidate)` (during save_world equivalent)
- `mud/net/connection.py:741` — `save_character(char)` (mid-session save)
- `mud/net/connection.py:1788` — `save_character(char)` (logout)
- `mud/net/connection.py:2036` — `save_character(char)` (disconnect)

These all go through `mud.account.account_manager.save_character` and require **no changes** once `account_manager` is updated.

**Load call sites** (via `account_manager.load_character`):
- `mud/net/connection.py:1535` — `load_character(chosen_name)` (login)
- `mud/net/connection.py:1625` — `load_character(sanitize_account_name(username).capitalize())` (reconnect)
- `mud/net/connection.py:1885` — `load_character(...)` (reconnect)

Also no changes needed once `account_manager` is updated.

### Test callers of `mud.persistence` (must update or delete)

| File | Import | Usage | Disposition |
|------|--------|-------|-------------|
| `tests/test_player_save_format.py` | `import mud.persistence as persistence` | Tests JSON pfile format | **Delete** — tests JSON-specific format, irrelevant after migration |
| `tests/test_time_persistence.py` | `import mud.persistence as persistence` | Tests `save_time_info`/`load_time_info` | **Keep, update import** if time functions moved to `mud/time_persistence.py` |
| `tests/test_account_auth.py:82` | `import mud.persistence as _persistence` | Patches `_persistence.PLAYERS_DIR` | **Update** — remove PLAYERS_DIR patch; auth test should hit DB directly |
| `tests/test_persistence.py` | `import mud.persistence as persistence` | Direct `persistence.save_character` / `persistence.load_character` | **Rewrite against DB path** (see §6) |
| `tests/test_boards.py:7` | `from mud import persistence` | Boards test (likely uses save_character) | **Update** — replace with `account_manager.save_character` |
| `tests/test_wiznet.py:3` | `import mud.persistence as persistence` | Wiznet test | **Update** — replace persistence calls with account_manager |
| `tests/test_commands.py:187` | `from mud import persistence as p` | Command test | **Update** |
| `tests/test_logging_admin.py:7` | `import mud.persistence as persistence` | Admin logging test | **Update** |
| `tests/test_persistence_password_hash.py:12` | `import mud.persistence as persistence` | Password hash round-trip | **Rewrite** against DB path |
| `tests/test_inventory_persistence.py:1` | `import mud.persistence as persistence` | Inventory persistence | **Rewrite** against DB path (see §6) |
| `tests/test_affects.py:2` | `import mud.persistence as persistence` | Affects round-trip | **Update** |
| `tests/integration/test_save_load_parity.py:25` | `import mud.persistence as persistence` | Save/load parity integration test | **Rewrite** against DB path |
| `tests/integration/test_tables_001_affect_migration.py:21` | `import mud.persistence as persistence` | TABLES-001 bit translation | **Rewrite** — migration logic must still be tested, but against DB path |
| `tests/integration/test_character_creation_runtime.py:12` | `import mud.persistence as _persistence` | Patches `_persistence.PLAYERS_DIR` | **Update** — remove PLAYERS_DIR patch |
| `tests/integration/test_pet_persistence.py:22` | `import mud.persistence as persistence` | Pet save/load | **Rewrite** against `pet_state` JSON column |
| `tests/integration/test_inv008_persistence_coherence.py:22` | `import mud.persistence as _persistence` | INV-008 enforcement (JSON path) | **Rewrite** — see §5 |

---

## 5. INV-008 Test Rewrite Plan

`tests/integration/test_inv008_persistence_coherence.py` currently asserts the JSON path. All 4 named tests must change their underlying surface while keeping the same test names and the same behavioral assertions.

**Shared fixture change** (`_clean`, lines 47-57): Remove `_persistence.PLAYERS_DIR = tmp_path / "players"` and `_persistence.PLAYERS_DIR = _persistence.Path("data/players")`. These are JSON-path artifacts. Keep DB reset (`Base.metadata.drop_all` / `create_all`).

### `test_inv008_save_load_round_trip_preserves_gameplay_state` (lines 65-103)

**What changes:** Nothing in the test body. The assertions already test `account_manager.save_character` and `account_manager.load_character`. Once `account_manager` delegates to DB instead of JSON, this test passes against the DB path automatically.

**Only change:** Remove the `_persistence.PLAYERS_DIR` patch from the `_clean` fixture. The test body is already correct.

### `test_inv008_load_registers_character` (lines 106-122)

**What changes:** Same as above — the test body already tests `account_manager.load_character`. No body changes needed; just fixture cleanup.

### `test_inv008_password_hash_round_trips` (lines 125-139)

**What changes:** None in test body. `pcdata.pwd` must survive `save_character` → `load_character`. Currently survives via JSON; must survive via DB after migration. Test body already correctly asserts `loaded.pcdata.pwd`.

### `test_inv008_room_placement_survives_round_trip` (lines 142-150)

**What changes:** None in test body. Room placement is persisted via `room_vnum` in the DB row. `from_orm` already reads and sets `char.room` from `room_vnum` (line 964). The DB-canonical save must write `db_char.room_vnum = char.room.vnum if char.room else ROOM_VNUM_TEMPLE`.

### Test to ADD (new)

The current test `test_inv008_db_fallback_loads_legacy_character` (lines 158-210) tests the JSON-then-DB fallback. After the reversal, there is no JSON fallback — the DB IS the path. This test becomes:

```python
def test_inv008_db_canonical_is_sole_path():
    """INV-008 reversed: DB row is the sole canonical source; no JSON fallback exists."""
    char_name = "Legacyx"
    created = create_character(None, char_name, starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created
    # No pfile should exist (and even if it did, it would not be consulted)
    loaded = load_character(char_name)
    assert loaded is not None
    assert loaded.name == char_name
    assert loaded in character_registry  # INV-003
```

---

## 6. The 3 Broken Persistence-Test Failures

**Failing tests:**
- `tests/test_persistence.py::test_character_json_persistence`
- `tests/test_persistence.py::test_inventory_round_trip_preserves_object_state`
- `tests/test_inventory_persistence.py::test_inventory_and_equipment_persistence`

**Root cause:** All three use `inventory_object_factory(3022)` (sword vnum 3022). The JSON area files at `data/areas/*.json` are incomplete — vnum 3022 is not loaded into `obj_registry`, so `spawn_object(3022)` returns `None` and the test fails.

**Recommendation: Delete these tests as part of Phase 2.** Do NOT regenerate area JSON files as a fix:

1. All three tests directly call `mud.persistence.save_character` / `mud.persistence.load_character`. Once `mud/persistence.py`'s character save/load functions are deleted (Phase 2), these tests are stale regardless of the area data issue.
2. The inventory round-trip behavior they test will be covered by the rewritten `test_inv008_save_load_round_trip_preserves_gameplay_state` once the DB path stores `inventory_state` JSON correctly.
3. Regenerating `data/areas/*.json` (via `convert_enhanced.py`) fixes a symptom of tests that are about to be deleted. It is wasted work.

**Before Phase 2, these tests can be skipped** with `@pytest.mark.skip(reason="JSON pfile path being replaced by DB-canonical path")` rather than deleted, to preserve the behavioral documentation during migration.

---

## 7. Risk Register

### INV-001 (SINGLE-DELIVERY) — No touch
Save/load path changes do not affect message delivery. `_push_message` in `engine.py` is unaffected. Risk: NONE.

### INV-002 (PROMPT-CLAMP) — No touch
Prompt rendering reads `char.hit` at display time. Whether that came from JSON or DB is irrelevant. Risk: NONE.

### INV-003 (REGISTRY-MEMBERSHIP) — CRITICAL risk if not handled
Today `_persistence.load_character` appends to `character_registry` at line 1176. The new `account_manager.load_character` must also append (currently it does, at lines 66-67, but only for the DB fallback path). After the reversal, the append MUST be in the single DB-only path. **Enforcement test:** `test_inv008_load_registers_character` covers this. Do not remove the `character_registry.append(char)` call.

### INV-004 (PC-CONNECTION-SURVIVES-DEATH) — No touch
Death path does not touch persistence. Risk: NONE.

### INV-005, INV-006 — No touch. Risk: NONE.

### INV-007 (RNG-DETERMINISM) — No touch. Risk: NONE.

### INV-008 (DUAL-LOAD-CHARACTER-COHERENCE) — Being superseded
The invariant itself changes: the new invariant is "DB row is the sole canonical source." Update `CROSS_FILE_INVARIANTS_TRACKER.md` after Phase 2 to reflect the new enforcement point.

### Data-loss risk: existing `data/players/*.json` pfiles
If the JSON load path is removed before pfiles are migrated to DB, any character with a pfile but no matching full DB row loses all gameplay state. The `create_character` DB row has gameplay fields but may be stale/zero for active players who have since progressed. **Mitigation:** Write and run `scripts/migrate_pfiles_to_db.py` BEFORE Phase 2 (before deleting the JSON load path). This script must:
1. Iterate `data/players/*.json`
2. Call `_upgrade_legacy_save` (TABLES-001 affect-bit translation) on each
3. Upsert the full DB row

### TABLES-001 affect-bit migration
`translate_legacy_affect_bits` (`mud/persistence.py:864-877`) translates pre-2.6.34 `affected_by` bitvectors. This logic runs during JSON load (`_upgrade_legacy_save`). After the DB migration, all pfiles should be at `pfile_version=1` (ROM-canonical bits). The migration script must apply the translation before inserting to DB. Once all pfiles are migrated and validated, this code path is only needed for disaster recovery.

### Async concerns
`save_character` is called from async context (e.g. `mud/net/connection.py:741`, `1788`, `2036`). The current `account_manager.save_character` is synchronous (uses `SessionLocal` directly with no `await`). The new DB-canonical version should remain synchronous — SQLAlchemy with SQLite does not require async for saves, and the current call sites do not `await` it. **No async changes required.**

### `ObjectInstance` shape divergence
As noted in §3.1: the current `ObjectInstance` table cannot store per-instance object overrides. Any character loaded via the current `from_orm` + `load_objects_for_character` path gets items reset to prototype defaults. This is an existing bug on the DB path (not introduced by this migration). The migration must fix it by adding `inventory_state` / `equipment_state` JSON columns to `Character` (Option A from §3.1). If this is not done, loaded characters will be missing enchanted items, depleted potions, customized equipment, and container contents.

### `PetSave` has no DB analog
`PetSave` (lines 241-281 of `mud/persistence.py`) is a complex nested dataclass. No column on `Character` stores it. The recommended `pet_state: JSON` column (§3.1) stores the entire `PetSave` dict verbatim. The deserialization logic in `_deserialize_pet` (`mud/persistence.py:579-725`) can be moved to `account_manager` as a private helper. Do not attempt to normalize pet state into a separate table — it adds complexity for low payoff.

---

## 8. Estimated Implementation Scope

| Metric | Estimate |
|--------|----------|
| Files to touch | 7 primary (`mud/db/models.py`, `mud/account/account_manager.py`, `mud/models/character.py`, `mud/models/conversion.py`, `mud/persistence.py`, `tests/integration/test_inv008_persistence_coherence.py`, `CROSS_FILE_INVARIANTS_TRACKER.md`) + ~14 test files to update/delete |
| New SQLAlchemy columns on `Character` | 39 |
| New JSON columns (subset of above) | 9 (`mod_stat`, `armor`, `conditions`, `aliases`, `skills`, `groups`, `last_notes`, `colours`, `pet_state`) + 2 for inventory (`inventory_state`, `equipment_state`) = 11 JSON columns |
| New standalone script | 1 (`scripts/migrate_pfiles_to_db.py`) |
| Net LOC delta | +350–450 (new `_update_db_row` function ~100 lines, `from_orm_full` expansion ~80 lines, migration script ~100 lines, test rewrites ~150 lines, deletions offset ~100 lines) |

### Single-run vs. split recommendation

**Split into 2 phases. A single run is not plausible.**

**Phase 1 — Schema + serializer (no behavior change):**
- Add all 39 columns + 2 inventory JSON columns to `mud/db/models.py:Character`
- Implement `from_orm_full` (reads all new columns) and `_update_db_row` (writes all new columns) in `mud/account/account_manager.py` or a new `mud/account/persistence_db.py`
- Write and run `scripts/migrate_pfiles_to_db.py` (JSON → DB one-time migration)
- Keep JSON path live in `account_manager` — still try JSON first, DB second
- Add Phase 1 test: verify `_update_db_row` round-trips all 71 fields
- Commit: "feat(persistence): DB-canonical schema and serializer (Phase 1)"

**Phase 2 — Flip and delete (behavior change):**
- Replace `account_manager.load_character` body with DB-only path
- Replace `account_manager.save_character` body with `_update_db_row` call
- Delete JSON player-save/load functions from `mud/persistence.py`; keep `TimeSave`, `save_time_info`, `load_time_info`, `save_world`/`load_world` (or move to `mud/time_persistence.py`)
- Delete/rewrite all stale test files from the caller surface table in §4
- Rewrite `test_inv008_persistence_coherence.py` per §5
- Update `CROSS_FILE_INVARIANTS_TRACKER.md`: INV-008 now enforces DB-canonical path
- Commit: "feat(persistence): DB-canonical complete — delete JSON pfile path (Phase 2)"

**Why two phases:** Phase 1 is additive (schema + serializer). Phase 2 flips the live production path and deletes code. Separating them means: (a) the migration script can be validated before the old path is removed; (b) if the schema migration fails, no production behavior has changed; (c) the ~14 test file updates are isolated to Phase 2 where they belong.
