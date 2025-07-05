from abc import ABC, abstractmethod
from typing import Dict, List


class AgentInterface(ABC):
    @abstractmethod
    def get_observation(self) -> Dict:
        """Return structured game state view."""
        raise NotImplementedError

    @abstractmethod
    def get_available_actions(self) -> List[str]:
        """Return a list of valid actions the agent can choose from."""
        raise NotImplementedError

    @abstractmethod
    def perform_action(self, action: str, args: List[str]) -> str:
        """Execute an action in-game. Returns textual feedback."""
        raise NotImplementedError
