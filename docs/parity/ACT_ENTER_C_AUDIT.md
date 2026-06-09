# ACT_ENTER_C_AUDIT.md

## Header

| Field | Value |
|---|---|
| ROM C file | `src/act_enter.c` |
| ROM C line count | 229 lines |
| Python entry points | `mud/commands/movement.py:47` (`do_enter`); portal transport logic in `mud/world/movement.py:441` (`move_character_through_portal`) |
| ROM C dispatcher | `mud/commands/dispatcher.py:261` — registered as `enter`, `min_position=Position.STANDING`; `mud/commands/remaining_rom.py:400` — `go` aliases to `do_enter` |
| Audit date | 2026-04-27 |
| Auditor | Claude Sonnet 4.6 |
| **Status** | ✅ **100% AUDITED — all 16 gaps closed (2026-06-01)** |
| Integration tests | `tests/integration/test_act_enter_gaps.py` — 26 tests, all passing |

### File Purpose

`act_enter.c` implements two functions:
1. `get_random_room(ch)` — helper that spins `number_range(0,65535)` until it finds a visible, non-private, non-safe, non-law (when applicable) room. Used by GATE_RANDOM and GATE_BUGGY portal destinations.
2. `do_enter(ch, argument)` — the `enter` / `go` command. Handles portal object lookup, trust/curse gating, destination resolution (random/buggy/fixed), TO_ROOM messages before and after transit, GOWITH flag, charge decrement, portal destruction, follower cascading, and mob-prog triggers.

The Python implementation splits this across `do_enter` (pre-flight checks in `mud/commands/movement.py`) and `move_character_through_portal` (transit logic in `mud/world/movement.py`).

---

## Function Inventory Table

| ROM C function | Lines | Python equivalent | Status |
|---|---|---|---|
| `get_random_room` | 44–63 | `_get_random_room` in `mud/world/movement.py` | ✅ AUDITED — ENTER-001/013 closed |
| `do_enter` | 66–229 | `do_enter` + `move_character_through_portal` | ✅ AUDITED — ENTER-002 through ENTER-018 closed |

---

## Gap Table

### ENTER-001 — `get_random_room`: non-NPC LAW room exclusion logic inverted ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-001 |
| ROM C reference | `src/act_enter.c:57–58` |
| Severity | IMPORTANT |
| **Closure** | Logic was verified correct for NPC/PC cases. The bounded loop (real gap) is covered by ENTER-013. Iteration cap raised to 100,000 matching ROM's infinite-loop guarantee. |

**ROM C logic (lines 57–58):**
```c
(IS_NPC(ch) || IS_SET(ch->act, ACT_AGGRESSIVE)
    || !IS_SET(room->room_flags, ROOM_LAW))
```
A random room is valid if: the character IS an NPC, OR the character has ACT_AGGRESSIVE set, OR the room does NOT have ROOM_LAW. In other words, a non-aggressive non-NPC player is blocked only from LAW rooms.

**Python logic (`mud/world/movement.py:270–273`):**
```python
act_flags = int(getattr(ch, "act", 0) or 0)
if not ch.is_npc and not (act_flags & int(ActFlag.AGGRESSIVE)):
    if flags & int(RoomFlag.ROOM_LAW):
        continue
```
This correctly excludes LAW rooms for non-aggressive PCs. However it also implicitly allows NPCs and aggressive PCs to land in LAW rooms. The logic is functionally equivalent for the PC case but the NPC branch is wrong: ROM allows _any_ NPC into a random LAW room (regardless of ACT_AGGRESSIVE), whereas the Python code also admits aggressive PCs to LAW rooms. This matches ROM for aggressive NPCs, but an NPC without ACT_AGGRESSIVE would be incorrectly blocked by the Python code because `not ch.is_npc` is False for NPCs — actually Python will skip the entire `if not ch.is_npc` block, meaning NPCs are NOT filtered at all in Python, matching ROM. Re-reading carefully: ROM admits NPC (line 57 first clause), Python skips the whole block when `ch.is_npc` — so NPC behaviour is actually correct. The subtle difference is for **non-NPC, aggressive** characters: ROM condition `IS_SET(ch->act, ACT_AGGRESSIVE)` — a PC with ACT_AGGRESSIVE set is admitted to LAW rooms in ROM. Python also admits them (`not (act_flags & ACT_AGGRESSIVE)` is False so the block is skipped). This is correct. **No actual bug here for the NPC/PC cases.** However: ROM iterates forever until it finds a valid room (`for(;;)`), while Python has a bounded loop (`attempts = max(len(room_registry), 1) * 2`). If the room registry is very sparse this loop can exhaust without finding a room and return `None`, which ROM never does.

