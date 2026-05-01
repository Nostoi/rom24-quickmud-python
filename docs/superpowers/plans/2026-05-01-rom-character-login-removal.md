# ROM Character Login Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the non-ROM account system and restore exact ROM-style character-based login, password ownership, and persistence.

**Architecture:** Convert the current account-first login stack into a character-first stack keyed entirely by character name. Store the password hash directly on persisted characters, remove `PlayerAccount`/`player_id` ownership plumbing, reset the development database instead of migrating legacy account data, and rewrite auth tests/docs to reflect ROM `nanny.c` / `save.c` behavior.

**Tech Stack:** Python 3, SQLAlchemy ORM, pytest, asyncio telnet login flow, SQLite development database.

---

### Task 1: Lock ROM Character Login Behavior With Failing Tests

**Files:**
- Modify: `tests/test_account_auth.py`
- Modify: `tests/integration/test_nanny_login_parity.py`
- Modify: `tests/test_telnet_server.py`

- [ ] **Step 1: Write the failing unit/parity tests**

Add tests that describe the ROM-shaped login API and remove account assumptions from the new assertions.

```python
def test_character_login_uses_character_name_and_password():
    from mud.account.account_service import create_character_record, login_character

    assert create_character_record("Hero", "secret")

    logged_in = login_character("Hero", "secret")
    assert logged_in is not None
    assert logged_in.name == "Hero"


def test_character_login_rejects_wrong_password_once():
    from mud.account.account_service import create_character_record
    from mud.net.connection import _run_character_login

    assert create_character_record("Hero", "secret")
    # drive the async prompt flow with one bad password and assert it returns None
```

- [ ] **Step 2: Run the focused tests to verify they fail for the right reason**

Run: `pytest tests/test_account_auth.py -k "character_login or account_create_and_login" -v`

Expected: FAIL because `create_character_record` / `login_character` / `_run_character_login` do not exist yet and current tests still encode account-based behavior.

- [ ] **Step 3: Rewrite telnet/login expectations to ROM prompts**

Add or rewrite a telnet-facing test that expects the first prompt to be `Name:` or the current ROM-equivalent character prompt and no account creation branch.

```python
async def test_telnet_server_creates_character_without_account_prompt():
    prompt = await reader.readuntil(b"Name: ")
    writer.write(b"Nova\r\n")
    confirm = await reader.readuntil(b"Did I get that right, Nova (Y/N)? ")
    assert b"Account:" not in prompt + confirm
```

- [ ] **Step 4: Run the telnet/parity tests to verify they fail**

Run: `pytest tests/integration/test_nanny_login_parity.py tests/test_telnet_server.py -k "login or telnet" -v`

Expected: FAIL because the live connection flow still prompts for `Account:` and routes through account selection.

- [ ] **Step 5: Commit the red test baseline**

```bash
git add tests/test_account_auth.py tests/integration/test_nanny_login_parity.py tests/test_telnet_server.py
git commit -m "test: lock ROM character-login expectations"
```

### Task 2: Replace Account Login Flow With ROM Character Login

**Files:**
- Modify: `mud/net/connection.py`
- Modify: `mud/account/account_service.py`
- Modify: `mud/account/__init__.py`
- Test: `tests/test_account_auth.py`
- Test: `tests/integration/test_nanny_login_parity.py`
- Test: `tests/test_telnet_server.py`

- [ ] **Step 1: Introduce character-auth helpers in `mud/account/account_service.py`**

Replace account-facing APIs with direct character-facing helpers. Keep the ROM-valid creation stat/group helpers in place.

```python
def character_exists(name: str) -> bool:
    session = SessionLocal()
    try:
        return session.query(Character).filter_by(name=name.capitalize()).first() is not None
    finally:
        session.close()


def login_character(name: str, raw_password: str) -> Character | None:
    session = SessionLocal()
    try:
        record = session.query(Character).filter_by(name=name.capitalize()).first()
        if record is None or not verify_password(raw_password, record.password_hash):
            return None
        runtime = from_orm(record)
        session.expunge(record)
        return runtime
    finally:
        session.close()
```

- [ ] **Step 2: Replace `_run_account_login` with `_run_character_login`**

Update `mud/net/connection.py` so the first prompt is for character name, then branch to old-password or new-character flow exactly like ROM `CON_GET_NAME`.

