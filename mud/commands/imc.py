from __future__ import annotations

from mud.imc import imc_enabled


def do_imc(char, args: str) -> str:
    """IMC command stub.

    - Disabled (default): returns a gated message.
    - Enabled: returns basic help/usage; no sockets opened here.
    """
    if not imc_enabled():
        return "IMC is disabled. Set IMC_ENABLED=true to enable."

    if not args or args.strip().lower() in {"help", "?"}:
        return "IMC is enabled (stub). Usage: imc send <channel> <message>"

    return "IMC stub: command not implemented."

