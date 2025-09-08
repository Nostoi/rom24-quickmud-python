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


def rotate_admin_log(today: datetime | None = None) -> Path:
    """Rotate admin.log to a date-stamped file once per (real) day.

    - If ``log/admin.log`` exists, rename it to ``log/admin-YYYYMMDD.log``.
    - Always return the new active path (``log/admin.log``).
    The ``today`` parameter allows tests to inject a deterministic date.
    """
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    active = log_dir / "admin.log"
    if not active.exists():
        return active
    dt = today or datetime.utcnow()
    dated = log_dir / f"admin-{dt.strftime('%Y%m%d')}.log"
    # Avoid clobbering: if dated file exists, append current log and remove active
    if dated.exists():
        dated.open("a", encoding="utf-8").write(active.read_text(encoding="utf-8"))
        active.unlink()
    else:
        active.rename(dated)
    # Create a fresh active log file
    active.touch()
    return active
