# Session Status — 2026-06-13 — MAGIC-044 (blindness room $n PERS) + MAGIC-043 (envenom room broadcast PERS) + MAGIC-042 (faerie_fog reveal PERS) + MAGIC-041 (chill_touch room $n PERS) + MAGIC-040 (cure room broadcast $n PERS) + MAGIC-039 (charm_person PERS) + MAGIC-038 (demonfire demons-of-Hell PERS+TO_ROOM) + MAGIC-037 (demonfire curse-tail $N) + MAGIC-036 (dispel TO_ROOM PERS+$S) + MAGIC-035 (curse/dispel TO_CHAR $N PERS) + MAGIC-034 (detect_* cluster $N PERS) + MAGIC-033 (know_alignment act semantics) + MAGIC-032 (sanctuary $N PERS) + MAGIC-031 (slow/stone_skin $N PERS) + MAGIC-030 (sleep silent gates) + MAGIC-029 (envenom-skill $p cap) + MAGIC-028 (plague $N PERS, MAGIC-022 batch fully closed) + MAGIC-027 (faerie_fire silent) + MAGIC-026 (object $p cap) + FIGHT-065 (disarm no-weapon literal) + MAGIC-025 (fly/infravision/pass_door $N PERS) + MAGIC-024 (giant_strength/haste $N/$E PERS) + MAGIC-022/023 + MAGIC-016..021 cluster + TRIP-001 + FIGHT-063/064 + GET-014 + SAC-006 + GIVE-002 + GOSSIP-001/002 + TELL-008 + EMOTE-005 + COMPARE-001 + FIGHT-062 + REPORT-001 + CONSIDER-001 + PRACTICE-001 + CAST-010/011 + PASSWORD-001 + SAVE-001 + ORDER-002/003 + PICK-001/002 + BRANDISH-007; cross-file invariants is the active pass

## Current State

- **Active focus**: Cross-file invariants pass (per-file audit tracker exhausted —
  only deferred track-only DB2 rows remain)
