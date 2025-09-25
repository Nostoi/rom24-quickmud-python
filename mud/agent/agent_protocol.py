from abc import ABC, abstractmethod


class AgentInterface(ABC):
    @abstractmethod
    def get_observation(self) -> dict:
        """Return structured game state view."""
        raise NotImplementedError

    @abstractmethod
    def get_available_actions(self) -> list[str]:
        """Return a list of valid actions the agent can choose from."""
        raise NotImplementedError

    @abstractmethod
    def perform_action(self, action: str, args: list[str]) -> str:
        """Execute an action in-game. Returns textual feedback."""
        raise NotImplementedError
