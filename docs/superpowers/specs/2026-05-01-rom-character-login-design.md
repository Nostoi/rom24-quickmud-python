# ROM Character Login Restoration Design

## Goal

Remove QuickMUD's Python-only account system and restore the ROM 2.4b6
character-based login and password model exactly, so login, reconnect, and new
character creation follow `src/nanny.c` / `src/save.c` semantics with no
account-layer abstraction.

## Problem Statement

The current Python port introduced a `PlayerAccount` abstraction that does not
exist in ROM 2.4b6. That abstraction changed observable login behavior:

- players authenticate to an account before selecting or creating a character
- passwords belong to accounts instead of characters
- active-session tracking is keyed to account names rather than character names
- persistence joins characters through account ownership rather than loading a
  single player by character name

This is an architectural improvement, not a faithful port. It violates the
project rule that ROM behavior is the source of truth unless a documented
runtime divergence is strictly required.

## Source-of-Truth ROM Behavior

The restored Python behavior must match these ROM surfaces:

- `src/nanny.c`
  - `CON_GET_NAME`: prompt for a character name, not an account
  - existing character path: `load_char_obj(d, argument)` then old-password flow
  - new character path: confirm name, gather new password, continue directly
    into race/sex/class/alignment/customization prompts
  - duplicate/reconnect behavior is keyed by character name
- `src/comm.c`
  - `check_parse_name` validates character names
  - duplicate-newbie sweep is name-based
- `src/save.c`
  - player persistence is stored per character/pfile
  - password belongs to the character (`ch->pcdata->pwd`)
  - save/load path is keyed by capitalized character name

## Non-Goals

- Preserve multi-character-per-account convenience
- Preserve account bans as a user-facing login concept
- Preserve account-specific tables, APIs, or tests
- Introduce compatibility shims that keep both account and ROM flows alive

## Target Behavior

### Login Flow

The login prompt asks for a character name. The flow then branches exactly like
ROM:

1. If the name is invalid, reject it.
2. If the character exists, prompt for that character's password.
3. If the password is wrong, disconnect after the first failure.
4. If the character is already playing, follow the reconnect / break-connect
   path keyed by character name.
5. If the character does not exist, prompt to confirm creation of a new
   character with that name.

### New Character Creation

New-character creation starts immediately after confirming the new name. The
password collected in the new-password / confirm-password prompts belongs to the
character being created. After that, the flow proceeds through the ROM creation
states already mirrored in the current codebase.

### Persistence Model

Character persistence becomes direct:

- one persisted character row per player character
- password hash stored on the character record
- character load keyed by character name only
- character save keyed by character identity only

No account ownership join remains in the runtime auth path.

### Reconnect and Duplicate Session Rules

Reconnect, duplicate-login checks, and active-session tracking are keyed by the
character name, not an account name. The Python `SESSIONS` map and any
auxiliary active-session set must reflect the same identity boundary ROM uses.

## Data Model Changes

### Remove

- `PlayerAccount` ORM model
- `player_accounts` table usage
- `Character.player_id`
- account-based relationship loading
- account-name references on runtime character state where they only support the
  removed account abstraction

### Add or Re-home

- persisted password hash on the character model if not already stored there
- character-auth helper(s) that verify a submitted password against the
  character's saved password
- direct character existence and load helpers

### Database Reset Requirement

This change assumes a development-only reset, not a compatibility migration.

- wipe the existing player/account database as part of the change
- rebuild the schema without `PlayerAccount` or `Character.player_id`
- do not write migration code, compatibility shims, or legacy account import
  logic

Because the account system is being removed as a non-ROM divergence, adding new
code to preserve or translate that model is out of scope.

## Code Boundaries

### Primary Runtime Files

- `mud/net/connection.py`
  - replace `_run_account_login`
  - remove account creation prompt path
  - remove character-selection flow that exists only because of accounts
  - rename helpers as needed to reflect ROM character login semantics

- `mud/account/account_service.py`
  - remove account APIs
  - preserve or relocate ROM-valid character creation helpers
  - keep `check_parse_name` parity helpers, but make them character-focused

- `mud/account/account_manager.py`
  - replace `(username, char_name)` loads with direct character-name loads
  - remove account-link repair logic

### Persistence / Database

- `mud/db/models.py`
- `mud/db/session.py`
- `mud/db/init.py`
- `mud/db/migrations.py`
- any seed or loader code that creates `PlayerAccount` rows
- startup/dev docs or scripts that recreate the wiped schema cleanly

### Tests

- replace account-auth tests with character-auth parity tests
- update integration tests that assume multi-character accounts
- remove fixtures that create `PlayerAccount` rows unless they are being
  rewritten as migration tests

### Documentation / Tracking

- `README.md`
- `CHANGELOG.md`
- `docs/parity/NANNY_C_AUDIT.md`
- `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`
- `docs/sessions/SESSION_STATUS.md`
- new `docs/sessions/SESSION_SUMMARY_2026-05-01_*.md`

## Testing Strategy

This removal must be driven by failing tests first.

### Required Behavioral Tests

- existing-character login succeeds with correct password
- wrong password disconnects on first attempt
- new-character path creates the character directly, with no account layer
- reconnect logic is keyed by character name
- character persistence survives reload/restart keyed by character name alone

### Required Regression Coverage

- bans and lockouts still behave correctly after identity changes
- nanny parity tests still match ROM prompts and disconnect behavior
- telnet server end-to-end login tests still pass with the new flow

## Documentation Requirements

The removal must be explicitly documented, not merely implied by code changes.

Required documentation changes:

- `CHANGELOG.md`: note the removal of the non-ROM account system and restoration
  of ROM character-based login
- `README.md`: remove references to account login and describe character-based
  authentication, including the development database reset
- parity docs: update `nanny.c` and related tracker notes to stop treating the
  account system as an accepted surface
- session docs: record the migration/removal and any legacy-data caveats

## Risks

### High Risk

- existing tests assume account-based ownership and login
- wiping the dev database will invalidate account-era local test data
- session/reconnect behavior may subtly regress if name-keyed identity is not
  applied consistently

### Medium Risk

- bans code currently distinguishes account bans from host bans
- persistence helpers may rely on `pcdata.account_name`
- docs and tracker entries currently normalize the account system as a partial
  parity layer

## Recommended Implementation Order

1. Lock ROM character-login behavior with failing tests.
2. Convert the runtime login flow from account-based to character-based.
3. Move password persistence to the character model and remove account joins.
4. Remove account-era schema/data assumptions and reset the development
   database.
5. Rewrite docs and parity trackers to document removal of the non-ROM system.

## Acceptance Criteria

The work is complete when all of the following are true:

- no runtime login path requires or exposes a separate account identity
- passwords are owned by characters, not accounts
- reconnect and duplicate-session checks are keyed by character name
- account tables/models/helpers are removed rather than preserved through
  compatibility code
- docs explicitly state that the account system was removed as a non-parity
  divergence and that development data was reset
- targeted auth, nanny, and telnet tests pass