**Revised verdict:** The bounded-loop risk is the real gap. ROM `get_random_room` cannot return NULL (it loops forever). Python `_get_random_room` can return `None`, and `move_character_through_portal` treats `None` destination as "It doesn't seem to go anywhere." This is a functional deviation.

---

### ENTER-002 — `do_enter` no-arg message wrong ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-002 |
| ROM C reference | `src/act_enter.c:227` |
| Severity | MINOR |
| **Closure** | Fixed in `mud/commands/movement.py`. Now returns `"Nope, can't do it."` matching ROM. |

**ROM C (line 227):** `send_to_char("Nope, can't do it.\n\r", ch);`

**Python (`mud/commands/movement.py:50`):** Returns `"Enter what?"`

ROM sends `"Nope, can't do it."` when the argument is empty. Python sends `"Enter what?"`. Wrong message.

---

### ENTER-003 — `do_enter` object-not-found message wrong ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-003 |
| ROM C reference | `src/act_enter.c:86–88` |
| Severity | MINOR |
| **Closure** | Fixed in `mud/commands/movement.py`. Now returns `"You don't see that here."` matching ROM. |

**ROM C (lines 86–88):**
```c
if (portal == NULL) {
    send_to_char("You don't see that here.\n\r", ch);
    return;
}
```

**Python (`mud/commands/movement.py:67`):** Returns `f"I see no {target} here."`

ROM sends `"You don't see that here."` Python sends `"I see no <target> here."` Wrong message text.

---

### ENTER-004 — Wrong "not a portal / closed" combined check and message ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-004 |
| ROM C reference | `src/act_enter.c:90–96` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/commands/movement.py`. Combined gate now emits `"You can't seem to find a way in."` for both non-portal objects and closed portals, matching ROM. |

**ROM C (lines 90–96):**
```c
if (portal->item_type != ITEM_PORTAL
    || (IS_SET(portal->value[1], EX_CLOSED) && !IS_TRUSTED(ch, ANGEL)))
{
    send_to_char("You can't seem to find a way in.\n\r", ch);
    return;
}
```
This is a **single combined gate**: if the object is not a portal, OR if it is a portal but closed and char lacks ANGEL trust, the message is `"You can't seem to find a way in."` — the same message for both cases.

**Python (`mud/commands/movement.py:59–80`):**
- The object-lookup loop only considers objects with `item_type == ItemType.PORTAL`, so non-portal objects are silently skipped (the character will get "I see no X here" instead of "You can't seem to find a way in."). This means if a player types `enter chest` where a chest object is in the room, ROM says `"You can't seem to find a way in."`, Python says `"I see no chest here."`.
- The closed-portal check at line 79 returns `"The portal is closed."` instead of `"You can't seem to find a way in."`.

Both branches produce the wrong message. The Python logic also silently skips non-portal objects during lookup instead of returning the ROM error.

---

### ENTER-005 — `do_enter` object lookup uses substring/fuzzy match instead of `get_obj_list` ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-005 |
| ROM C reference | `src/act_enter.c:82` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/commands/movement.py`. Now calls `get_obj_list(char, target, room_contents)` which handles visibility, numbered prefix syntax (`2.portal`), and keyword-list matching. |

**ROM C (line 82):** `portal = get_obj_list(ch, argument, ch->in_room->contents);`

