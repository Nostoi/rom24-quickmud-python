# Session Summary — 2026-06-19 — /loop gap-closer: ACT_COMM group/follow (5/5)

## Scope

A `/loop` gap-closer session targeting 5 gaps, picking up from the prior loop
(WEAR-012/LOOK-008/LOOK-009/SCORE-001/HANDLER-007, v2.14.139-143). The per-file
audit tracker is exhausted, so all five gaps this loop were **probe-surfaced**:
a group/follow-messaging probe read ROM `src/act_comm.c` (do_follow / do_group /
add_follower / stop_follower) against the Python port and found five genuine
divergences, all in the same `act()`-rendering / PERS-masking / scan-domain
family. Each was closed TDD-first (one failing test → fix → commit) per
`/rom-gap-closer`. Push-at-end was requested.

## Outcomes

### `GROUP-002` — ✅ FIXED (2.14.144)

- **Python**: `mud/commands/group_commands.py:228-247` (do_group charm branch)
- **ROM C**: `src/act_comm.c:1833-1835`
- **Gap**: charmed-`ch` group rejection went to the wrong recipient and dropped `$m`.
- **Fix**: ROM `act_new("You like your master too much to leave $m!", ch, NULL, victim, TO_VICT)` delivers **to the victim** with `$m` = the charmed ch's objective pronoun; ch gets nothing. Python returned the (pronoun-less) line to `char`. Now delivers TO_VICT via `_send_to_char_sync` with `_object_pronoun(_sex_of(char))`, returns `""`. (Faithful dead-code replication — the branch is effectively unreachable because a charmed char has a master, tripping the earlier "But you are following someone else!" guard.)
- **Tests**: `tests/integration/test_group_broadcasts.py::test_do_group_charmed_ch_rejection_goes_to_victim_with_pronoun` — pass.

### `GROUP-003` — ✅ FIXED (2.14.145)

- **Python**: `mud/commands/group_commands.py:186-200` (do_group no-arg display)
- **ROM C**: `src/act_comm.c:1787-1802`
- **Gap**: `group` display only scanned `room.people` + a nonexistent `leader.followers`, dropping cross-room group members.
- **Fix**: iterate `character_registry` (the `char_list` equivalent) and `add_member` each `is_same_group` hit. Corrects **membership** (the observable bug); iteration order is registry append-order, which matches neither old code nor ROM head-insert exactly — order was not the divergence.
- **Tests**: `tests/integration/test_do_group_notification.py::test_do_group_display_includes_cross_room_members` — pass.

### `FOLLOW-004` — ✅ FIXED (2.14.146)

- **Python**: `mud/characters/follow.py:add_follower` / `stop_follower`
- **ROM C**: `src/act_comm.c:1605`, `:1627`
- **Gap**: the follower-facing TO_CHAR lines (`You now follow $N.` / `You stop following $N.`) baked `_display_name(master)` — no PERS masking, leaking an invisible master's name to its (often charmed) follower.
- **Fix**: render both via `act_format("…$N.", recipient=follower, arg2=master)` (the `$N`→`_pers(arg2, recipient)` masking path). Removed the now-unused `_display_name` helper from `follow.py`.
- **Tests**: `tests/integration/test_follow_can_see_gating.py::test_follow_004_add_follower_to_char_masks_invisible_master_name`, `::test_follow_004_stop_follower_to_char_masks_invisible_master_name` — pass.

### `FOLLOW-005` — ✅ FIXED (2.14.147)

- **Python**: `mud/commands/group_commands.py:do_follow` (charm + NOFOLLOW branches)
- **ROM C**: `src/act_comm.c:1558`, `:1576-1577`
- **Gap**: `do_follow`'s two rejection lines (`But you'd rather follow $N!` / `$N doesn't seem to want any followers.`) baked names — no PERS masking, no sentence-start capitalization. The charm line is genuinely reachable (charmed follower of an invisible master); the NOFOLLOW line is practically unreachable (`get_char_room` won't target an unseen victim) but takes the same fix.
- **Fix**: both branches render via `act_format(…, recipient=char, arg2=target)` (PERS `$N` + INV-029 first-letter cap).
- **Tests**: `tests/integration/test_follow_can_see_gating.py::test_follow_005_do_follow_charm_rejection_masks_invisible_master` — pass.

### `GROUP-004` — ✅ FIXED (2.14.148)

- **Python**: `mud/commands/group_commands.py:_class_who_name` + display loop
- **ROM C**: `src/act_comm.c:1794-1795`
- **Gap**: the display's class column used `getattr(gch, "class_name", "???")[:3]` — `class_name` doesn't exist, so **every** PC rendered "???".
- **Fix**: new `_class_who_name(gch)` resolves `CLASS_TABLE[gch.ch_class].who_name` (mirroring the `do_who` lookup in `info_extended.py`); mobs still show "Mob". Also corrected a test-isolation slip introduced in the GROUP-003 test (`c8fabe02`): a doubled `character_registry.extend(snapshot)` + stray `room_registry.pop(9411)`.
- **Tests**: `tests/integration/test_do_group_notification.py::test_do_group_display_uses_class_who_name` — pass.

## Outstanding

- **`GROUP-005` — 🔄 OPEN** (filed in `ACT_COMM_C_AUDIT.md`). The **same PERS-masking bug class** in `do_group`'s own display and add/remove broadcasts, walked past while closing GROUP-002/003/004 (loop was at its 5/5 target). Three sites: header `leader_name` (`group_commands.py:154`; ROM `PERS(leader, ch)`, `:1781`), per-member `gch_name` (`:188`; ROM `capitalize(PERS(gch, ch))`, `:1796`), and the add/remove broadcasts (`:233-256`; `_display_name(char)`/`_display_name(victim)` instead of `act()`-rendered `$n`/`$N`). Fix shape: use the existing `_pers_gated` helper (+capitalize on the member line) and convert the broadcasts to `act_format`/`act_to_room` like GROUP-002. **This is the obvious next gap-closer target.**

## Files Modified

- `mud/commands/group_commands.py` — GROUP-002/003/004/FOLLOW-005; new `_class_who_name`.
- `mud/characters/follow.py` — FOLLOW-004; removed unused `_display_name`.
- `tests/integration/test_group_broadcasts.py` — GROUP-002 test.
- `tests/integration/test_do_group_notification.py` — GROUP-003/004 tests + isolation fix.
- `tests/integration/test_follow_can_see_gating.py` — FOLLOW-004 (×2) / FOLLOW-005 tests.
- `docs/parity/ACT_COMM_C_AUDIT.md` — flipped rows GROUP-002/003/004, FOLLOW-004/005 ✅; filed GROUP-005 OPEN; corrected stale "iterates character_registry equivalent" note.
- `CHANGELOG.md` — Fixed entries for all five.
- `pyproject.toml` — 2.14.143 → 2.14.148.

## Test Status

- Group/follow area suites — all green throughout.
- **Full suite: 5856 passed, 4 skipped (`PYTEST_EXIT=0`, captured directly, ~6m17s).**
- `ruff check` clean on every touched file.

## Next Steps

Close **GROUP-005** (the adjacent do_group PERS-masking gap) via `/rom-gap-closer`
— it's documented and the obvious continuation of this loop. After that, the
cross-file / divergence-class sweep remains the active pass: probe fresh surfaces
(give/put-to-mob, do_split gold math, weather/time, OLC) with C-oracle-vs-pyreplay
scripts. Durable lesson reinforced this session: **green ≠ diff-clean** — a doubled
`extend(snapshot)` shipped past area-tests + ruff + detect_changes in `c8fabe02`;
scan the cumulative diff before pushing.
