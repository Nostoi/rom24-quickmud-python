from pathlib import Path
from typing import Any, Dict, List


def log_agent_action(agent_id: str, observation: Dict[str, Any], action: str, result: str) -> None:
    Path("logs").mkdir(exist_ok=True)
    log_path = Path("logs") / f"agent_{agent_id}.log"
    with log_path.open("a") as f:
        f.write(f"\nOBS: {observation}\nACT: {action}\nRES: {result}\n{'='*40}\n")
