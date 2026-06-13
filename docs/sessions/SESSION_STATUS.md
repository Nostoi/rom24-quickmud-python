# Session Status — 2026-06-13 — MAGIC-022 (protection evil/good $N PERS) + MAGIC-016..021 cluster + TRIP-001 + FIGHT-063/064 + GET-014 + SAC-006 + GIVE-002 + GOSSIP-001/002 + TELL-008 + EMOTE-005 + COMPARE-001 + FIGHT-062 + REPORT-001 + CONSIDER-001 + PRACTICE-001 + CAST-010/011 + PASSWORD-001 + SAVE-001 + ORDER-002/003 + PICK-001/002 + BRANDISH-007; cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted —
  only deferred track-only DB2 rows remain)
- **Last completed**: MAGIC-022 — `protection_evil`/`protection_good`
  (`mud/skills/handlers.py`, 6 sites across the sibling pair) "$N is already
  protected." / "$N is protected from evil/good." now render via `act_format`
  ($N = PERS NPC short_descr + cap) instead of the baked keyword name, matching ROM
  `act(..., TO_CHAR)`. **A NEW enumerated batch of ~15 remaining baked-name
  spell-handler sites is now tracked in MAGIC_C_AUDIT.md** (faerie_fire, disarm, fly,
  frenzy, giant_strength, haste, infravision, pass_door, envenom, etc.) — same
  `act_format` fix, each ROM act-code to verify (v2.14.66). Before that: MAGIC-021 —
  `spell_change_sex` (`mud/skills/handlers.py:change_sex`)
  already-changed line now replicates ROM's literal `$s(?)` quirk exactly via
  `act_format("$N has already had $s(?) sex changed.", recipient=caster,
  actor=caster, arg2=victim)` — `$N` = victim PERS (cap), `$s` = the **caster's**
  possessive (a ROM bug the author flagged with "(?)"), + literal "(?)". Was baking
  victim name + "their" with no "(?)". A male caster sees "A green goblin has already
  had his(?) sex changed." **This CLOSES the MAGIC-016 baked-name spell-handler
  cluster** (armor/shield/bless/cures/curse/change_sex all ✅) (v2.14.65). Before
  that: MAGIC-020 — `spell_curse` object branch
  (`mud/skills/handlers.py:curse`) now capitalizes `$p` via `act_format` and
  broadcasts the "glows with a red/malevolent aura" lines TO_ALL (caster +
  `act_to_room`) instead of caster-only, matching ROM `act("$p …", ch, obj, NULL,
  TO_CHAR/TO_ALL)` (`src/magic.c:1737/1751/1773`). Cursing "a silver dagger" now
  shows "A silver dagger glows with a malevolent aura." to the whole room (was
  lowercase, caster-only). The MAGIC-016 spell-handler cluster is now down to ONE
  remaining member: `change_sex` (the literal `$s(?)` ROM quirk) (v2.14.64). Before
  that: MAGIC-019 — `cure_blindness`/`cure_disease`/`cure_poison`
  (`mud/skills/handlers.py`) "$N doesn't appear to be blinded/diseased/poisoned."
  lines now render via `act_format` ($N = PERS NPC short_descr + cap) instead of the
  baked keyword name, matching ROM `act(..., TO_CHAR)` (`src/magic.c:1608/1650/1694`).
  MAGIC-016 cluster progress — armor/shield/bless/cures ✅ done; only change_sex
  (literal `(?)` quirk) and curse-object remain OPEN (v2.14.63). Before that:
  MAGIC-018 — `spell_bless` (`mud/skills/handlers.py:bless`)
  cross-target lines "$N already has divine favor." / "You grant $N the favor of
  your god." now render via `act_format` ($N = PERS NPC short_descr + cap) instead
  of the baked keyword name, matching ROM `act(..., TO_CHAR)` (`src/magic.c:845,863`).
  Continues the MAGIC-016 spell-handler cluster — armor/shield/bless now done;
  change_sex (literal `(?)` quirk), cures, curse-object still tracked OPEN
  (v2.14.62). Before that: MAGIC-017 — `spell_shield` (`mud/skills/handlers.py:shield`)
  cross-target TO_CHAR "$N is already protected by a shield." now uses `act_format`,
  and the success TO_ROOM "$n is surrounded by a force shield." now uses
  `act_to_room` (replacing a hand-rolled name-baking loop with a "Someone"
  fallback), matching ROM `act(..., TO_CHAR/TO_ROOM)`. PERS short_descr + cap;
  invisible→"someone". Continues the MAGIC-016 spell-handler cluster (shield struck
  off the remaining list; frenzy/change_sex/cures/curse still OPEN) (v2.14.61).
  Before that: MAGIC-016 — `spell_armor` (`mud/skills/handlers.py:armor`)
  cross-target lines "$N is already armored." / "$N is protected by your magic."
  now render via `act_format` ($N = PERS NPC short_descr + cap) instead of the baked
  keyword name, matching ROM `act(..., ch, NULL, victim, TO_CHAR)`
  (`src/magic.c:763,776`). Casting armor on NPC "goblin"/"a green goblin" now shows
  "A green goblin is protected by your magic." (was "goblin is …"). **⚠️ Filed
  cluster (next agent):** the same baked-name pattern in shield / frenzy-divine-favor
  / change_sex (literal `(?)` ROM quirk!) / cure_blindness-disease-poison /
  curse-object handlers — each needs its ROM act() code verified before conversion
  (see MAGIC-016 row in MAGIC_C_AUDIT.md) (v2.14.60). Before that: TRIP-001 —
  `do_trip` (`mud/skills/handlers.py:trip`) three
  blocking messages now render via `act_format`: "$S feet aren't on the ground."
  (his/her/its, was "Their"), "$N is already down." (PERS short_descr + cap, was
  the keyword name), "$N is your beloved master." (was "They are your beloved
  master." — wrong pronoun AND "are" vs ROM "is"), matching ROM `act(..., TO_CHAR)`
  (`src/fight.c` do_trip). The handler already used act_format for its disarm/dirt
  lines — this was an inconsistency. Found applying the `act()`-rendering lens to
  fight.c skill commands (v2.14.59). Before that: FIGHT-064 — the kill/murder safety
  messages "$N is your
  beloved master." and "But $N looks so cute and cuddly..." now render via
  `act_format("$N …", arg2=victim)` in BOTH copies (`combat.py:_kill_safety_message`
  + `murder.py:_murder_safety_check`), matching ROM `act("$N …", ch, NULL, victim,
  TO_CHAR)` (`src/fight.c:1061,2707`). `$N` = PERS = NPC short_descr (capitalized),
  not the baked keyword name — a charmed PC killing NPC master "wizard"/"a dark
  wizard" now sees "A dark wizard is your beloved master." (was "wizard is …").
  Found applying the `$N`/PERS/ACT-CAP lens to the is_safe family (v2.14.58). Before
  that: FIGHT-063 — `do_backstab` (`mud/commands/combat.py`)
  "hurt and suspicious" rejection now renders via `act_format("$N is hurt and
  suspicious ... you can't sneak up.", arg2=victim)` — `$N` = PERS = the NPC
  short_descr (not the keyword name), capitalized — matching ROM
  `act(..., ch, NULL, victim, TO_CHAR)` (`src/fight.c:2946`). Was baking
  `victim.name` lowercase ("goblin sneaky is hurt…" vs ROM "A sneaky goblin is
  hurt…"). Found applying the `$N`/PERS/ACT-CAP lens to fight.c (v2.14.57). Before
  that: GET-014 — `do_get` (`mud/commands/inventory.py`) carry-limit
  messages now render via `act_format("$d: …", arg2=obj.name)` — `$d` = the FIRST
  keyword of `obj.name`, capitalized buf[0] — matching ROM `act("$d: you can't carry
  that many items.", ch, NULL, obj->name, TO_CHAR)`. Was baking the full lowercase
  `obj.name` keyword string ("relic ancient: …" vs ROM "Relic: …"). Closed the
  long-standing ⚠️ SIMILAR row in the audit's comparison table. Found applying the
  ACT-CAP/`$d` lens (v2.14.56). Before that: SAC-006 — `do_sacrifice`
  (`mud/commands/obj_manipulation.py`)
  rejection line ("$p is not an acceptable sacrifice.") and furniture line
  ("$N appears to be using $p.") now render via `act_format` so ROM's act() buf[0]
  capitalization applies — a lowercase object short_descr ("a blessed relic") shows
  "A blessed relic is not an acceptable sacrifice." (was lowercase). Found applying
  the CONSIDER-001 ACT-CAP lens to act_obj; the `$mself` reflexive was already
  faithful (object_pronoun+"self" = itself) (v2.14.55). Before that: GIVE-002 —
  `do_give` (`mud/commands/give.py`) four giver-facing
  rejection lines ("$N has $S hands full.", "$N can't carry that much weight.",
  "$N can't see it.", shopkeeper "Sorry, you'll have to sell that.") now render via
  `act_format` with ROM's `$N` (PERS name) + `$S` (possessive his/her/its) instead
  of a baked name + a `_victim_possessive` helper that wrongly returned "their" for
  sexless victims (ROM `$S` = "its"). Deleted the dead helpers. Found applying the
  EMOTE-005/TELL-008 pronoun lens to act_obj (v2.14.54). Before that: GOSSIP-002 —
  completed the global-channel PERS class:
  `do_grats`/`do_quote`/`do_question`/`do_answer`/`do_music`
  (`mud/commands/communication.py`) now PERS-mask `$n` per recipient via the
  `render` param added in GOSSIP-001, matching ROM `act_new("{t$n grats…", …,
  d->character, TO_VICT)`. All seven public channels (gossip/auction + these five)
  now mask an invisible/wiz-invis sender to "someone". `clantalk`/`immtalk` left as
  a low-value edge (immtalk = holylight-visible immortals) (v2.14.53). Before that:
  GOSSIP-001 — global channels `do_gossip`/`do_auction`
  (`mud/commands/communication.py`) now PERS-mask `$n` per recipient via a new
  backward-compatible `render` param on `broadcast_global` (`mud/net/protocol.py`),
  matching ROM's `descriptor_list` walk with `act_new("{d$n gossips…", …,
  d->character, TO_VICT)`. An invisible/wiz-invis gossiper now shows "Someone
  gossips" to listeners who can't see them, instead of leaking the name (the Python
  baked `char.name` into one shared message). **Remaining (filed, next agent):** the
  other global channels — grats/quote/question/answer/music — bake the name the same
  way; mechanical follow-up with the same `render=` pattern (v2.14.52). Before that:
  TELL-008 — `do_tell` (`mud/commands/communication.py`)
  teller-facing status lines now render the victim's gendered pronouns via
  `act_format` ($E=He/She/It, $S=his/her/its, $N=name) instead of the baked victim
  name + "they"/"their". Six messages (not-receiving / can't-hear / linkdead /
  AFK-NPC / AFK-PC / writing-note) matching ROM `act("$E …", ch, 0, victim,
  TO_CHAR)` (`src/act_comm.c`). E.g. `tell bob hi` (sexless, QUIET) → "It is not
  receiving tells." (was "Bob is not receiving tells."). Found applying the
  EMOTE-005 $n/PERS lens to the comm commands (v2.14.51). Before that: EMOTE-005 —
  `do_emote` (`mud/commands/communication.py`) self
  line now renders the actor's OWN NAME via `pers(char, char)` (e.g. "Bob nods"),
  not "You nods" — **correcting the false-premise EMOTE-002**. ROM `act()` does no
  `$n`→"You" conversion; `$n` → `PERS(ch, to)`, and `PERS(ch, ch)` = the actor's
  name (a char always sees itself). Proof: ROM `do_say` writes a *literal*
  "You say '%s'" for its self-line, redundant if `act()` did the conversion. Stock
  ROM emote shows the emoter their own name. Found by re-verifying the EMOTE-002 ✅
  against source (AGENTS.md re-verify rule); inverted its test (v2.14.50). Before
  that: COMPARE-001 — `do_compare` (`mud/commands/compare.py`)
  arg2-empty equipped-match (`_find_equipped_match`) now requires the **same
  item_type AND overlapping wear_flags** (`& ~ITEM_TAKE`), matching ROM
  `src/act_info.c:2323-2332`. The old code returned the first equipped non-weapon
  item for ARMOR, so "compare ring" wrongly compared against a worn helmet (no
  shared wear slot). Rewrote to iterate `char.equipment` with the overlap check.
  Found by re-verifying the "do_compare 100% COMPLETE" audit row (v2.14.49). Before
  that: FIGHT-062 — `do_flee` (`mud/commands/combat.py`) "$n has
  fled!" room broadcast now routes through `act_to_room(was_in, "$n has fled!",
  char)` instead of a hand-rolled `desc.send` loop that baked `char.name` (no `$n`
  PERS masking) and skipped descriptor-less witnesses (NPCs got no TRIG_ACT, the
  opponent left behind got nothing). Matches ROM `act("$n has fled!", TO_ROOM)`
  (`src/fight.c:3005-3007`). Sibling of REPORT-001 from the hand-rolled-broadcast
  sweep (v2.14.48). Before that: REPORT-001 — `do_report` (`mud/commands/info.py`) room
  broadcast now routes through `act_to_room(room, "$n says 'I have …'", char)`
  instead of a hand-rolled `desc.send` loop that baked `char.name` (no `$n` PERS
  masking), skipped descriptor-less occupants (NPCs got no TRIG_ACT), and used
  `!=` identity. Matches ROM `act("$n says ...", TO_ROOM)` (`src/act_info.c:2670`)
  — INV-025/027 PERS masking + INV-001 single-delivery + TRIG_ACT. Found by
  re-verifying the "do_report 100% COMPLETE" audit row against source (v2.14.47).
  Before that: CONSIDER-001 — `do_consider` (`mud/commands/consider.py`) now
  capitalizes the rendered difficulty line via `capitalize_act_line`, matching ROM
  `act()` `buf[0] = UPPER(buf[0])` (`src/comm.c:2379`). For the four messages
  beginning with `$N`, the lowercase victim short_descr's first letter is now
  capitalized ("a fierce goblin" → "A fierce goblin is no match for you."). Found by
  re-verifying the "do_consider 100% COMPLETE" audit row against source. `do_train`
  and `do_quit` re-verified this session and confirmed faithful (v2.14.46). Before
  that: PRACTICE-001 — `do_practice` (`mud/commands/advancement.py`)
  failure-gate order now matches ROM (`src/act_info.c`): the ACT_PRACTICE
  trainer-presence gate ("You can't do that here.") fires *before* the
  `practice <= 0` and spell-validity gates (was after). A player not at a trainer
  who also had 0 practices / named an invalid skill saw the wrong message. Moved
  the trainer gate to right after IS_AWAKE (awake → trainer → sessions → spell).
  Found by re-verifying the "do_practice 100% COMPLETE" audit claim against source
  (v2.14.45). Before that: CAST-011 — `do_cast` (`mud/commands/combat.py`) now broadcasts
  the spell incantation to the room via `broadcast_spell_words(char, skill.name)`
  (skipping `ventriloquate`), matching ROM `src/magic.c:544-545`
  `if (str_cmp(name, "ventriloquate")) say_spell(ch, sn)`. The helper existed
  (`mud/skills/say_spell.py`, with class-based garbling + INV-001 single-delivery)
  but `do_cast` never called it — casting was silent to the room. Caster still
  receives nothing (FINDING-013 preserved) (v2.14.44). Before that: CAST-010 —
  `do_cast` (`mud/commands/combat.py`) cast-lag now
  uses the spell's own `beats` (`apply_wait_state(char, skill.beats)`) instead of a
  flat `get_pulse_violence()` (12), matching ROM `src/magic.c:547`
  `WAIT_STATE(ch, skill_table[sn].beats)`. 34 of ~120 spells have beats≠12 (fly=18,
  enchant armor=24, mass healing=36) so they were mis-lagged; 19 beats-0 spells were
  over-lagged. ROM uses the RAW beats (no HASTE/SLOW for casting), so the fix reads
  `skill.beats` directly, not `_compute_skill_lag` (v2.14.43). Before that:
  PASSWORD-001 — `do_password` (`mud/commands/character.py`)
  wrong-password penalty now uses `apply_wait_state(ch, 40)` (UMAX) instead of
  `ch.wait = 40` (assignment), matching ROM `src/act_info.c:2895` `WAIT_STATE(ch, 40)`
  — a higher existing wait is preserved, not lowered. Sibling of SAVE-001 from the
  same ROM-WAIT_STATE-site cross-check (v2.14.42). Before that: SAVE-001 — `do_save`
  (`mud/commands/session.py`) now applies
  `apply_wait_state(ch, 4 * get_pulse_violence())` (=48) after the save+message,
  matching ROM `src/act_comm.c:1530` `WAIT_STATE(ch, 4 * PULSE_VIOLENCE)`. The code
  saved but applied no wait (the audit doc's "+ WAIT_STATE ✅ 100%" was a stale
  false-✅, corrected). Found by an enumerated ROM-WAIT_STATE-site cross-check
  (move_char/do_recall confirmed faithful; do_save was the gap; do_password noted
  below). **Filed for next agent:** `do_password` (`mud/commands/character.py`) uses
  `ch.wait = 40` (assignment) where ROM `src/act_info.c:2895` uses
  `WAIT_STATE(ch, 40)` = UMAX — a higher existing wait would be lowered (minor,
  PASSWORD-001 candidate, see Outstanding) (v2.14.41). Before that: ORDER-003 —
  `do_order` (`mud/commands/group_commands.py`)
  single-target gate now includes ROM's third "Do it yourself!" clause
  `IS_IMMORTAL(victim) && victim->trust >= ch->trust` (`src/act_comm.c`), via
  `victim.is_immortal() and victim.trust >= char.trust`. A charmed immortal whose
  trust ≥ the orderer's is now refused (a normal charmed mob is unaffected, since
  `is_immortal()` = ROM `get_trust >= 52`) (v2.14.40). Before that: ORDER-002 —
  `do_order` (`mud/commands/group_commands.py`) now
  applies `apply_wait_state(char, get_pulse_violence())` (=12) on both the
  single-target and `order all` paths when an order lands, matching ROM
  `src/act_comm.c` `if (found) { WAIT_STATE(ch, PULSE_VIOLENCE); ... }`. The code
  had a `# Note: WAIT_STATE not implemented yet` stub (and the audit doc's "✅
  WAIT_STATE" claim was a stale false-✅, now corrected). No-follower path stays
  lag-free, as ROM. **Also filed ORDER-003 (🔄 OPEN):** the single-target "Do it
  yourself!" gate omits ROM's `IS_IMMORTAL(victim) && victim->trust >= ch->trust`
  clause (v2.14.39). Before that: PICK-002 — `do_pick` (`mud/commands/doors.py`) WAIT_STATE now
  uses `apply_wait_state(char, beats)` (canonical `UMAX` helper) with the pick-lock
  skill beats (12, data-driven from the registry), matching ROM
  `src/act_move.c:856` `WAIT_STATE(ch, skill_table[gsn_pick_lock].beats)`. The old
  code did `char.wait += 24` — wrong value (24 vs 12) and additive (stacked) instead
  of `UMAX`. Adjacent to PICK-001's TODO stubs in the same function (v2.14.38).
  Before that: PICK-001 — `do_pick` (`mud/commands/doors.py`, the live
  `pick` command) now calls `check_improve(char, "pick lock", FALSE/TRUE, 2)` at
  all four ROM sites (failure src/act_move.c:872; portal/container/door success
  908/946/982). The code shipped with four `# TODO: Implement check_improve` stubs
  — the per-file audit's "do_pick 100% — check_improve FIXED" rows were a **stale
  false-✅** (now corrected in `ACT_MOVE_C_AUDIT.md`). Identical class to RECALL-002.
  Surfaced by the post-BRANDISH-007 check_improve-site sweep. **Out-of-scope, filed
  for next agent:** there is a second, fully-featured `mud/skills/handlers.py:pick_lock`
  that also handles check_improve but is NOT the dispatched command — the do_pick /
  pick_lock duplication should be reconciled (delegate, like SNEAK-001/HIDE-001 did)
  (v2.14.37). Before that: BRANDISH-007 — `do_brandish` (`mud/commands/magic_items.py`)
  now calls `check_improve(ch, "staves", True, 2)` **inside** the per-target loop,
  once per cast, matching ROM `src/act_obj.c:2050-2052`. The previous code hoisted
  it to run once after the loop, so AoE staves (TAR_CHAR_OFFENSIVE/DEFENSIVE spells
  hitting N people) under-counted skill-learn rolls and under-drew the shared MM RNG
  (`check_improve` rolls `number_range(1,1000)` for PCs) by N−1. Surfaced by a
  do_quaff/do_recite/do_brandish/do_zap sibling sweep of the magic-item command
  cluster after EAT-007 (do_recite and do_zap are single-target, no loop, confirmed
  faithful) (v2.14.36). Before that: EAT-007 — `do_eat` (`mud/commands/consumption.py`) poison
  branch now derives the affect's level/duration from the **raw** `value[0]`
  (ROM act_obj.c:1347-1348: `level=number_fuzzy(value[0])`, `duration=2*value[0]`)
  instead of the Python's `value[0] if value[0] else 1` substitution — so
  poisoned food with `value[0]==0` yields `duration=0` (was 2). `number_fuzzy` is
  still called once either way, so RNG alignment holds (v2.14.35). Before that:
  DRINK-010 — `do_drink` (`mud/commands/consumption.py`) now
  decrements `value[1]` whenever `value[0] > 0` (ROM act_obj.c:1276-1277),
  removing a spurious `item_type == DRINK_CON` guard the Python had added; a
  fountain with positive capacity now drains (and may go negative, as ROM does)
  instead of staying frozen. Stock ROM fountains use `value[0]==0` so this is
  invisible for them; only capacity-bearing fountains diverged (v2.14.34). Before
  that: WIZ-052 — `do_mstat` (`mud/commands/imm_search.py`) now reads
  the `pcdata.condition` array by `COND_*` enum slot
  (`thirst=condition[Condition.THIRST]`, `hunger=[HUNGER]`, `full=[FULL]`,
  `drunk=[DRUNK]`) instead of by display order (`[0]/[1]/[2]/[3]`). The array is
  enum-keyed (`DRUNK=0, FULL=1, THIRST=2, HUNGER=3`), so the old positional read
  scrambled every label — Thirst printed the DRUNK slot, Hunger the FULL slot,
  etc. (ROM act_wiz.c:1637-1641). Surfaced by a post-EAT-006 sibling sweep for
  other `condition[]` mis-indexers (v2.14.33). Before that: EAT-006 — `do_eat`
  (`mud/commands/consumption.py`) now
  restores hunger/fullness by calling `gain_condition(ch, Condition.FULL/HUNGER,
  …)` (as `do_drink` already did), instead of an inline `min(48, current+value)`
  clamp that bypassed `gain_condition`'s `level >= LEVEL_IMMORTAL` early-return
  and `condition == -1` permanent-satiation sentinel (ROM act_obj.c:1326-1327 /
  update.c:367-377). Immortals eating food no longer have conditions bumped, and
  a -1 slot is preserved (v2.14.32). Before that: INV-049 — mob special
  procedures are now dispatched INSIDE
  the `mobile_update` per-mob loop (`mud/ai/__init__.py`) at the ROM position
  (`src/update.c:425-431`): after the charm/empty-area gates, before shop-gold,
  triggers, scavenge, and wander, with a TRUE result `continue`ing to skip the
  rest of that mob's tick. The previous code ran `run_npc_specs()` as a separate
  pass over `room_registry` after the whole loop, bypassing the charm/empty gates
  and the TRUE-suppression and reordering the shared MM RNG draws.
  `run_npc_specs()` is kept as a test/manual entry point only and removed from
  `game_tick` (v2.14.31). Before that: GL-044 — `mobile_update` wander now draws its direction
  with `number_bits(5)` (single 5-bit roll, aborts when >5 → wanders 6/32 of
  eligible ticks), mirroring ROM `src/update.c:498`. Previously used
  `number_door()` (the do_flee primitive, `src/db.c:3541`) which re-rolls until
  ≤5 and never aborts — mobs wandered ~5× too often and the variable reroll loop
  desynced the shared Mitchell-Moore stream (v2.14.30). Before that: INV-048 —
  auto-assist (`check_assist`) now fires from
  exactly one site, `game_loop.violence_tick` (ROM `src/fight.c:90`,
  `violence_update`). Removed the erroneous inline `check_assist` from
  `mud/ai/aggressive.py:aggressive_update` — ROM `aggr_update` (`src/update.c:1136`)
  ends each aggression with a bare `multi_hit` and never assists, so assists land
  on the next violence tick, not the aggression pulse. The stray call started
  assists a tick early and drew extra coins from the shared MM RNG stream
  (v2.14.29). Earlier this session: INV-020 step (v) carried+worn object extract
  on every non-death extract leg (v2.14.28, `34519468`), INV-020 step (iv)
  `stop_fighting(both=True)` on quit+disconnect (v2.14.27, `20c22cb1`), INV-047
  multi-path extract-ref cleanup (v2.14.26, `cb67db83`), INV-047 single-path
  mprog_target quirk (v2.14.25), MOBCMD-019 (v2.14.24), xdist flakes (v2.14.23)
- **Pointer to latest summary**: [SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md](SESSION_SUMMARY_2026-06-12_XDIST_FLAKE_FIXES.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.66 |
| Tests | protection-pers 2/2, buffs 27/27, full suite last green 5727 passed / 4 skipped (v2.14.65) |
| MAGIC-022 status | ✅ FIXED protection evil/good (`$N` PERS ×6); ⚠️ ~15-site baked-name batch tracked |
| MAGIC-021 status | ✅ FIXED change_sex ($s(?) quirk replicated); **MAGIC-016 cluster CLOSED** |
| MAGIC-020 status | ✅ FIXED curse-object ($p cap + TO_ALL aura broadcast) |
| MAGIC-019 status | ✅ FIXED cure blindness/disease/poison (`$N` PERS) |
| MAGIC-018 status | ✅ FIXED bless (`$N` PERS TO_CHAR ×2) |
| MAGIC-017 status | ✅ FIXED shield (`$N` TO_CHAR + `$n` TO_ROOM PERS) |
| MAGIC-016 status | ✅ FIXED armor (`$N` PERS); ⚠️ frenzy/change_sex/cures/curse baked-name cluster still OPEN |
| TRIP-001 status | ✅ FIXED (do_trip 3 blocking msgs use $S/$N pronouns via act_format) |
| FIGHT-064 status | ✅ FIXED (kill/murder safety msgs use $N PERS short_descr; both combat.py + murder.py copies) |
| FIGHT-063 status | ✅ FIXED (backstab hurt msg uses $N PERS short_descr + cap via act_format) |
| GET-014 status | ✅ FIXED (carry-limit msg uses $d first keyword + capitalization via act_format; closes ⚠️ SIMILAR) |
| SAC-006 status | ✅ FIXED (sacrifice rejection/furniture msgs capitalize object name via act_format) |
| GIVE-002 status | ✅ FIXED (give rejection lines use $N/$S pronouns via act_format; sexless → "its" not "their") |
| GOSSIP-001/002 status | ✅ FIXED all 7 public channels (gossip/auction/grats/quote/question/answer/music PERS-mask `$n`); clan/immtalk = low-value edge |
| TELL-008 status | ✅ FIXED (tell status lines use $E/$S/$N pronouns via act_format, not baked name + "they") |
| EMOTE-005 status | ✅ FIXED (emote self renders actor name via PERS, not "You"; reverts false-premise EMOTE-002) |
| COMPARE-001 status | ✅ FIXED (do_compare equipped-match requires same item_type + overlapping wear_flags) |
| FIGHT-062 status | ✅ FIXED (do_flee "$n has fled!" uses act_to_room — PERS mask + single-delivery + TRIG_ACT) |
| REPORT-001 status | ✅ FIXED (do_report room broadcast uses act_to_room — PERS mask + single-delivery + TRIG_ACT) |
| CONSIDER-001 status | ✅ FIXED (do_consider capitalizes act() buf[0]; $N-first messages cap the victim name) |
| PRACTICE-001 status | ✅ FIXED (do_practice trainer gate precedes session/spell gates, matching ROM order) |
| CAST-011 status | ✅ FIXED (do_cast broadcasts say_spell to room, except ventriloquate; was silent) |
| CAST-010 status | ✅ FIXED (do_cast uses per-spell beats for WAIT_STATE, not flat PULSE_VIOLENCE) |
| PASSWORD-001 status | ✅ FIXED (do_password wrong-pwd penalty uses UMAX, not =40 assignment) |
| SAVE-001 status | ✅ FIXED (do_save applies WAIT_STATE(ch, 4*PULSE_VIOLENCE=48); stale false-✅ corrected) |
| ORDER-003 status | ✅ FIXED (do_order gate adds IS_IMMORTAL(victim) && trust>=orderer clause) |
| ORDER-002 status | ✅ FIXED (do_order applies WAIT_STATE(ch, PULSE_VIOLENCE=12) on landed orders; stale false-✅ corrected) |
| PICK-002 status | ✅ FIXED (do_pick WAIT_STATE uses beats=12 + UMAX, data-driven; was +=24 additive) |
| PICK-001 status | ✅ FIXED (do_pick wires check_improve at all 4 ROM sites; stale false-✅ corrected) |
| BRANDISH-007 status | ✅ FIXED (do_brandish check_improve fires inside per-target loop, once per cast — AoE skill-learn + RNG draw count) |
| EAT-007 status | ✅ FIXED (do_eat poison level/duration use raw value[0], no `or 1` substitution) |
| DRINK-010 status | ✅ FIXED (do_drink drains value[1] on value[0]>0 regardless of item type; fountains included) |
| WIZ-052 status | ✅ FIXED (do_mstat condition line reads COND_* enum slots, not display order) |
| EAT-006 status | ✅ FIXED (do_eat delegates condition restore to gain_condition; immortal/-1-sentinel guards honored) |
| INV-049 status | ✅ ENFORCED (spec_fun dispatched inside mobile_update — gated by charm/empty, TRUE-result suppresses rest of tick; no separate run_npc_specs pass) |
| GL-044 status | ✅ FIXED (mobile_update wander uses number_bits(5), aborts >5; not number_door) |
| INV-048 status | ✅ ENFORCED (check_assist fires only from violence_tick; aggr_update never assists) |
| INV-020 status | ✅ ENFORCED (full extract_char chain — steps i–v — on all extract legs: raw_kill, _extract_character, quit, disconnect) |
| INV-047 status | ✅ ENFORCED (extract-ref cleanup on all paths) |
| INV-046 status | ✅ ENFORCED (phantom-registry class fully closed + grep-guarded) |
| Per-file OPEN gaps | 0 live (DB2-004/005 deferred track-only) |
| Active focus | Cross-file invariants probe |

## Next Intended Task

The per-file audit tracker has no live `🔄 OPEN` rows; cross-file invariants is the
primary pass. Use the probe-then-scope method (read ROM C contract → read Python
equivalent → one failing test → close as a single gap or file as the next free
INV-NNN). Candidates:

1. **Mob memory / hunt** — `src/fight.c` ATTACK_BACK and the hunt/track loop vs the
   Python AI tick (not yet probed).
2. **Position-transition edges** — `update_pos` / `stop_fighting` ordering across
   damage, sleep, rest, and death.

Confirmed-faithful (do not re-probe without new evidence): weather/time fan-out and
`update_handler` pulse cadence (locked by `tests/test_game_loop_order.py` +
`tests/integration/test_weather_time.py`); `stop_fighting` position semantics and
mob prototype-count recompute (recall-oracle confirmed this session).

**Process reminder:** after every phantom-class / list-walk fix, re-grep the whole
`mud/` tree before trusting a hand-built site inventory — family 3a's inventory
missed 2 sites that the family-3b re-grep caught.