- **Last completed**: MAGIC-044 — `blindness`'s "$n appears to be blinded." room
  broadcast (`mud/skills/handlers.py:blindness` ~1672) now uses `act_to_room(room,
  "$n …", target, exclude=target)` — actor is the blinded victim, `$n` = PERS(victim)
  cap — instead of a hand-rolled loop baking `target.name` (with a "Someone" ternary
  that masked visible NPCs), matching ROM `act(…, TO_ROOM)` (`src/magic.c:889`). The
  MAGIC-003 fix had converted the delivery channel but left the baked-name loop.
  Found by the post-MAGIC-043 verification sweep (commands/ confirmed clean of baked
  `$n` patterns). Existing PC-target test stays green (v2.14.89). Before that:
  MAGIC-043 — `envenom`'s two room broadcasts (food "treats $p
  with deadly poison", weapon "coats $p with deadly venom", `mud/skills/handlers.py`
  ~4099/~4203) now use `act_to_room(room, "$n … $p …", caster, arg1=obj,
  exclude=caster)` — $n = PERS(caster), $p = obj — instead of pre-baked
  `_character_name`/`short_descr` strings, matching ROM `act(…, TO_ROOM)`
  (`src/act_obj.c:887/946`). An NPC caster now renders its short_descr. **This clears
  the post-MAGIC-022 act()-lens baked-name tail in `handlers.py`** (the systematic
  `_send_to_char(caster, f"{name}…")` / hand-rolled-room-loop grep is now empty for
  spell handlers) (v2.14.88). Before that: MAGIC-042 — `faerie_fog`'s "$n is revealed!" per-revealed-char
  broadcast (`mud/skills/handlers.py:faerie_fog` ~4304) now uses `act_to_room(room,
  "$n is revealed!", occupant, exclude=occupant)` for per-recipient PERS instead of
  a pre-baked `_character_name` string passed to `_act_room`, matching ROM
  `act(…, TO_ROOM)` (`src/magic.c:2850`). NPC short_descr now renders capitalized.
  The spell's "conjures a cloud" line already used act_to_room. Existing PC-target
  test stays green. **Remaining act()-lens tail (filed in MAGIC-042 row):** envenom
  room broadcasts ("treats/coats $p with deadly poison/venom") (v2.14.87).
  Before that: MAGIC-041 — `chill_touch`'s "$n turns blue and shivers."
  room broadcast (`mud/skills/handlers.py:chill_touch` ~2393) now uses
  `act_to_room(room, "$n …", target, exclude=target)` — actor is the chilled victim,
  `$n` = PERS(victim) cap — instead of a hand-rolled loop baking the keyword `name`,
  matching ROM `act(…, TO_ROOM)` (`src/magic.c:1417`). The caster (not the victim)
  still receives it. Existing PC-target test stays green. **Remaining act()-lens tail
  (filed in MAGIC-041 row):** faerie_fog "$n is revealed!" + envenom room broadcasts
  (v2.14.86). Before that: MAGIC-040 — `cure_blindness` ("$n is no longer blinded.")
  and `cure_poison` ("$n looks much better.") room broadcasts
  (`mud/skills/handlers.py`) now use `act_to_room(room, "$n …", victim,
  exclude=victim)` — the actor is the cured victim, so `$n` = PERS(victim) cap —
  instead of a hand-rolled loop baking the keyword `name`, matching ROM
  `act(…, TO_ROOM)` (`src/magic.c:1062/1702`). PC-victim + INV-025 cancellation-mask
  tests stay green. Found by the continuing act()-lens sweep (v2.14.85). Before that:
  MAGIC-039 — `charm_person`'s two success messages
  (`mud/skills/handlers.py:charm_person`) now render via `act_format`: TO_VICT
  "Isn't $n just so nice?" ($n = PERS caster seen by victim) + TO_CHAR "$N looks at
  you with adoring eyes." ($N = PERS victim, cap), matching ROM
  (`src/magic.c:1388/1390`) instead of the baked `actor_name`/`target_name`. Found
  by the continuing act()-lens sweep. The existing PC-name charm test stays green
  (v2.14.84). Before that: MAGIC-038 — `demonfire`'s "demons of Hell" broadcast
  (`mud/skills/handlers.py:demonfire` ~2986) now renders via `act_to_room`/`act_format`
  ($n/$N PERS) with ROM's TO_ROOM topology — the "calls forth" line is TO_ROOM
  (every occupant except the actor, **victim included**) and "has assailed you" is
  TO_VICT ($n PERS to victim). The Python had baked both names and excluded the
  victim from the room loop, so the victim never saw "calls forth". Re-baselined the
  demonfire damage test (victim now gets "calls forth" at messages[0]). Matches ROM
  `spell_demonfire` (v2.14.83). Before that: MAGIC-037 — `demonfire`'s curse-tail "$N looks very
  uncomfortable." line (`mud/skills/handlers.py:demonfire` ~3031) now renders via
  `act_format` ($N = PERS victim short_descr, cap) instead of the baked keyword
  `name`. ROM `spell_demonfire` ends by calling `spell_curse(...)`, whose line is
  `act("$N …", TO_CHAR)` (`src/magic.c:1801`). Found by the continuing act()-lens
  sweep. **Filed next (MAGIC-038):** demonfire's own "demons of Hell" lines
  (`handlers.py:~2994/2996`) bake names AND the Python excludes the victim from the
  TO_ROOM loop where ROM `act(…, TO_ROOM)` includes the victim — a PERS +
  TO_ROOM-topology fix (v2.14.82). Before that: MAGIC-036 — the `dispel_evil` is_good ("Mota protects $N.")
  and `dispel_good` is_evil ("$N is protected by $S evil.") **TO_ROOM** branches
  (`mud/skills/handlers.py`) now use `act_to_room(room, …, caster, arg2=victim,
  exclude=caster)` — per-recipient PERS + `$S` victim possessive, actor excluded —
  matching ROM `act(…, TO_ROOM)` (`src/magic.c:2024/2053`). Fixed three divergences:
  baked keyword→PERS, "name's evil"→`$S` ("its evil" for a sexless NPC), and removed
  the caster over-delivery (ROM TO_ROOM excludes the actor). No tests asserted the
  old caster-delivery (v2.14.81). Before that: MAGIC-035 — `curse` ("$N looks very uncomfortable.") and
  `dispel_evil`/`dispel_good` neutral-victim ("$N does not seem to be affected.")
  TO_CHAR reject lines (`mud/skills/handlers.py`) now render via `act_format`
  ($N = PERS victim short_descr, cap) instead of the baked keyword `name`, matching
  ROM `act(..., TO_CHAR)` (`src/magic.c:1801/2027/2059`). Found by the continuing
  act()-lens sweep. **Filed next (MAGIC-036):** the dispel **TO_ROOM** branches —
  "Mota protects $N." (dispel_evil is_good, magic.c:2024) and "$N is protected by $S
  evil." (dispel_good is_evil, :2053) — bake `name` AND the Python over-delivers to
  the caster (ROM TO_ROOM excludes the actor); needs PERS + $S + TO_ROOM exclusion
  (v2.14.80). Before that: MAGIC-034 — the 5 sibling detect_* spells
  (`detect_evil`/`good`/`hidden`/`invis`/`magic`, `mud/skills/handlers.py`)
  cross-target "can already …" duplicate-cast rejects now render via
  `act_format("$N can already …", arg2=target)` ($N = PERS victim short_descr, cap)
  instead of the baked keyword `name`, matching ROM
  `act(..., TO_CHAR)` (`src/magic.c:1846/1875/1905/1936/1968`); self-cast literals
  were already correct. Re-baselined the 5 existing duplicate-gating tests
  (lit-room setup for PERS). Found by the continuing act()-lens sweep.
  **Filed next:** more baked `$N` lines from the same grep — "$N looks very
  uncomfortable." (magic.c:1801), "$N does not seem to be affected." (:2027/:2059),
  "$N is protected by $S evil." (:2053, TO_ROOM) (v2.14.79). Before that:
  MAGIC-033 — `know_alignment` (`mud/skills/handlers.py:know_alignment`
  ~5860) now renders all 7 alignment-band messages via `act_format("$N …", arg2=victim)`,
  matching ROM `spell_know_alignment`'s single `act(msg, ch, NULL, victim, TO_CHAR)`
  (`src/magic.c:3674-3690`). Three divergences fixed: NPC victims now show the
  capitalized PERS short_descr (was baked keyword); the invented "You …" self-variant
  removed (ROM always uses `$N` — self-cast shows the caster's own name); and ROM's
  literal "…pure evil!." typo (double `!.`) is now preserved (was "evil!"). Existing
  band tests re-baselined across 3 files (lit-room setup for PERS, self-name, typo).
  Wider blast radius than the other act()-lens gaps but one coherent gap (v2.14.78).
  Before that: MAGIC-032 — `sanctuary` (`mud/skills/handlers.py:sanctuary`
  ~7386) cross-target reject leg ("$N is already in sanctuary.") now renders via
  `act_format` ($N = PERS victim short_descr, cap) instead of baked `target.name`,
  matching ROM `act(..., TO_CHAR)` (`src/magic.c:4284`); the self-cast literal was
  already correct. Found by the continuing post-MAGIC-022 act()-lens sweep.
  **Filed next (MAGIC-033 candidate):** `spell_know_alignment` (`magic.c:3666-3690`)
  ALWAYS uses `act("$N …")` (7 tiers, no "You …" self-variant — Python invented
  one), is missing the `ap > -350` "$N lies to $S friends." tier, and must preserve
  ROM's literal typo "embodiment of pure evil!." (v2.14.77). Before that:
  MAGIC-031 — `slow` (~7622) and `stone_skin` (~7852)
  (`mud/skills/handlers.py`) cross-target reject legs ("$N can't get any slower than
  that." / "$N is already as hard as can be.") now render via `act_format`
  ($N = PERS victim short_descr, cap) instead of the baked `_character_name`,
  matching ROM `act(..., TO_CHAR)` (`src/magic.c:4396/4452`). The self-cast legs are
  ROM literals and were already correct. Closes the follow-up filed under MAGIC-030.
  The existing PC-target stone_skin test stays green (PERS = name) (v2.14.76).
  Before that: MAGIC-030 — `sleep` (`mud/skills/handlers.py:sleep` ~7560)
  no longer emits three invented reject messages ("You are already fast asleep." /
  "$N is already fast asleep." / "$N is immune to sleep."); ROM `spell_sleep`
  (`src/magic.c:4363`) silently `return`s on every gate (already-asleep, undead NPC,
  level, saves). The already-affected and undead branches now return False silently
  (the level/saves gates were already silent). Same spurious-output class as
  MAGIC-027. Surfaced by a fresh act()-lens grep sweep after the MAGIC-022 batch
  closed. **Filed next (MAGIC-031 candidate):** the same sweep found `spell_slow`
  ("$N can't get any slower than that.") and `spell_stone_skin` ("$N is already as
  hard as can be.") cross-target legs bake `_character_name` where ROM uses `$N`
  PERS cap — a clean two-site conversion (v2.14.75). Before that:
  MAGIC-029 — the `envenom` skill's already-poisoned-weapon
  dict message (`mud/skills/handlers.py:envenom` ~4160) now capitalizes buf[0] via
  `capitalize_act_line(...)`, matching ROM `do_envenom` `act("$p is already
  envenomed.")` (`src/act_obj.c:929`). Unlike the `poison`-spell weapon branch
  (MAGIC-026, `_send_to_char`), this path returns a `{"message": …}` dict consumed by
  the command layer, so it bypassed act()'s cap. Envenoming "a serrated dagger" now
  returns "A serrated dagger is already envenomed." This **resolves the last
  MAGIC-022-batch follow-up** — the batch is now 100% closed (v2.14.74). Before that:
  MAGIC-028 — `plague` (`mud/skills/handlers.py:plague` ~6589)
  "$N seems to be unaffected." cross-target leg now renders via `act_format`
  ($N = PERS victim short_descr, cap) instead of the baked `_character_name`,
  matching ROM `act(..., TO_CHAR)` (`src/magic.c:3905`). The batch's "sanctuary(?)"
  note was misattributed — the line lives in `plague`. **This CLOSES the MAGIC-022
  enumerated baked-name batch** (MAGIC-023/024/025/026/027/028 + FIGHT-065 all
  resolved); only the `envenom`-skill dict-return `$p` follow-up (filed under the
  MAGIC-026 row) remains. Re-baselined `test_plague_respects_saves_and_undead`
  (FIELD→INSIDE so PERS isn't night-masked) (v2.14.73). Before that:
  MAGIC-027 — `faerie_fire` (`mud/skills/handlers.py:faerie_fire`)
  no longer emits two invented "already surrounded by a pink outline" messages on a
  duplicate cast; ROM `spell_faerie_fire` (`src/magic.c:2811`) silently `return`s
  when the victim already has `AFF_FAERIE_FIRE`. Both fabricated lines removed (the
  branch now returns False silently). This closes the `faerie_fire` batch entry as a
  **spurious-output** divergence, NOT the `$N` cap conversion the batch note assumed
  — the ROM source check showed there is no message to convert. Re-baselined the
  detection test that asserted the invented line (v2.14.72). Before that:
  MAGIC-026 — six object `$p` blocking lines in
  `mud/skills/handlers.py` (`bless`-object, `continual_light`, `fireproof`,
  `poison` weapon branch ×3) now capitalize buf[0] via `capitalize_act_line(...)`,
  matching ROM `act("$p …", ch, obj, NULL, TO_CHAR)` (`src/magic.c:794/1483/2770/3962/3968`).
  Blessing an already-blessed "a glowing rune" now shows "A glowing rune is already
  blessed." (was lowercase). Chose `capitalize_act_line` over `act_format("$p")` to
  match the same-function MAGIC-011 sibling leg and avoid `can_see_object`-masking
  fragility (the caster always sees a targeted object). Re-baselined two missed-caps
  test assertions. **Follow-up filed (MAGIC-026 row):** the `envenom` skill's
  dict-return `$p` paths (`handlers.py:~4139/4160`, ROM `do_envenom` act_obj.c:929)
  have the same gap on a different delivery contract (v2.14.71). Before that:
  FIGHT-065 — the `disarm` skill handler
  (`mud/skills/handlers.py:disarm`, the path `mob_hit`/`_mob_offensive_skill`
  dispatches) now emits ROM's **literal** "Your opponent is not wielding a weapon."
  when the victim is unarmed, instead of baking `_character_name(victim)`
  ("goblin is not wielding a weapon."). ROM `do_disarm` (`src/fight.c:3175`) uses a
  fixed `send_to_char(...)` — no `$N`/PERS render. The player command
  `combat.py:do_disarm` (:1218) was already correct; this was the duplicate
  skill-handler path. Closes the `disarm` entry in the MAGIC-022 batch as a literal
  fix (NOT a `$N` conversion) (v2.14.70). Before that: MAGIC-025 — `fly` ("$N doesn't need your help to fly."),
  `infravision` ("$N already has infravision."), and `pass_door` ("$N is already
  shifted out of phase.") (`mud/skills/handlers.py`) already-affected blocking
  lines now render via `act_format` — $N = PERS NPC short_descr (cap) — matching ROM
  `act(..., ch, NULL, victim, TO_CHAR)` (`src/magic.c:2892/3594/3874`). Casting on an
  already-affected NPC "goblin"/"a green goblin" now shows "A green goblin doesn't
  need your help to fly." (was lowercase "goblin …"). Orphaned `name` assignments
  removed. Continues the MAGIC-022 batch (fly/infravision/pass_door struck;
  disarm/faerie_fire/fireproof/envenom/bless-object/sanctuary remain) (v2.14.69).
  Before that: MAGIC-024 — `giant_strength` ("$N can't get any stronger.")
  and `haste` ("$N is already moving as fast as $E can.") (`mud/skills/handlers.py`)
  now render via `act_format` — $N = PERS short_descr (cap), $E = victim's subject
  pronoun (sexless → "it", not "they") — matching ROM `act(..., TO_CHAR)`
  (`src/magic.c:3028,3074`). Continues the MAGIC-022 batch (giant_strength/haste
  struck; infravision/fly/disarm/faerie_fire/pass_door/fireproof/envenom/bless-object
  remain) (v2.14.68). Before that: MAGIC-023 — `spell_frenzy` (`mud/skills/handlers.py:frenzy`,
  4 sites) "$N is already in a frenzy." / "$N doesn't look like $e wants to fight
  anymore." / "Your god doesn't seem to like $N" now render via `act_format`
  ($N = PERS short_descr + cap) instead of baked name + literal "they". Replicates
  ROM's `$e`-is-CASTER pronoun quirk verbatim (a male caster sees "A green goblin
  doesn't look like **he** wants to fight anymore."). Continues the MAGIC-022
  baked-name batch (frenzy struck; faerie_fire/disarm/fly/giant_strength/haste/…
  still tracked) (v2.14.67). Before that: MAGIC-022 — `protection_evil`/`protection_good`
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
| Version | 2.14.89 |
| Tests | magic044 1/1, blindness 4/4, full suite green 5773 passed / 4 skipped (v2.14.89) |
| MAGIC-022 batch | ✅ FULLY CLOSED (023/024/025/026/027/028/029 + FIGHT-065) |
| act()-lens spell-handler tail | ✅ CLEARED (MAGIC-025..044 — baked-name $n/$N/$p/$S + hand-rolled-room-loop sites in handlers.py converted; commands/ confirmed clean) |
| MAGIC-044 status | ✅ FIXED blindness room broadcast `$n` PERS (act_to_room) |
| MAGIC-043 status | ✅ FIXED envenom room broadcasts `$n`/`$p` PERS (act_to_room) |
| MAGIC-042 status | ✅ FIXED faerie_fog "$n is revealed!" per-recipient PERS (act_to_room) |
| MAGIC-041 status | ✅ FIXED chill_touch room broadcast `$n` PERS (actor=victim, act_to_room) |
| MAGIC-040 status | ✅ FIXED cure_blindness/cure_poison room broadcast `$n` PERS (actor=victim, act_to_room) |
| MAGIC-039 status | ✅ FIXED charm_person TO_VICT/$n + TO_CHAR/$N PERS |
| MAGIC-038 status | ✅ FIXED demonfire "demons of Hell" — PERS + ROM TO_ROOM (victim included) topology |
| MAGIC-037 status | ✅ FIXED demonfire curse-tail `$N` PERS cap |
| MAGIC-036 status | ✅ FIXED dispel TO_ROOM "protected" lines — PERS + `$S` + actor-excluded delivery |
| MAGIC-035 status | ✅ FIXED curse/dispel TO_CHAR `$N` PERS cap |
| MAGIC-034 status | ✅ FIXED detect_* cluster (5 spells) cross-target `$N` PERS cap |
| MAGIC-033 status | ✅ FIXED know_alignment via act("$N") — NPC short_descr cap, no "You" self-variant, "evil!." typo preserved |
| MAGIC-032 status | ✅ FIXED sanctuary cross-target `$N` PERS cap |
| MAGIC-031 status | ✅ FIXED slow/stone_skin cross-target `$N` PERS cap (self-legs were correct literals) |
| MAGIC-030 status | ✅ FIXED sleep silent on all reject gates (removed 3 invented lines) |
| MAGIC-029 status | ✅ FIXED envenom-skill dict-return "already envenomed" caps buf[0] |
| MAGIC-028 status | ✅ FIXED plague "$N seems to be unaffected" uses PERS cap (was baked name) |
| MAGIC-027 status | ✅ FIXED faerie_fire duplicate is silent (removed 2 invented "already surrounded" lines) |
| MAGIC-026 status | ✅ FIXED object `$p` cap (bless-obj/continual_light/fireproof/poison-weapon ×3); envenom-skill dict-return follow-up filed |
| FIGHT-065 status | ✅ FIXED disarm no-weapon line uses ROM literal "Your opponent is not wielding a weapon." (was baked name) |
| MAGIC-025 status | ✅ FIXED fly/infravision/pass_door (`$N` PERS short_descr, cap) |
| MAGIC-024 status | ✅ FIXED giant_strength/haste (`$N`/`$E` PERS; sexless→"it") |
| MAGIC-023 status | ✅ FIXED frenzy (`$N` PERS ×4, `$e`-caster quirk replicated) |
| MAGIC-022 status | ✅ FIXED protection evil/good (`$N` PERS ×6); ⚠️ ~13-site baked-name batch tracked |
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
