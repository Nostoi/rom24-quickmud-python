from pathlib import Path
from typing import Any


def log_agent_action(agent_id: str, observation: dict[str, Any], action: str, result: str) -> None:
    Path("log").mkdir(exist_ok=True)
    log_path = Path("log") / f"agent_{agent_id}.log"
    with log_path.open("a") as f:
        f.write(f"\nOBS: {observation}\nACT: {action}\nRES: {result}\n{'=' * 40}\n")