ROM uses `get_obj_list` which: (a) checks visibility (`can_see`), (b) supports numbered prefix syntax (`2.portal`), (c) matches against the object's keyword list using `is_name`.

**Python (`mud/commands/movement.py:57–64`):** Iterates `char.room.contents` doing substring match on `short_descr`/`name`, with a hardcoded `target == "portal"` wildcard. This does not call `get_obj_list`, does not check character visibility of the object, does not support `2.portal` numbered syntax, and the `target in name` substring match is not the same as ROM's keyword-list `is_name` check.

`get_obj_list` already exists in the codebase at `mud/commands/obj_manipulation.py:26`.

---

### ENTER-006 — Follower cascade: `do_stand` for charmed followers below STANDING ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-006 |
| ROM C reference | `src/act_enter.c:178–180` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/world/movement.py:_stand_charmed_follower`. Now delegates to real `do_stand` from `mud.commands.position`, matching ROM `do_function(fch, &do_stand, "")`. |

**ROM C (lines 178–180):**
```c
if (fch->master == ch && IS_AFFECTED(fch, AFF_CHARM)
    && fch->position < POS_STANDING)
    do_function(fch, &do_stand, "");
```
Before attempting to move a charmed follower, ROM stands them up (via `do_stand`) if they are below STANDING, **regardless of whether they will actually be able to follow**.

**Python (`mud/world/movement.py:88–89`):**
```python
if follower.has_affect(AffectFlag.CHARM) and follower.position < Position.STANDING:
    _stand_charmed_follower(follower)
```
`_stand_charmed_follower` only sets `position = STANDING` and sends a message. It does not fully mirror `do_stand` (which in ROM would also wake the character properly and fire any related triggers). The check itself exists, but the implementation is a local stub rather than delegating to the real `do_stand` equivalent.

---

### ENTER-007 — Follower cascade: `"You follow $N."` uses act() / TO_CHAR, Python uses plain string ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-007 |
| ROM C reference | `src/act_enter.c:195` |
| Severity | MINOR |
| **Closure** | Fixed in `mud/world/movement.py:_move_followers`. Now uses `act_format("You follow $N.", ...)` so invisible leaders show as "someone". |

**ROM C (line 195):** `act("You follow $N.", fch, NULL, ch, TO_CHAR);`

ROM formats the leader's name through `act()` with the `$N` token (which resolves to the target's name as seen by the subject, applying visibility). 

**Python (`mud/world/movement.py:105–106`):**
```python
follower.send_to_char(f"You follow {leader.name}.")
```
Uses a raw f-string with `leader.name`, bypassing act-format visibility checks. If the leader is invisible to the follower, ROM would show `"You follow someone."` while Python would show the leader's real name.

---

### ENTER-008 — TO_ROOM departure message uses `broadcast_room` plain string instead of `act()` ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-008 |
| ROM C reference | `src/act_enter.c:134` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/world/movement.py:move_character_through_portal`. Now uses `act_format("$n steps into $p.", ...)` + `broadcast_room`, applying visibility to both `$n` (char) and `$p` (portal). |

**ROM C (line 134):** `act("$n steps into $p.", ch, portal, NULL, TO_ROOM);`

This uses the `act()` engine: `$n` = char's name (with visibility: "someone" if invisible), `$p` = portal object name (with visibility: "something" if not visible to observer).

**Python (`mud/world/movement.py:514`):**
```python
broadcast_room(current_room, f"{char_name} steps into {portal_name}.", exclude=char)
```
Uses raw f-string with plain name — no act-format visibility substitution. Invisible characters and invisible portal objects will show their real names to all observers instead of "someone"/"something".

---

### ENTER-009 — TO_CHAR entry message sent in wrong order relative to room move ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-009 |
| ROM C reference | `src/act_enter.c:136–143` |
| Severity | IMPORTANT (originally logged CRITICAL) |
| **Closure** | Fixed in `mud/world/movement.py:move_character_through_portal`. Entry message now sent via `char.send_to_char()` BEFORE `remove_character`/`add_character`, matching ROM order (line 136-140 before line 142-143). |

