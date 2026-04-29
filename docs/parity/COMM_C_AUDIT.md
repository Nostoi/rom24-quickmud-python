# `comm.c` ROM Parity Audit

- **Date opened:** 2026-04-29
- **ROM source:** `src/comm.c` (2831 lines, network I/O + I/O primitives + colour + `act_new`)
- **Python module(s):**
  - `mud/net/connection.py` — telnet / login / `_stop_idling`
  - `mud/net/ansi.py` — ROM `{x` token translation
  - `mud/net/protocol.py` — `send_to_char` over network
  - `mud/models/character.py:Character.send_to_char` — per-character output buffer
  - `mud/utils/act.py:act_format` — partial `act_new` token expansion (wiznet only)
  - `mud/account/account_service.py:is_valid_account_name` — `check_parse_name` port
  - `mud/commands/auto_settings.py:do_prompt` — sets `pcdata.prompt`
  - `mud/handler.py` — inline `fix_sex` clamp at affect-strip site
- **Status:** 🔄 IN PROGRESS — Phase 1–3 complete, gap closures pending.

## Scope notes

`comm.c` is mostly the ROM networking layer (`main`, `init_socket`,
`game_loop_*`, descriptor read/write, telnet protocol). QuickMUD replaces that
with an asyncio telnet/SSH/WebSocket pipeline (`mud/net/connection.py`,
`mud/net/telnet_server.py`, `mud/net/ssh_server.py`, `mud/network/websocket_stream.py`).
**Per the tracker (`P3-6: comm.c — Different architecture`), the
descriptor/select loop is intentional architectural divergence and out of
scope for parity.**

The non-networking surface in `comm.c` is in scope and is what this audit
covers:

- `bust_a_prompt` (1420) — prompt token expansion (`%h %m %v %r …`)
- `act_new` (2184) — per-room broadcast with `$n $N $e $E $m $M $s $S $p $P $t $T $d` tokens
- `colour` / `colourconv` (2391 / 2741) — `{x`-style ANSI conversion
- `send_to_char` / `send_to_char_bw` / `send_to_desc` (1965 / 1931 / 2016) — colour-aware writers
- `page_to_char` / `page_to_char_bw` / `show_string` (2064 / 1941 / 2123) — pager
- `check_parse_name` (1699) — name acceptability
- `check_reconnect` / `check_playing` (1836 / 1885) — login linkdead handling
- `stop_idling` (1910) — limbo-return on input
- `fix_sex` (2178) — clamp `ch->sex` to `[0,2]`

Per the existing tracker entries for `act_obj.c`, `act_move.c`, `handler.c`,
and `act_info.c`, individual `act()` broadcast call sites have been audited
and fixed *in situ*. Building a single central `act()` dispatcher is a
whole-codebase refactor and is not booked as a single closeable gap here —
new TO_ROOM / TO_VICT broadcast omissions get an ID in the calling
subsystem's audit doc, not this one.

---

## Phase 1 — Function Inventory

