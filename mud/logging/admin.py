from __future__ import annotations

from datetime import datetime
from pathlib import Path


def log_admin_command(actor: str, command: str, args: str) -> None:
    """Append a single admin-command entry to log/admin.log.

    Format: ISO timestamp, actor, command, args (space-joined).
    Creates the log directory if missing.
    """
    Path("log").mkdir(exist_ok=True)
    line = f"{datetime.utcnow().isoformat()}Z\t{actor}\t{command}\t{args}\n"
    (Path("log") / "admin.log").open("a", encoding="utf-8").write(line)