**ROM C order (lines 136–143):**
1. `act("You enter $p.", ch, portal, NULL, TO_CHAR);` — OR the `...somewhere else...` variant
2. `char_from_room(ch);`
3. `char_to_room(ch, location);`

The TO_CHAR entry message is sent **before** the character moves to the new room.

**Python (`mud/world/movement.py:516–531, 567–572`):**
- `current_room.remove_character(char)` / `destination.add_character(char)` happen at lines 516–517.
- `_auto_look(char)` fires at line 531.
- The `entry_message` return value (lines 567–572) is the string returned to the caller — it is not sent via `send_to_char` inside the function; it depends on whether the caller sends it. The caller `do_enter` just does `return move_character_through_portal(...)` and does not call `send_to_char`. So the TO_CHAR entry message may never actually be delivered to the player's output buffer via `send_to_char` — it is only returned as a Python string return value.

This is a CRITICAL gap: the player receives no "You enter …" / "You walk through … and find yourself somewhere else..." message.

---

### ENTER-010 — Arrival TO_ROOM message uses `broadcast_room` plain string instead of `act()` ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-010 |
| ROM C reference | `src/act_enter.c:151–154` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/world/movement.py:move_character_through_portal`. Now uses `act_format("$n has arrived.", ...)` and `act_format("$n has arrived through $p.", ...)` + `broadcast_room`. |

**ROM C (lines 151–154):**
```c
if (IS_SET(portal->value[2], GATE_NORMAL_EXIT))
    act("$n has arrived.", ch, portal, NULL, TO_ROOM);
else
    act("$n has arrived through $p.", ch, portal, NULL, TO_ROOM);
```

**Python (`mud/world/movement.py:526–529`):**
```python
arrival_message = (
    f"{char_name} has arrived." if uses_normal_exit else f"{char_name} has arrived through {portal_name}."
)
broadcast_room(destination, arrival_message, exclude=char)
```
Same visibility issue as ENTER-008: raw f-string bypasses act-format; invisible characters show real name.

---

### ENTER-011 — Portal fade-out message goes to wrong recipients ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-011 |
| ROM C reference | `src/act_enter.c:200–213` |
| Severity | IMPORTANT |
| **Closure** | Fixed in new `mud/world/movement.py:_portal_fade_out`. Correctly sends TO_CHAR to traveller; if destination==origin also TO_ROOM there; otherwise only to old_room people. Uses `act_format` for `$p` visibility. Calls `_extract_obj` from `mud.game_loop`. |

**ROM C (lines 200–213):**
```c
if (portal != NULL && portal->value[0] == -1) {
    act("$p fades out of existence.", ch, portal, NULL, TO_CHAR);
    if (ch->in_room == old_room)
        act("$p fades out of existence.", ch, portal, NULL, TO_ROOM);
    else if (old_room->people != NULL) {
        act("$p fades out of existence.",
            old_room->people, portal, NULL, TO_CHAR);
        act("$p fades out of existence.",
            old_room->people, portal, NULL, TO_ROOM);
    }
    extract_obj(portal);
}
```
ROM sends the message:
- TO_CHAR (the traveller, in the **destination** room)
- If destination == origin: also TO_ROOM (destination)
- If destination != origin and origin has people: TO_CHAR of first person in origin room + TO_ROOM of origin room

**Python (`mud/world/movement.py:555–566`):**
```python
if charges_remaining == -1:
    fade_message = f"{portal_name} fades out of existence."
    if hasattr(char, "send_to_char"):
        char.send_to_char(fade_message)
    for room in (current_room, destination):
        contents = getattr(room, "contents", None)
        if isinstance(contents, list) and portal in contents:
            contents.remove(portal)
            broadcast_room(room, fade_message, exclude=char if room is destination else None)
