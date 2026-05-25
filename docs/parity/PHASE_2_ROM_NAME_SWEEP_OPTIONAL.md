# Phase 2 (optional): ROM-name cosmetic field sweeps on `Object`

**Status:** Optional. Not on the active backlog.
**Filed:** 2026-05-25, after INV-013 shipped (v2.9.2).

## Background

After INV-012 (`OBJECT-LIST-CANONICAL`, v2.9.0) and INV-013
(`OBJECT-LOCATION-COHERENCE`, v2.9.2), the `Object` runtime class
carries ROM-faithful field names **as aliases** alongside their
original Python names:

| Python (canonical storage) | ROM-faithful alias              | Refs |
|---------------------------|----------------------------------|------|
| `prototype`               | `pIndexData` (`@property`)       | ~291 |
| `contained_items`         | `contains` (read-only `@property`) | ~182 |

Both aliases are real `@property` accessors on the same backing field
— no divergence risk, and the ROM-named form is callable today.

(`location` was the third candidate originally listed for Phase 2; it
turned out to be load-bearing semantics, not cosmetics, and shipped
under INV-013 instead.)

## The work, if pursued

A full sweep that:

1. Makes the ROM name the backing field.
2. Deletes the `@property` alias.
3. Renames every caller (`obj.prototype` → `obj.pIndexData`,
   `obj.contained_items` → `obj.contains`).
4. Updates docs / comments referencing the old names.

This is **purely cosmetic** — pure ROM-source-parity for code readers
cross-referencing `src/handler.c`, `src/db.c`, etc. against the Python
port.

## Why not scheduled

- Both aliases are already callable; readers can search for the ROM
  name and find live code today.
- `pIndexData` is a Hungarian-notation C-ism that reads worse than
  `prototype` to modern Python eyes. `contains` is fine but the
  Python-typed read of `contained_items` is also fine.
- 473 mechanical edits is real churn for an aesthetic-only win.
- The load-bearing parts of the original "Phase 2" intent (the
  consolidation and the location divergence) already shipped under
  INV-012 and INV-013.

## When to revisit

Pick this up if:

- A future session is explicitly about ROM-source line-by-line
  cross-reference (e.g. an audit that wants Python field names to
  match C struct field names 1:1 in diff form).
- The project adopts a convention that all parity-sensitive code MUST
  use ROM names. The current convention is *aliases exist*; using
  either is fine.

## How, if and when

- One rename per commit, full suite between each.
- `superpowers:subagent-driven-development` fits — the sweep
  parallelizes per target file.
- Treat as one focused session: pick `prototype → pIndexData` first
  (higher impact / more cross-references in core code), then
  `contained_items → contains` (concentrated in `game_loop.py` and
  `combat/death.py`).
- Delete this file when the work lands, or when the convention is
  resolved against doing it.
