from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from itertools import count
from typing import TYPE_CHECKING

from mud.models.character import Character

if TYPE_CHECKING:
    from mud.net.connection import TelnetStream


_descriptor_sequence = count(1)


def _next_descriptor_id() -> int:
    return next(_descriptor_sequence)


@dataclass
class Session:
    name: str
    character: Character
    reader: asyncio.StreamReader
    connection: TelnetStream
    account_name: str = ""
    last_command: str = field(default="")
    repeat_count: int = field(default=0)
    editor: str | None = None
    editor_state: dict[str, object] = field(default_factory=dict)
    ansi_enabled: bool = True
    go_ahead_enabled: bool = True
    show_buffer: list[str] | None = None
    show_index: int = 0
    show_page_lines: int = 0
    descriptor_id: int = field(default_factory=_next_descriptor_id)

    def clear_paging(self) -> None:
        """Reset any active show_string pagination state."""

        self.show_buffer = None
        self.show_index = 0
        self.show_page_lines = 0

    async def start_paging(self, text: str, page_lines: int) -> None:
        """Initialize pagination for *text* and deliver the first page."""

        if not text:
            await self._send_text(text)
            return

        if page_lines <= 0:
            await self._send_text(text)
            return

        segments = _split_for_paging(text)
        if not segments:
            await self._send_text(text)
            return

        if self.show_buffer:
            self.show_buffer.extend(segments)
            if self.show_page_lines <= 0:
                self.show_page_lines = page_lines
            return

        self.show_buffer = segments
        self.show_index = 0
        self.show_page_lines = page_lines
        await self.send_next_page()

    async def send_next_page(self) -> bool:
        """Send the next page of buffered output.

        Returns ``True`` when more pages remain, otherwise ``False``.
        """

        if not self.show_buffer:
            self.clear_paging()
            return False

        connection = getattr(self, "connection", None)
        if connection is None or not hasattr(connection, "send_text"):
            # Unable to deliver via telnet framing; fall back to a single flush.
            combined = "".join(self.show_buffer[self.show_index :])
            await self._send_text(combined)
            self.clear_paging()
            return False

        page_limit = self.show_page_lines if self.show_page_lines > 0 else len(self.show_buffer)
        lines_sent = 0
        end_index = self.show_index
        chunks: list[str] = []

        while end_index < len(self.show_buffer):
            segment = self.show_buffer[end_index]
            chunks.append(segment)
            if _segment_ends_line(segment):
                lines_sent += 1
            if lines_sent >= page_limit:
                end_index += 1
                break
            end_index += 1

        else:
            end_index = len(self.show_buffer)

        payload = "".join(chunks)
        if payload:
            await connection.send_text(payload, newline=False)

        self.show_index = end_index
        if self.show_index >= len(self.show_buffer):
            self.clear_paging()
            return False

        await connection.send_line("[Hit Return to continue]")
        return True

    async def _send_text(self, text: str) -> None:
        connection = getattr(self, "connection", None)
        if connection is None:
            return
        text = _normalize_rom_newlines(text)
        if hasattr(connection, "send_text"):
            await connection.send_text(text, newline=False)
        elif hasattr(connection, "send_line"):
            await connection.send_line(text)


def _split_for_paging(text: str) -> list[str]:
    normalized = _normalize_rom_newlines(text)
    segments: list[str] = []
    last_index = 0
    for match in re.finditer(r"\n\r|\r\n|\r|\n", normalized):
        end = match.end()
        segments.append(normalized[last_index:end])
        last_index = end
    if last_index < len(normalized):
        segments.append(normalized[last_index:])
    return segments


def _segment_ends_line(segment: str) -> bool:
    return (
        segment.endswith("\n\r")
        or segment.endswith("\r\n")
        or segment.endswith("\n")
        or segment.endswith("\r")
    )


SESSIONS: dict[str, Session] = {}


def get_online_players() -> list[Character]:
    return [sess.character for sess in SESSIONS.values()]


def _normalize_rom_newlines(text: str) -> str:
    if "\r\n" not in text:
        return text
    return text.replace("\r\n", "\n\r")