```
Python always broadcasts to BOTH rooms. ROM only broadcasts to the old room if the destination differs AND the old room has people. Also, Python uses `broadcast_room` (plain string) instead of `act("$p fades...", ...)` — losing act-format visibility on `$p`.

Additionally, Python removes the portal from `contents` but does not call `extract_obj` (the full ROM object extractor that also removes the object from the global object list).

---

### ENTER-012 — Charge decrement happens before follower cascade (order mismatch) ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-012 |
| ROM C reference | `src/act_enter.c:158–176` |
| Severity | IMPORTANT |
| **Closure** | Charge-decrement order was already correct. Fixed the follower message suppression: `_move_followers` lambda now passes `_is_follow=False` so each follower receives full departure/arrival TO_ROOM messages matching ROM's recursive `do_enter` call per follower. |

**ROM C order (lines 158–176):**
1. `do_look "auto"` (line 156)
2. Charge decrement: `portal->value[0]--; if(==0) value[0]=-1;` (lines 159–164)
3. Circular-follow guard: `if(old_room == location) return;` (line 167)
4. Follower loop iterating `old_room->people` (lines 170–198)
5. Portal fade and extract_obj (lines 200–213)
6. Mob-prog triggers (lines 219–222)

Critical ordering: the charge is decremented **before** followers try to use the portal. Each follower who calls `do_enter` recursively will again decrement. ROM's follower check at line 174 reads `portal->value[0] == -1` to gate whether followers may pass — this relies on the charge having already been decremented. Followers share the same portal charge counter.

**Python (`mud/world/movement.py:533–553`):**
```python
# charge decrement (lines 533–536)
if len(values) > 0 and int(values[0]) > 0:
    values[0] = int(values[0]) - 1
    if values[0] == 0:
        values[0] = -1

charges_remaining = int(values[0]) if len(values) > 0 else 0

if not (gate_flags & int(PortalFlag.GOWITH)) and charges_remaining != -1:
    # follower cascade (lines 541–548)
    _move_followers(...)
```
The charge decrement order is correct. However, the guard `charges_remaining != -1` means Python will **not move followers at all** when the portal just ran out of charges (value[0] went to -1 on this use). ROM does the opposite: followers are processed **after** the decrement and the follower loop checks `portal->value[0] == -1` to **skip** each follower individually — meaning if there were 2 charges left before the transit, 1 charge remains and followers can still use it. If 1 charge was left (now 0 → set to -1), followers cannot use it. Python correctly handles the "portal just expired" case by not cascading, but let's confirm: ROM line 174 `if(portal==NULL || portal->value[0]==-1) continue;` — yes, when value[0]==-1 after decrement, followers are skipped one-by-one (continue, not break). Python's `charges_remaining != -1` guard skips the entire `_move_followers` call, which has the same net effect. This is equivalent. **No actual gap here on the cascade guard.**

The real gap in ENTER-012 is that Python's `_move_followers` calls `move_character_through_portal(follower, portal, _is_follow=True)` but the `_is_follow=True` path suppresses the `"$n steps into $p."` departure message AND the arrival message for all followers. ROM has followers call `do_function(fch, &do_enter, argument)` — a full recursive `do_enter` — which sends the full TO_ROOM departure message `"$n steps into $p."` and arrival message for each follower. Python suppresses these for followers.

---

### ENTER-017 — Expiring portal fade-out happened after ENTRY/GREET triggers ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-017 |
| ROM C reference | `src/act_enter.c:200–222` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/world/movement.py:move_character_through_portal` (2026-06-01). The one-charge portal fade/extract block now runs before the `TRIG_ENTRY` / `mp_greet_trigger` block, matching ROM ordering. Regression: `tests/integration/test_act_enter_gaps.py::TestEnter011PortalFadeOut::test_fade_happens_before_greet_trigger`. |

**ROM C order (lines 200–222):**
```c
if (portal != NULL && portal->value[0] == -1) {
    act("$p fades out of existence.", ch, portal, NULL, TO_CHAR);
    ...
    extract_obj(portal);
}

if (IS_NPC(ch) && HAS_TRIGGER(ch, TRIG_ENTRY))
    mp_percent_trigger(ch, NULL, NULL, NULL, TRIG_ENTRY);
if (!IS_NPC(ch))
    mp_greet_trigger(ch);
```

