from __future__ import annotations

import os


def imc_enabled() -> bool:
    """Feature flag for IMC. Disabled by default."""
    return os.getenv("IMC_ENABLED", "false").lower() in {"1", "true", "yes"}


def maybe_open_socket() -> None:
    """No-op when IMC is disabled. Never opens sockets in disabled mode."""
    if not imc_enabled():
        return None
    # Intentionally unimplemented: networking is out of scope for P0 stub.
    raise NotImplementedError("IMC networking not implemented in stub")