| ROM function | ROM lines | Python counterpart | Status | Notes |
|--------------|-----------|---------------------|--------|-------|
| `main` | 360–476 | `mud/net/telnet_server.py` (asyncio entry) | N/A | Networking arch — out of scope |
| `init_socket` | 477–542 | `mud/net/telnet_server.py` / `ssh_server.py` | N/A | Networking arch |
| `game_loop_mac_msdos` / `game_loop_unix` | 543–938 | `mud/game_loop.py` | N/A | Tick scheduler in Python; descriptor I/O is async |
| `init_descriptor` | 939–1051 | `mud/net/connection.py` (login dispatcher) | N/A | Networking arch |
| `close_socket` | 1052–1123 | `mud/net/connection.py` (cleanup paths) | N/A | Networking arch |
| `read_from_descriptor` / `read_from_buffer` / `process_output` / `write_to_descriptor` | 1124–1684 | asyncio stream readers/writers | N/A | Networking arch |
| `bust_a_prompt` | 1420–1595 | ❌ NONE | ❌ MISSING | `pcdata.prompt` is stored but never expanded; `send_prompt` always emits literal `"> "` (COMM-001). |
| `write_to_buffer` | 1602–1654 | `Character.send_to_char` + per-stream writer | N/A | Buffer-management diverges with asyncio |
| `log_f` | 1685–1694 | `mud/logging` helpers | N/A | Logging plumbing |
| `check_parse_name` | 1699–1829 | `mud/account/account_service.py:is_valid_account_name` | ⚠️ PARTIAL | Length lower bound (COMM-003), mob-name collision (COMM-004), clan-name reject (COMM-006), double-newbie-disconnect (COMM-005) all missing. |
| `check_reconnect` | 1836–1878 | `mud/net/connection.py:_broadcast_reconnect_notifications` + login flow | ✅ AUDITED | "$N groks the fullness of $S link." wiznet broadcast and "note in progress" reminder both present. |
| `check_playing` | 1885–1906 | `mud/net/connection.py:_prompt_yes_no("This account is already playing. Reconnect? (Y/N)")` | ✅ AUDITED | Y/N branch matches `CON_BREAK_CONNECT`. |
| `stop_idling` | 1910–1924 | `mud/net/connection.py:_stop_idling` | ⚠️ PARTIAL | Broadcast uses literal name, not `act("$n has returned from the void.")` PERS-aware text (COMM-007). |
| `send_to_char_bw` / `send_to_char` / `send_to_desc` | 1931 / 1965 / 2016 | `mud/models/character.py:Character.send_to_char` + `mud/net/protocol.py:send_to_char` + `mud/net/ansi.py:render_ansi` | ⚠️ PARTIAL | ANSI token table is a strict subset of ROM (COMM-008). pcdata-customizable channel codes intentionally not implemented (no pfile parity goal — like `sha256_crypt`). |
| `page_to_char_bw` / `page_to_char` | 1941 / 2064 | `mud/net/protocol.py:send_to_char` → `Session.start_paging` | ✅ AUDITED | `send_to_char` auto-routes through the pager when `lines > 0` and text exceeds the page limit (architectural simplification of ROM's per-callsite `page_to_char` opt-in). |
| `show_string` | 2123–2174 | `mud/net/session.py:Session.send_next_page` + `mud/net/connection.py:_read_player_command` | ✅ AUDITED | ROM dispatch semantics verified after COMM-002: empty input continues; any non-empty input aborts and is consumed as no-op. |
| `fix_sex` | 2178–2182 | `mud/handler.py:1112-1114, 1144-1149` (inline) | ⚠️ PARTIAL | Logic exists at the affect-strip site only; no module-level helper for spell affects that flip sex (COMM-009). |
| `act_new` | 2184–2388 | `mud/utils/act.py:act_format` (wiznet subset) + per-call-site broadcasts | ⚠️ PARTIAL — architectural | No central dispatcher. TO_CHAR/TO_VICT/TO_ROOM/TO_NOTVICT modes, `min_pos` filter, `MOBtrigger` handoff are reimplemented per command in `mud/spec_funs.py`, `mud/mob_cmds.py`, `mud/commands/*`. Per-site gaps are tracked in the calling subsystem's audit (`ACT_OBJ_C_AUDIT.md`, `ACT_MOVE_C_AUDIT.md`, `HANDLER_C_AUDIT.md`). Not booked as a single closeable gap here. |
| `colour` | 2391–2739 | `mud/net/ansi.py:translate_ansi` | ⚠️ PARTIAL | Subset of token table (COMM-008). |
| `colourconv` | 2741–2790 | `mud/net/ansi.py:render_ansi` | ✅ AUDITED | ANSI-on/off branch driven by `conn.ansi_enabled` (different gate from `PLR_COLOUR`, but functionally equivalent for QuickMUD's per-connection ANSI prompt). |
| `printf_to_desc` / `printf_to_char` / `bugf` / `gettimeofday` | 2791–2831 | Python `f"…"` / `logging` | N/A | C variadic boilerplate. |

---

## Phase 2 — Verification highlights

### `bust_a_prompt` — ROM 1420–1595

ROM walks `ch->prompt`, replacing `%h %H %m %M %v %V %x %X %g %s %a %r %R %z %% %e %c %o %O` with hp/mana/move/exp/gold/silver/alignment/room/area-name/exits, falls back to `"{p<%dhp %dm %dmv>{x %s"` if unset, and short-circuits to `"{p<AFK>{x "` when `COMM_AFK` is on. The result is colourconv'd and written to the descriptor.

Python's `mud/commands/auto_settings.py:do_prompt` saves the string into `pcdata.prompt` (`"<%hhp %mm %vmv> "` for `prompt all`) but no consumer renders it. `send_prompt` in `mud/net/connection.py` is hard-coded to `"> "`. The `COMM_AFK` flag is recognized for the AFK channel filter but not surfaced in the prompt. **No HP / mana / move display ever reaches the client** — a regression visible to every connected player.

### `check_parse_name` length bound — ROM 1729

```c
if (strlen (name) < 2)
    return FALSE;
```

Python's `is_valid_account_name` uses `< 3`, so 2-letter ROM-legal names (e.g. `Bo`, `Jo`) are rejected. The companion `total_caps > strlen/2 && strlen < 3` clause at ROM 1774–1776 is also reachable in C only at `len == 2`; with Python's stricter early-return that branch is dead code (no functional impact, but worth noting in the fix).

### `check_parse_name` mob-name collision — ROM 1782–1796

ROM rejects new-character names that collide with any `MOB_INDEX_DATA->player_name` to prevent `kill <yourself>` confusion. Python has no equivalent guard.

### `check_parse_name` clan reject — ROM 1713–1718

ROM iterates `clan_table[]` and refuses names that match a clan's name. Python has no clan-name guard. With the current `mud/models/clan.py` (`Loner` is the canonical clan), a player named `Loner` would slip past — though `loner` is already covered by `_RESERVED_NAMES`.

### `check_parse_name` double-newbie disconnect — ROM 1804–1825

When a not-yet-`CON_PLAYING` descriptor is using the same character name as the connecting one, ROM disconnects the duplicate, `wiznet`s `"Double newbie alert (%s)"`, and rejects the new name. Python doesn't run a duplicate-newbie sweep.

### `stop_idling` broadcast — ROM 1922

```c
act ("$n has returned from the void.", ch, NULL, NULL, TO_ROOM);
```

`act()` resolves `$n` via `PERS(ch, to)` so other characters who can't see `ch` still get a sensible substitute. Python's `_stop_idling` calls `destination.broadcast(f"{name} has returned from the void.", exclude=char)` with `name = char.name or "Someone"`. Acceptable for the common case but bypasses sneak/visibility (`can_see`) and lacks the capitalization rules of `act_new`.

### `fix_sex` — ROM 2178–2182

```c
if (ch->sex < 0 || ch->sex > 2)
    ch->sex = IS_NPC (ch) ? 0 : ch->pcdata->true_sex;
```

ROM calls `fix_sex` from `db.c:load_char_obj`, `magic.c` (when transformation/polymorph spells flip sex), and from `handler.c` after object affects unwear. Python only does the clamp inline at `mud/handler.py:1112-1114` (during the affect-strip pass) and `1144-1149` (perm stat reset). Spell handlers and load paths that toggle `ch.sex` directly will not auto-clamp.

### `colour` token table — ROM 2391–2739

ROM's `{`-token table includes ~40 entries, of which roughly half are pcdata-customizable channel/wiznet colors (`{p {s {S {d {9 {Z {o {O {i {I {1-7 {k {K {l {L {n {N {a {A {q {Q {f {F {e {E {h {H {j`) and the rest are basic colours plus four "specials": `{D` (dark grey), `{*` (bell), `{/` (newline), `{-` (tilde), `{{` (literal brace).

`mud/net/ansi.py:ANSI_CODES` covers `{x {r {g {y {b {m {c {w {R {G {Y {B {M {C {W {h {H` — basic 8-colour + bright + the `{h`/`{H` pair. The four specials (`{D {* {/ {-`) and the `{{` literal-brace escape are missing. The pcdata-customizable colour codes are intentionally out of scope: QuickMUD has no pfile parity goal and no `pcdata.prompt[3]`-style channel-colour customization, by deliberate analogy with the SHA-256 → PBKDF2 divergence.

### `act_new` — ROM 2184–2388 (architectural divergence note)

ROM's `act_new` is the single dispatcher for every `$n`-style broadcast in the
codebase. QuickMUD has not built a central equivalent: the token expansion
lives in `mud/utils/act.py:act_format` (wiznet-only subset, no `$d` door, no
`min_pos` filter, no `MOBtrigger`/`mp_act_trigger` handoff), and individual
commands rebuild their own broadcast helpers (`spec_funs._broadcast_room`,
`mob_cmds._move_to_room`, ad-hoc f-strings in `mud/commands/*.py`).

**This is treated as architectural carry-over, not a single comm.c gap.** Per-site
TO_ROOM / TO_VICT omissions are gap-tracked in the calling file's audit:

- `act_obj.c` audit gaps DROP-* / GET-* / GIVE-* — closed.
- `act_move.c` audit gaps ENTER-* / FOLLOW-* — closed.
- `handler.c` audit gaps HANDLER-* — closed.
- `board.c` audit gaps BOARD-002 / BOARD-003 — closed.

Future broadcast omissions get IDs in the calling subsystem's audit, not in
`COMM_C_AUDIT.md`. If the team later decides to consolidate into a real
`mud.act` dispatcher, that will be a refactor PR with its own design doc, not
a single-gap close.

---

## Phase 3 — Gaps

| ID | Severity | ROM ref | Python ref | Description | Status |
|----|----------|---------|------------|-------------|--------|
| COMM-001 | CRITICAL | `src/comm.c:1420-1595` | `mud/utils/prompt.py:bust_a_prompt`, `mud/net/connection.py:1698,1923` | `bust_a_prompt` ported. Tokens `%h %H %m %M %v %V %x %X %g %s %a %r %R %z %% %e %c %o %O` expand against character state; default `<%dhp %dm %dmv> %s` fallback when `ch->prompt` unset; `COMM_AFK` short-circuits to `<AFK>`. `do_prompt` now stores on `Character.prompt` (matches ROM `ch->prompt`) instead of the `PCData.prompt` colour-triplet field. `send_prompt` applies ANSI rendering so `{p…{x` colour wrappers don't leak. | ✅ FIXED |
| COMM-002 | IMPORTANT | `src/comm.c:632-633,1941-2174` | `mud/net/session.py:Session.start_paging`, `mud/net/connection.py:_read_player_command` | Pager machinery (`Session.start_paging` / `send_next_page` / `clear_paging`) was already wired into `send_to_char` and `_read_player_command`, but the input-handling diverged from ROM: `"c"` was treated as continue (ROM has no continue hotkey — only empty input continues), and arbitrary non-empty input was dispatched to `interpret()` instead of being consumed as the abort signal. Fixed `_read_player_command` to mirror ROM `comm.c:632-633`: while paging, ROM dispatches input to `show_string` instead of `interpret`; empty input continues, ANY non-empty input aborts and is consumed as no-op (returns `" "`). | ✅ FIXED |
| COMM-003 | IMPORTANT | `src/comm.c:1729` | `mud/account/account_service.py:591` | `check_parse_name` length lower bound was `< 3`, ROM is `< 2`. Two-letter ROM-legal names (e.g. `Bo`) were rejected. Fixed by flipping the bound to `< 2` and updating `test_name_validator_matches_rom_check_parse_name` (NANNY-012) which had locked in the wrong threshold with a docstring misreading ROM. | ✅ FIXED |
| COMM-004 | IMPORTANT | `src/comm.c:1782-1796` | `mud/account/account_service.py:is_valid_character_name` | New `is_valid_character_name` helper layered on top of `is_valid_account_name` adds the ROM mob-keyword collision check. `create_character` and `_run_character_creation_flow` now use it; the old `is_valid_account_name` keeps syntactic-only semantics so account-name validation (a Python addition with no ROM analogue) still works. | ✅ FIXED |
| COMM-005 | MINOR | `src/comm.c:1804-1825` | `mud/account/account_service.py:575-617` | `check_parse_name` doesn't sweep `descriptor_list` for not-yet-`CON_PLAYING` duplicates and doesn't emit the `"Double newbie alert (%s)"` wiznet broadcast. | 🔄 OPEN |
| COMM-006 | MINOR | `src/comm.c:1713-1718` | `mud/account/account_service.py:is_valid_character_name` | `is_valid_character_name` now iterates `CLAN_TABLE` and rejects exact (case-insensitive) matches. `rom` and `loner` are now both rejected. | ✅ FIXED |
| COMM-007 | MINOR | `src/comm.c:1922` | `mud/net/connection.py:_stop_idling` | `_stop_idling` now broadcasts via `act_format("$n has returned from the void.", recipient=None, actor=char)` instead of the literal `f"{name} has returned from the void."` fallback. Routes through ROM-style `$n` token expansion (`mud/utils/act.py:_pers`) so name → short_descr fallback works correctly for entities without a literal `name`. | ✅ FIXED |
| COMM-008 | MINOR | `src/comm.c:2714-2728` | `mud/net/ansi.py:5-23` | ANSI translator missing ROM specials: `{D` (dark grey), `{*` (bell), `{/` (newline), `{-` (tilde), `{{` (literal-brace escape). pcdata-customizable channel codes (`{p {s {6 {7 {k …`) are intentionally not in scope (no pfile parity). | 🔄 OPEN |
| COMM-009 | MINOR | `src/comm.c:2178-2182` | `mud/handler.py:1112-1114` (only callsite) | No standalone `fix_sex` helper. Spell handlers / load paths that flip `ch.sex` outside the affect-strip pass don't auto-clamp to `[0,2]`. | 🔄 OPEN |

### Deferred-by-design (no IDs)

- **Networking layer** (`main`, `init_socket`, `game_loop_*`, descriptor I/O,
  telnet protocol bytes): asyncio rewrite, intentional architectural
  divergence, tracker confirms.
- **Central `act()` dispatcher**: per-site broadcasts handled in calling
  subsystem audits; not a single closeable gap here.
- **pcdata-customizable channel/wiznet colours**: no pfile parity goal,
  parallel to SHA-256 → PBKDF2 deliberate divergence.
- **`_RESERVED_NAMES` extras (`god`, `imp`)**: stricter than ROM, not a
  parity regression.

---

## Phase 4 — Gap Closures

### COMM-007 — `_stop_idling` broadcast via act_format (MINOR)

- **Test:** `tests/test_networking_telnet.py::test_stop_idling_broadcast_uses_rom_act_format`
  — entity with `name=None, short_descr="the wraith"` is correctly
  broadcast as `"the wraith has returned from the void."`. The legacy
  literal-name fallback would have produced `"Someone has returned…"`.
- **Implementation:** `mud/net/connection.py:_stop_idling` now builds
  the message via `act_format("$n has returned from the void.",
  recipient=None, actor=char)` mirroring ROM `act("$n has returned from
  the void.", ch, NULL, NULL, TO_ROOM)` at `src/comm.c:1922`. Routes
  through `mud/utils/act.py:_pers` so `$n` expands via the canonical
  ROM-style perspective rules (name → short_descr → `someone`). The
  pre-existing test `test_stop_idling_returns_character_to_previous_room`
  remains green (named players still render with their name).

### COMM-002 — `show_string` pager input semantics (IMPORTANT)

- **Test:** `tests/test_networking_telnet.py::test_show_string_pager_aborts_on_any_non_empty_input_per_rom`
  asserts that `"c"` and arbitrary non-empty input abort the pager and are
  consumed as no-op (returns `" "`), not dispatched to `interpret()`.
  `test_show_string_paginates_output` updated to assert ROM-faithful
  abort consumption.
- **Implementation:** `mud/net/connection.py:_read_player_command` —
  while `session.show_buffer` is set, empty input advances paging; any
  non-empty input clears the pager and returns `" "`. Mirrors ROM
  `src/comm.c:632-633` (input dispatched to `show_string` instead of
  `interpret`) and `src/comm.c:2131-2141` (`one_argument(input, buf);
  if (buf[0] != '\0')` abort branch). The previous QuickMUD extensions
  (`"c"` → continue, `"q"` → abort, others → execute as command) were
  non-ROM and have been removed.
- **Note:** the bulk paging machinery (`Session.start_paging`,
  `send_next_page`, `clear_paging`) was already in place and wired into
  `mud/net/protocol.py:send_to_char`; this gap closure pinned the
  ROM-faithful abort semantics that were missing.

### COMM-006 — Clan-name rejection (MINOR)

- **Test:** `tests/integration/test_nanny_login_parity.py::test_name_validator_rejects_clan_name`
  asserts `rom` / `ROM` / `loner` are all rejected.
- **Implementation:** `is_valid_character_name` iterates `CLAN_TABLE` and
  rejects case-insensitive exact matches before the mob-collision loop,
  mirroring ROM src/comm.c:1713-1718.

### COMM-004 — Mob-keyword collision rejection (IMPORTANT)

- **Test:** `tests/integration/test_nanny_login_parity.py::test_name_validator_rejects_mob_keyword_collision`
  — installs a mob prototype with `player_name="dragon ancient red"` and
  asserts `is_valid_character_name("dragon")` / `("ancient")` are False
  while `is_valid_account_name("dragon")` stays True.
- **Implementation:** new `mud/account/account_service.py:is_valid_character_name`
  layered on top of `is_valid_account_name`, iterating `mob_registry` and
  using `mud.world.char_find.is_name`. `create_character` and
  `mud/net/connection.py:_run_character_creation_flow` switched to the new
  helper; existing account-name callers (`create_account`,
  `login_with_host`, `list_characters`) keep syntactic-only validation.
- **Test fallout:** `tests/test_account_auth.py` was using stock
  RPG-flavour names (`Zeus`, `Nomad`, `Queen`, `Guardian`) that
  legitimately collide with real game mob keywords. ROM rejects those
  names too — per AGENTS.md "test contradicting ROM C is a bug in the
  test." Renamed to invented non-colliding tokens (`Borogon`, `Plumlux`,
  `Pelvex`, `Quorblix`).

### COMM-003 — `check_parse_name` length floor (IMPORTANT)

- **Test:** `tests/integration/test_nanny_login_parity.py::test_name_validator_matches_rom_check_parse_name`
  rewritten to assert ROM's `< 2` bound (`Bo` accepted, `a` rejected). The
  prior assertion `is_valid_account_name("xy") is False` had locked in the
  buggy `< 3` Python behaviour with a docstring misreading ROM
  (`src/comm.c:1729` is `strlen < 2`). Per AGENTS.md "test contradicting ROM
  C is a bug in the test."
- **Implementation:** `mud/account/account_service.py:591` — bound flipped
  from `< 3` to `< 2`.

### COMM-001 — `bust_a_prompt` rendering (CRITICAL)

- **Test:** `tests/integration/test_prompt_rom_parity.py` (8 cases — default,
  custom token expansion, AFK, `%%`, alignment word vs numeric, `%r` room
  name, `do_prompt` storage field).
- **Implementation:** `mud/utils/prompt.py:bust_a_prompt(char) -> str`. Wired
  into both telnet game-loop call sites in `mud/net/connection.py`. ANSI
  rendering applied in `send_prompt` so `{p`/`{x` wrappers don't leak.
- **Side fix:** `mud/commands/auto_settings.py:do_prompt` now writes to
  `char.prompt` (mirrors ROM `ch->prompt`) instead of
  `pcdata.prompt` (which is the colour triplet). Five existing tests in
  `test_player_prompt.py` / `test_player_auto_settings.py` /
  `test_config_commands.py` updated to assert the correct field — they were
  asserting the buggy behaviour.

---

## Phase 5 — Completion

- Tracker row `comm.c | P3 | ❌ Not Audited | 50%` will flip to
  `⚠️ Partial — non-networking audited` once COMM-001 / COMM-002 / COMM-003 /
  COMM-004 are closed (the four CRITICAL/IMPORTANT items). The MINORs may
  ship together or in a follow-up patch session.
- The "P3-6: comm.c (NOT AUDITED - 50%) — Different architecture" block at
  `ROM_C_SUBSYSTEM_AUDIT_TRACKER.md:1007-1018` is correct *for the networking
  layer* but underestimates the non-networking surface; will be revised to
  cite `COMM_C_AUDIT.md` and the deferred-by-design list.