Python had the same two behaviors but in reverse order: `mp_greet_trigger(ch)` ran before `_portal_fade_out(...)`. That was observable to scripts and message ordering on a one-charge portal. ROM expires and extracts the portal first, then runs the mob-program entry/greet hooks.

---

### ENTER-018 — Portal departure/arrival broadcasts bypass per-recipient PERS masking ✅ FIXED

| Field | Detail |
|---|---|
| Gap ID | ENTER-018 |
| ROM C reference | `src/act_enter.c:134,151-154` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/world/movement.py:move_character_through_portal` + `_portal_fade_out` (2026-06-01). Replaced `broadcast_room()` + `mobprog.mp_act_trigger_room()` pairs with `_act_to_room()` calls, which render per-recipient via `act_format(recipient=recipient, ...)` and dispatch `mp_act_trigger` per NPC — matching ROM's `act(..., TO_ROOM)` per-recipient PERS masking (INV-027). Observable: an invisible player entering a portal now appears as "Someone" to unaided witnesses, not their real name. Regression: `tests/integration/test_inv025_movement_act_trigger_dispatch.py::TestPortalPERSMasking`. |

**ROM C (lines 134, 151-154):**
```c
act("$n steps into $p.", ch, portal, NULL, TO_ROOM);     // line 134
act("$n has arrived.", ch, portal, NULL, TO_ROOM);        // line 152 (GATE_NORMAL_EXIT)
act("$n has arrived through $p.", ch, portal, NULL, TO_ROOM); // line 154
```
All three use `act(TO_ROOM)`, which renders `$n` through `PERS(ch, to)` → `can_see(to, ch)` per recipient (src/comm.c:2230–2385, INV-027). An invisible actor's name must render as "someone" for recipients who cannot see them.

**Python (before fix):** `broadcast_room()` delivered a single baked string (rendered once with `recipient=None`, so `$n` expanded to the actor's real name unconditionally) to all recipients — no PERS masking. `mobprog.mp_act_trigger_room()` dispatched a single pre-rendered message to all NPC recipients.

**Python (after fix):** `_act_to_room()` renders per recipient with `act_format(recipient=recipient, ...)`, then delivers via `push_message()` and dispatches `mp_act_trigger()` per NPC — matching ROM's `act(TO_ROOM)` per-recipient behavior exactly. Same fix applied to `_portal_fade_out`'s TO_ROOM broadcasts (lines 204, 209-210).

---

### ENTER-019 — Portal followers were pre-skipped by destination visibility ✅ FIXED

| Field | Detail |
|---|---|
| Gap ID | ENTER-019 |
| ROM C reference | `src/act_enter.c:177-198`, compared with `src/act_move.c:218` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/world/movement.py:_move_followers` / `move_character_through_portal` (2026-06-09). Directional movement still requires follower `can_see_room` per `act_move.c:218`, but portal follower recursion no longer applies that pre-gate because ROM `act_enter.c:177-198` calls `do_enter` for each standing follower without a `can_see_room` check. Regression: `tests/integration/test_act_enter_gaps.py::TestEnter012FollowerMessages::test_follower_attempts_portal_before_destination_visibility_gate`. |

**ROM C distinction:**
```c
/* act_move.c:216-219 */
if (fch->master == ch && fch->position == POS_STANDING
    && can_see_room (fch, to_room))
    move_char (fch, door, TRUE);

/* act_enter.c:190-196 */
if (fch->master == ch && fch->position == POS_STANDING) {
    act ("You follow $N.", fch, NULL, ch, TO_CHAR);
    do_function (fch, &do_enter, argument);
}
```

Python reused one `_move_followers` helper for both paths, so portal followers inherited the directional `can_see_room` pre-check and were silently skipped when they could not see the destination. ROM still lets the follower attempt the recursive `do_enter`; the follower may then fail inside `do_enter`'s own destination check (`act_enter.c:119`) and receive the portal "doesn't seem to go anywhere" line. The fix adds an explicit `require_destination_visibility` switch at the two call sites so both ROM contracts remain separate.