```python
async def _run_character_login(conn: TelnetStream, host_for_ban: str | None) -> tuple[Character, bool] | None:
    submitted = await _prompt(conn, "Name: ")
    if submitted is None:
        return None
    name = sanitize_character_name(submitted)
    if not is_valid_character_name(name):
        await _send_line(conn, "Illegal name, try another.")
        return None
    if character_exists(name):
        password = await _prompt(conn, "Password: ", hide_input=True)
        if password is None:
            return None
        char = login_character(name, password)
        if char is None:
            await _send_line(conn, "Wrong password.")
            return None
        return char, False
    confirmed = await _prompt_yes_no(conn, f"Did I get that right, {name.capitalize()} (Y/N)? ")
    ...
```

- [ ] **Step 3: Remove character-selection/account-creation flow branches**

Delete `_select_character` and any account-only logic. Route new-character creation directly from `_run_character_login` into `_run_character_creation_flow`.

```python
login_result = await _run_character_login(conn, host_for_ban)
if login_result is None:
    return
char, reconnecting = login_result
if getattr(char, "level", 0) <= 0:
    char = await _run_character_creation_flow(conn, char.name)
```

- [ ] **Step 4: Replace active-session helpers to use character names**

Rename or rewrite `release_account`, `clear_active_accounts`, `is_account_active` to character-name identity and update call sites.

```python
_active_characters: set[str] = set()

def release_character(name: str) -> None:
    _active_characters.discard(name.strip().lower())
```

- [ ] **Step 5: Run the focused auth/login tests to verify they pass**

Run: `pytest tests/test_account_auth.py tests/integration/test_nanny_login_parity.py tests/test_telnet_server.py -k "login or password or reconnect or telnet" -v`

Expected: PASS for the rewritten login-path tests.

- [ ] **Step 6: Commit the runtime login conversion**

```bash
git add mud/net/connection.py mud/account/account_service.py mud/account/__init__.py tests/test_account_auth.py tests/integration/test_nanny_login_parity.py tests/test_telnet_server.py
git commit -m "fix(parity): restore ROM character-first login flow"
```

### Task 3: Move Password Persistence Onto Characters And Remove Account Ownership

**Files:**
- Modify: `mud/db/models.py`
- Modify: `mud/account/account_manager.py`
- Modify: `mud/models/character.py`
- Modify: `mud/db/seed.py`
- Modify: `mud/scripts/load_test_data.py`
- Modify: `mud/persistence.py`
- Test: `tests/test_inventory_persistence.py`
- Test: `tests/integration/test_character_creation_runtime.py`
- Test: `tests/test_db_seed.py`

- [ ] **Step 1: Add character-owned password field and remove account ownership fields**

Update the ORM model so `Character` carries `password_hash`, and remove `PlayerAccount`, `player_id`, and `player` relationships.

```python
class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String, default="")
    level: Mapped[int] = mapped_column(Integer)
    hp: Mapped[int] = mapped_column(Integer)
```

- [ ] **Step 2: Rewrite character load/save helpers to key only by character name**

Update `mud/account/account_manager.py` and `mud/models/character.py:to_orm` so no username or `player_id` is required.

```python
def load_character(char_name: str) -> Character | None:
    session = SessionLocal()
    try:
        db_char = session.query(DBCharacter).filter(DBCharacter.name == char_name).first()
        ...
    finally:
        session.close()


def to_orm(character: Character) -> DBCharacter:
    return DBCharacter(
        name=character.name,
        password_hash=getattr(character.pcdata, "pwd", ""),
        ...
    )
```

- [ ] **Step 3: Write character-creation persistence directly**

Update the creation helper so newly created characters persist their password hash on the character row.

```python
def create_character_record(name: str, password: str, **kwargs) -> bool:
    new_char = Character(
        name=name.capitalize(),
        password_hash=hash_password(password),
        level=0,
        hp=20,
        room_vnum=ROOM_VNUM_SCHOOL,
        ...
    )
```

- [ ] **Step 4: Rewrite seed/bootstrap code to create a test character, not a test account**

Update `mud/db/seed.py`, `mud/scripts/load_test_data.py`, and user-facing command docstrings.

```python
def create_test_character():
    char = Character(
        name="Testman",
        password_hash=hash_password("admin"),
        level=1,
        hp=100,
        room_vnum=3001,
    )
```

- [ ] **Step 5: Run persistence-focused tests**

Run: `pytest tests/test_inventory_persistence.py tests/integration/test_character_creation_runtime.py tests/test_db_seed.py -v`

Expected: PASS after all direct character persistence call sites and fixtures are updated.

- [ ] **Step 6: Commit the schema/persistence rewrite**

