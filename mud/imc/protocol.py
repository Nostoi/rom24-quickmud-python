from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    """Minimal IMC-like frame for testing parser/serializer.

    Format (text line):
      "<type> <from> <to> :<message>"
    Example:
      "chat alice@quickmud * :Hello world"
    """

    type: str
    source: str
    target: str
    message: str


def parse_frame(line: str) -> Frame:
    parts = line.strip().split(" ", 3)
    if len(parts) < 4 or not parts[3].startswith(":"):
        raise ValueError("invalid IMC frame: expected '<type> <from> <to> :<message>'")
    ftype, source, target, msg = parts
    return Frame(type=ftype, source=source, target=target, message=msg[1:])


def serialize_frame(frame: Frame) -> str:
    return f"{frame.type} {frame.source} {frame.target} :{frame.message}"