---

### ENTER-013 — `_get_random_room` bounded-loop can return `None` ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-013 |
| ROM C reference | `src/act_enter.c:48–62` |
| Severity | IMPORTANT |
| **Closure** | Fixed in `mud/world/movement.py:_get_random_room`. Iteration cap raised from `len(registry)*2` to 100,000, matching ROM's infinite-loop guarantee in practice. |

**ROM C:** Infinite `for(;;)` loop; never returns NULL.

**Python (`mud/world/movement.py:257–275`):** `attempts = max(len(room_registry), 1) * 2` — bounded. Can return `None` if no suitable room found within 2× registry size. `move_character_through_portal` treats `None` destination as `"It doesn't seem to go anywhere."` — which is incorrect ROM behavior for a GATE_RANDOM portal (the portal should always find a destination).

---

### ENTER-014 — Private-room trust check uses `MAX_LEVEL` instead of `IMPLEMENTOR` ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-014 |
| ROM C reference | `src/act_enter.c:120` |
| Severity | MINOR |
| **Closure** | `MAX_LEVEL == 60 == IMPLEMENTOR` — numerically correct. No functional change needed. The constant name difference is cosmetic and documented here for future maintainers. |

**ROM C (line 120):** `(room_is_private(location) && !IS_TRUSTED(ch, IMPLEMENTOR))`

`IMPLEMENTOR` is the top trust level in ROM (level 60 in this codebase = `MAX_LEVEL`). ROM uses `IS_TRUSTED(ch, IMPLEMENTOR)` to let only implementors bypass private room entry via portals.

**Python (`mud/world/movement.py:499`):** `not (char.is_admin or trust >= MAX_LEVEL)`

`MAX_LEVEL` is 60 which equals `IMPLEMENTOR`. This is numerically correct, but uses `MAX_LEVEL` constant instead of a named `LEVEL_IMPLEMENTOR` constant. Not a functional bug, but semantically wrong — if these constants diverge in the future this will break silently. Minor/cosmetic.

---

### ENTER-015 — `"$p doesn't seem to go anywhere."` message uses `act()` but Python uses plain string ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-015 |
| ROM C reference | `src/act_enter.c:122–124` |
| Severity | MINOR |
| **Closure** | Fixed in `mud/world/movement.py:move_character_through_portal`. Now uses `act_format("$p doesn't seem to go anywhere.", ...)` + `char.send_to_char()` matching ROM `act(...)` call. |

**ROM C (lines 122–124):**
```c
act("$p doesn't seem to go anywhere.", ch, portal, NULL, TO_CHAR);
```
`$p` resolves the portal object's short description with visibility check.

**Python (`mud/world/movement.py:501`):** Returns `"It doesn't seem to go anywhere."` — no `$p` substitution, wrong message text entirely.

---

### ENTER-016 — Fighting check silently returns in ROM; Python returns an error string ✅ AUDITED

| Field | Detail |
|---|---|
| Gap ID | ENTER-016 |
| ROM C reference | `src/act_enter.c:70–71` |
| Severity | MINOR |
| **Closure** | Fixed in both `mud/commands/movement.py` and `mud/world/movement.py`. Fighting check now returns `""` (empty string) silently, matching ROM `if (ch->fighting != NULL) return;`. Duplicate `send_to_char` call also removed from `move_character_through_portal`. |

**ROM C (lines 70–71):**
```c
if (ch->fighting != NULL)
    return;
```
Silent return — no message sent to the player.

**Python (`mud/commands/movement.py:52–53`):**
```python
if getattr(char, "fighting", None) is not None:
    return "No way!  You are still fighting!"
```
Returns a message. ROM is silent. (Note: `move_character_through_portal` also has this check at line 446–450, sending `"No way!  You are still fighting!"` via `send_to_char`. That check is also wrong — ROM is silent.)

---

## Summary