```bash
git add mud/db/models.py mud/account/account_manager.py mud/models/character.py mud/db/seed.py mud/scripts/load_test_data.py mud/persistence.py tests/test_inventory_persistence.py tests/integration/test_character_creation_runtime.py tests/test_db_seed.py
git commit -m "refactor(parity): remove account-owned character persistence"
```

### Task 4: Remove Account-Era Schema Assumptions And Reset Development Database

**Files:**
- Modify: `mud/db/init.py`
- Modify: `mud/db/migrations.py`
- Modify: `mud/__main__.py`
- Modify: `README.md`
- Modify: `tests/test_account_auth.py`

- [ ] **Step 1: Replace account bootstrap with character-only schema setup**

Update database init so it recreates the development schema and seeds the default test character required by the current dev bootstrap flow.

```python
def initialize_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    create_test_character()
```

- [ ] **Step 2: Remove account-era migration helpers**

Strip helpers that only exist to preserve the old account-backed schema and make `run_migrations()` perform the clean development reset required by the spec.

```python
def run_migrations() -> None:
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
        Base.metadata.create_all(bind=conn)
    print("✅ Development database reset complete.")
```

- [ ] **Step 3: Update CLI text to stop mentioning accounts**

Rewrite `loadtestuser`/SSH command help so they refer to character login.

```python
@cli.command()
def loadtestuser():
    """Load a default test character."""
```

- [ ] **Step 4: Run the schema/bootstrap tests**

Run: `pytest tests/test_account_auth.py tests/test_db_seed.py -k "database or seed or character_login or character_exists or wrong_password" -v`

Expected: FAIL first on any tests still asserting account-based bootstrapping or auth names; update/remove those tests until the suite reflects character login only, then PASS.

- [ ] **Step 5: Reset the local dev database file**

Run: `rm -f mud.db`

Expected: the obsolete account-era SQLite file is removed so the next init/migration run recreates the schema without `player_accounts`.

- [ ] **Step 6: Commit the database reset path**

```bash
git add mud/db/init.py mud/db/migrations.py mud/__main__.py README.md tests/test_account_auth.py
git commit -m "chore(parity): reset dev database for character-only auth"
```

### Task 5: Rewrite Documentation, Trackers, And Verification Surface

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `docs/parity/NANNY_C_AUDIT.md`
- Modify: `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- Modify: `docs/sessions/SESSION_STATUS.md`
- Create: `docs/sessions/SESSION_SUMMARY_2026-05-01_ROM_CHARACTER_LOGIN_RESTORATION.md`

- [ ] **Step 1: Add changelog entry for removal of the non-ROM account system**

```markdown
## [Unreleased]

### Removed
- Eliminated the Python-only account login system and restored ROM 2.4b6 character-based authentication.

### Changed
- Login, reconnect, and new-character creation now key directly on character names and character-owned passwords.
```

- [ ] **Step 2: Rewrite README authentication references**

Replace phrases like “account login” / “account creation” with “character login” / “new character creation”, and document the development database reset.

```markdown
Authentication follows ROM 2.4b6: players log in with a character name and that character's password. The old Python-only account layer has been removed. Development databases created under the account-era schema must be discarded and recreated.
```

- [ ] **Step 3: Update parity trackers to remove account-system normalization**

Edit `docs/parity/NANNY_C_AUDIT.md` and `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` so they no longer describe account semantics as accepted parity behavior.

```markdown
The prior Python-only account abstraction was removed. `CON_GET_NAME` and the old/new password states now mirror ROM's character-based identity boundary.
```

- [ ] **Step 4: Write the session handoff summary**

Create a dated session summary documenting the removal, dev database wipe, key file changes, and exact verification commands/results.

```markdown
# Session Summary — 2026-05-01 — ROM character login restoration

- Removed `PlayerAccount` and account-first login flow
- Restored character-owned password persistence
- Reset development database schema
```

- [ ] **Step 5: Run final verification commands**

Run: `pytest tests/test_account_auth.py tests/integration/test_nanny_login_parity.py tests/test_telnet_server.py tests/integration/test_character_creation_runtime.py -v`

Run: `ruff check .`

Expected: PASS on targeted auth/persistence suites and clean lint output.

- [ ] **Step 6: Commit the docs/tracker finalization**

```bash
git add CHANGELOG.md README.md docs/parity/NANNY_C_AUDIT.md docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md docs/sessions/SESSION_STATUS.md docs/sessions/SESSION_SUMMARY_2026-05-01_ROM_CHARACTER_LOGIN_RESTORATION.md
git commit -m "docs(parity): record account-system removal"
```
