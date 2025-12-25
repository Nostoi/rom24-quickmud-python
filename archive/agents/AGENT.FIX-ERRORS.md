You are a senior Python engineer working on a MUD engine repo named `rom24-quickmud-python`. The current problem is **unresolved Git merge-conflict markers** that are causing test collection to blow up with a `SyntaxError` in `mud/models/character.py`.

## Goal
Resolve all conflict markers, fix any follow-on import/circular-import issues, and get **pytest collection to succeed with 0 errors**. It’s OK if some tests fail after collection; the acceptance bar for this task is “collection succeeds”.

## Concrete error (from user):
- Import chain: `from .obj import ObjIndex, ObjectData, Affect` → `mud/models/obj.py` → `from .character import Character`
- Crash: `mud/models/character.py`, line ~136, contains `<<<<<<< HEAD` which triggers:
  ```
  SyntaxError: invalid syntax
  ```
- 74 errors occurred during **collection**.

## Step-by-step plan
1. **Scan for conflict markers**:
   - Search entire repo for these tokens: `<<<<<<<`, `=======`, `>>>>>>>`.
   - At minimum, fix `mud/models/character.py` (around line 136). There may be others.
   - Remove markers and reconcile both sides **intentionally** (don’t just delete lines). Prefer code that keeps public APIs used by tests.

2. **Repair imports & circulars**:
   - Files involved: `mud/models/character.py` and `mud/models/obj.py`.
   - If there’s a circular import (`obj.py` imports `character.py` and vice versa), do **one** of the following minimal changes:
     - Move type-only imports behind a guard:
       ```python
       from typing import TYPE_CHECKING
       if TYPE_CHECKING:
           from .character import Character
       ```
       and replace runtime references with forward strings in type hints: `def foo(bar: "Character"): ...`
     - Or perform **local (deferred) imports** inside functions/methods where needed.
   - Keep **runtime** imports acyclic.
   - Verify all needed `__init__.py` files exist in packages so relative imports work.

3. **Stabilize module boundaries**:
   - Ensure `mud/models/obj.py` exports `ObjIndex`, `ObjectData`, and `Affect` as expected by callers.
   - If renames occurred during the merge, add compatibility aliases to avoid breakage (e.g., `Affect = AffectData` if tests expect `Affect`).

4. **Lint-safe syntax & quick hygiene**:
   - Remove any stray `print`/debug or conflict junk.
   - Keep formatting consistent; do not introduce behavior changes unless tests require it.

5. **Prove collection passes**:
   - Run:
     ```
     python -m pytest -q
     ```
   - If collection still errors, iterate until **collection succeeds with 0 errors**.
   - If specific tests fail **after** collection, leave them; this task’s acceptance is collection success.

6. **Commit small, descriptive changes**:
   - Example messages:
     - `fix(models): resolve merge conflict in character.py`
     - `fix(imports): break circular import between obj.py and character.py using TYPE_CHECKING`
     - `chore: ensure package __init__.py files present`

## Acceptance criteria
- Running `python -m pytest -q` performs **test discovery/collection without any errors**.
- No remaining conflict markers anywhere in the repo.
- `mud/models` imports do not raise `SyntaxError` or `ImportError` at import time.

## Useful implementation tips
- When resolving `character.py` conflicts, keep class/enum/function signatures that tests likely rely upon. If both sides added attributes/methods, merge the union where logically consistent.
- Prefer forward references in type hints to avoid import-time cycles:
  ```python
  from __future__ import annotations
  ```
  Then use `"Character"` in annotations.
- If `obj.py` must refer to `Character` at runtime, move that import into the specific function that needs it to avoid top-level cycles.

## Commands to run (in this order)
1. `git status && git rev-parse --abbrev-ref HEAD`
2. `git grep -n -E '<<<<<<<|=======|>>>>>>>'`
3. Fix files; then `python -m pytest -q`
4. Repeat edits until collection is clean.
5. `git add -A && git commit -m "fix: resolve conflicts and break circular imports for clean pytest collection"`

Return the final diff of files you changed and the last pytest output showing **0 errors during collection**.
