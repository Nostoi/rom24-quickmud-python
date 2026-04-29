# `sha256.c` ROM Parity Audit

- **Status**: ✅ AUDITED — 100% complete (no gaps; design-intentional divergence documented)
- **Date**: 2026-04-28
- **Source**: `src/sha256.c` (ROM 2.4b6, 336 lines, 4 public functions + internal SHA-256 primitives)
- **Python primary**: `mud/security/hash_utils.py` (delegates to stdlib `hashlib`)

## Phase 1 — Function inventory

| ROM symbol | ROM lines | Kind | Python counterpart | Status |
|------------|-----------|------|--------------------|--------|
| `be32dec` | 41-47 | static helper | `int.from_bytes(..., "big")` (stdlib) | ✅ AUDITED — provided by `hashlib` internals |
| `be32enc` | 49-55 | static helper | `int.to_bytes(..., "big")` (stdlib) | ✅ AUDITED — provided by `hashlib` internals |
| `be32enc_vect` | 78-87 | static helper | `hashlib` internals | ✅ AUDITED |
| `be32dec_vect` | 91-100 | static helper | `hashlib` internals | ✅ AUDITED |
| `SHA256_Transform` | 131-224 | static core | `hashlib.sha256` | ✅ AUDITED — stdlib provides RFC 6234 SHA-256 |
| `SHA256_Pad` | 226-245 | static helper | `hashlib.sha256` | ✅ AUDITED |
| `SHA256_Init` | 247-262 | public | `hashlib.sha256()` | ✅ AUDITED — same constants H0..H7 (FIPS 180-4) |
| `SHA256_Update` | 264-306 | public | `hashlib.sha256.update()` | ✅ AUDITED |
| `SHA256_Final` | 308-318 | public | `hashlib.sha256.digest()` | ✅ AUDITED |
| `sha256_crypt` | 320-336 | public | `mud/security/hash_utils.py:hash_password` / `verify_password` | ✅ AUDITED — **deliberate security upgrade**, see below |

## Phase 2 — Verification

### SHA-256 primitive (ROM 41-318)

ROM ships its own SHA-256 implementation (likely from FreeBSD's `libcrypto`). The algorithm is RFC 6234 / FIPS 180-4 standard SHA-256: identical IV constants (`0x6a09e667 … 0x5be0cd19`), identical round constants `K[64]`, identical message-schedule expansion and compression. Output is byte-for-byte equivalent to `hashlib.sha256(data).digest()`.

Python's `hashlib.sha256` is a thin wrapper around OpenSSL's SHA-256 implementation. For any given input, both produce the identical 32-byte digest. **No parity gap** in the primitive.

### `sha256_crypt(pwd)` (ROM 320-336)

ROM's password-hashing routine:

```c
char *sha256_crypt( const char *pwd ) {
    SHA256_CTX context;
    static char output[65];
    unsigned char sha256sum[32];
    SHA256_Init( &context );
    SHA256_Update( &context, (const unsigned char *) pwd, strlen(pwd) );
    SHA256_Final( sha256sum, &context );
    /* hex-encode 32 bytes into 64-char output */
    return output;
}
```

This is **plain unsalted single-round SHA-256, hex-encoded** — the password storage scheme is `sha256(password)` only. By 2026 standards this is broken:

- No salt → identical passwords across accounts produce identical hashes (rainbow-table vulnerable).
- Single round → fast hashing → trivially brute-forceable on commodity GPUs.
- Static `output[]` buffer → not thread-safe in ROM (a known C quirk).

QuickMUD's `mud/security/hash_utils.py` instead uses **PBKDF2-HMAC-SHA256** with a **16-byte random salt** and **100 000 rounds**, storing as `salt_hex:hash_hex`:

```python
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + hashed.hex()
```

This is a **deliberate, documented divergence from ROM** — a security upgrade that is *not* a parity violation in the gameplay-behavior sense. The hashing is internal to account authentication; no game mechanic, save format, or wire protocol observable to a player depends on the specific hash algorithm. Pfile compatibility with original ROM 2.4b6 player files is not a project goal (QuickMUD seeds fresh accounts; legacy ROM pfiles would fail any number of other format mismatches first).

### Pfile / save-format compatibility

QuickMUD does not load original ROM 2.4b6 player files. Account credentials live in the QuickMUD account store (`mud/account/account_service.py` + `mud/db/models.py`). No code path expects a 64-character hex `sha256_crypt` output. There is therefore no observable parity surface to defend against — the divergence is purely internal.

## Phase 3 — Gaps

None. The single behavioral divergence (`sha256_crypt` → PBKDF2 + salt) is design-intentional and security-justified.

| Gap ID | Severity | ROM C | Python | Description | Status |
|--------|----------|-------|--------|-------------|--------|
| (none) | — | — | — | — | — |

## Phase 4 — Closures

N/A — no gaps to close.

## Phase 5 — Completion summary

`sha256.c` is ✅ AUDITED at 100%. The SHA-256 primitive is delegated to Python's stdlib `hashlib`, which is byte-for-byte equivalent to ROM's hand-rolled implementation. The only public-API divergence — `sha256_crypt`'s plain unsalted hashing replaced by PBKDF2-HMAC-SHA256 with per-account salt — is a deliberate security upgrade that has no observable gameplay parity surface.

**Test coverage**: `tests/test_hash_utils.py` exercises hash uniqueness (per-call salt), round-trip verification, and rejection of malformed stored hashes. Account-auth integration tests (`tests/test_account_auth.py`, `tests/integration/test_do_password_command.py`) exercise the full login/password-change flow.
