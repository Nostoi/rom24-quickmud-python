from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from mud.net.ansi import render_ansi

MAX_INPUT_LENGTH = 256


class WebSocketStream:
    """WebSocket adapter matching the connection interface used by telnet/SSH."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self._echo_enabled = True
        self.ansi_enabled = True
        self.peer_host: str | None = None
        self._go_ahead_enabled = False
        self._closed = False
        self._in_game = False
        self._character = None
        self._session_state = "connected"
        self._pushback: deque[str] = deque()

        client = getattr(websocket, "client", None)
        if client is not None:
            self.peer_host = getattr(client, "host", None)

    def set_ansi(self, enabled: bool) -> None:
        self.ansi_enabled = bool(enabled)

    def set_in_game(self, character) -> None:
        self._in_game = True
        self._character = character
        self._session_state = "game"

    def _infer_session_state(self, prompt: str) -> str:
        lowered = prompt.strip().lower()
        if self._in_game:
            return "game"
        if lowered.startswith("account:"):
            return "account"
        if "password" in lowered:
            return "password"
        if lowered.startswith("character:"):
            return "character"
        if any(
            token in lowered
            for token in (
                "choose your race",
                "sex (m/f)",
                "choose your class",
                "which alignment",
                "customize",
                "customization>",
                "choose your hometown",
                "choose your starting weapon",
                "keep these stats",
                "new password",
                "confirm password",
            )
        ):
            return "character_creation"
        return "session"

    def _normalize(self, message: str, *, newline: bool) -> str:
        rendered = render_ansi(message, self.ansi_enabled)
        normalized = rendered.replace("\r\n", "\n").replace("\n\r", "\n")
        if newline and not normalized.endswith("\n"):
            normalized += "\n"
        return normalized

    async def flush(self) -> None:
        return

    async def negotiate(self) -> None:
        return

    async def disable_echo(self) -> None:
        self._echo_enabled = False

    async def enable_echo(self) -> None:
        self._echo_enabled = True

    async def send_text(self, message: str, *, newline: bool = False) -> None:
        if self._closed:
            return
        # TODO: remove debug timestamp before merging to master
        payload: dict[str, Any] = {
            "type": "output" if self._in_game else "info",
            "text": self._normalize(message, newline=newline),
            "ts": datetime.now().isoformat(timespec="milliseconds"),
        }
        if self._in_game and self._character is not None:
            room = getattr(self._character, "room", None)
            payload["room"] = getattr(room, "vnum", None) if room is not None else None
            payload["hp"] = getattr(self._character, "hit", None)
        try:
            await self.websocket.send_json(payload)
        except (WebSocketDisconnect, RuntimeError):
            self._closed = True
            return

    async def send_line(self, message: str) -> None:
        await self.send_text(message, newline=True)

    def set_go_ahead_enabled(self, enabled: bool) -> None:
        self._go_ahead_enabled = bool(enabled)

    async def send_prompt(self, prompt: str, *, go_ahead: bool | None = None) -> None:
        if self._closed:
            return
        if go_ahead is not None:
            self._go_ahead_enabled = bool(go_ahead)
        self._session_state = self._infer_session_state(prompt)
        try:
            await self.websocket.send_json(
                {
                    "type": "prompt",
                    "text": prompt,
                    "session_state": self._session_state,
                    "secret": not self._echo_enabled,
                }
            )
        except (WebSocketDisconnect, RuntimeError):
            self._closed = True
            return

    async def readline(self, *, max_length: int = MAX_INPUT_LENGTH) -> str | None:
        if self._closed:
            return None

        if self._pushback:
            return self._pushback.popleft()

        while True:
            try:
                message = await self.websocket.receive_json()
            except WebSocketDisconnect:
                self._closed = True
                return None

            if not isinstance(message, dict):
                continue

            text = message.get("text")
            if not isinstance(text, str):
                continue

            text = text[: max_length - 2]
            return text

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self.websocket.close()
        except RuntimeError:
            pass
