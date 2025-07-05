from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
from fastapi import WebSocket
from mud.models.character import Character


@dataclass
class WebSocketPlayerSession:
    """Session wrapper for WebSocket clients."""

    websocket: WebSocket
    character: Character
    name: str
    session_type: str = "websocket"

    async def send(self, payload: Dict[str, Any]) -> None:
        await self.websocket.send_json(payload)

    async def recv(self) -> Dict[str, Any]:
        return await self.websocket.receive_json()