### ✅ ALL GAPS CLOSED — 100% AUDITED (2026-06-01)

### Gap Count by Severity

| Severity | Count | Gap IDs | Status |
|---|---|---|---|
| CRITICAL | 1 | ENTER-009 | ✅ Closed |
| IMPORTANT | 11 | ENTER-001, ENTER-004, ENTER-005, ENTER-006, ENTER-008, ENTER-010, ENTER-011, ENTER-012, ENTER-013, ENTER-017, ENTER-018 | ✅ All Closed |
| MINOR | 5 | ENTER-002, ENTER-003, ENTER-007, ENTER-014, ENTER-015, ENTER-016 | ✅ All Closed |

(ENTER-016 counted as MINOR; total = 17 gaps — all closed)

### Files Modified

- `mud/commands/movement.py` — `do_enter`: ENTER-002, ENTER-003, ENTER-004, ENTER-005, ENTER-016
- `mud/world/movement.py` — `_get_random_room`: ENTER-001, ENTER-013; `_stand_charmed_follower`: ENTER-006; `_move_followers`: ENTER-007; `move_character_through_portal`: ENTER-008, ENTER-009, ENTER-010, ENTER-011, ENTER-012, ENTER-015, ENTER-016, ENTER-017, ENTER-018; `_portal_fade_out`: ENTER-011, ENTER-018

### Integration Tests

`tests/integration/test_act_enter_gaps.py` — 26 tests, all passing

### Recommended Close Order

**Phase 1 — Critical functional correctness (close first)**

1. **ENTER-009** (CRITICAL): TO_CHAR entry message never delivered. The `"You enter $p."` / `"You walk through..."` message must be sent via `char.send_to_char()` inside `move_character_through_portal`, not just returned as a string.

**Phase 2 — Important behavioral gaps**

2. **ENTER-005** (IMPORTANT): Replace the custom portal-lookup loop in `do_enter` with a call to `get_obj_list` (already in `mud/commands/obj_manipulation.py`). This also fixes numbered-prefix syntax and visibility gating.
3. **ENTER-004** (IMPORTANT): Fix the combined non-portal / closed-portal check to emit `"You can't seem to find a way in."` for both cases, matching ROM.
4. **ENTER-008 + ENTER-010** (IMPORTANT): Replace `broadcast_room(room, f"...")` with `act_format`-based dispatch so `$n`/`$p` tokens apply visibility correctly for departure and arrival messages.
5. **ENTER-011** (IMPORTANT): Fix portal fade-out to: (a) send to traveller via TO_CHAR, (b) send to old-room people only when destination != origin, (c) use `act("$p fades...")` for `$p` visibility, (d) call `extract_obj` equivalent.
6. **ENTER-013** (IMPORTANT): Make `_get_random_room` retry indefinitely (or with a very large bound) to match ROM's infinite-loop guarantee for GATE_RANDOM portals.
7. **ENTER-006** (IMPORTANT): Delegate charmed-follower stand-up to the real `do_stand` equivalent rather than the local stub.
8. **ENTER-012** (IMPORTANT): Ensure followers each get proper TO_ROOM messages on departure and arrival (currently suppressed by `_is_follow=True`).
9. **ENTER-001** (IMPORTANT): Already a borderline case — see note in gap. The NPC/PC logic is effectively equivalent; the only residual issue is bounded loop (covered by ENTER-013).

**Phase 3 — Minor/cosmetic**

10. **ENTER-002**: Fix empty-arg message to `"Nope, can't do it."`.
11. **ENTER-003**: Fix object-not-found message to `"You don't see that here."`.
12. **ENTER-015**: Fix destination-null message to `"$p doesn't seem to go anywhere."` with act-format.
13. **ENTER-007**: Use act-format for `"You follow $N."` in follower cascade.
14. **ENTER-016**: Remove `"No way!  You are still fighting!"` message — ROM is silent on fighting check.
15. **ENTER-014**: Define and use `LEVEL_IMPLEMENTOR` constant instead of `MAX_LEVEL` for private-room bypass check.
