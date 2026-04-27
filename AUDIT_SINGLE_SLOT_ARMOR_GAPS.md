# Single-Slot Armor Audit: ROM C vs Python

**Scope**: BODY, HEAD, LEGS, FEET, HANDS, ARMS, ABOUT, WAIST branches of `wear_obj()`  
**ROM Reference**: `src/act_obj.c` lines 1483–1561  
**Python Target**: `mud/commands/equipment.py` do_wear(), _get_wear_location(), _wear_location_messages()

---

## Verified: No Issues Found

✅ **Message Wording** — All 8 single-slot TO_ROOM and TO_CHAR messages match ROM exactly (lines 1487–1559 vs. lines 473–480).

✅ **Slot Ordering** — Python checks slots in the same order as ROM (BODY → HEAD → LEGS → FEET → HANDS → ARMS → ABOUT → WAIST).

✅ **wear_all() Semantics** — Python's `_wear_all()` line 438 correctly skips occupied slots (matching ROM's `fReplace=FALSE` silent fail at line 1720).

---

## Gaps

| Line | Issue | Severity |
|------|-------|----------|
| do_wear:202-204 + _unequip_to_inventory:38 | **Duplicate "You can't remove X" message**. When item is NOREMOVE: _unequip_to_inventory() emits msg at line 38, then do_wear() emits the same msg again at line 204. ROM emits only once (remove_obj line 1384 → return → wear_obj returns silently). | IMPORTANT |
| do_wear:116 | **Position check** `ch.position < Position.SLEEPING`. ROM's wear_obj() has no position check (only level check at line 1405). This check is enforced at the command dispatcher level in ROM, not in wear_obj. Python's check may block valid wear attempts if dispatcher also checks. Verify no double-check. | IMPORTANT |

---

## Notes

- `remove_obj()` semantics are correctly implemented in `_unequip_to_inventory()` for the success path (unequip + messages).
- The NOREMOVE error message issue affects both `do_wear` armor paths and any other code calling `_unequip_to_inventory()` when the equipped item is locked.

