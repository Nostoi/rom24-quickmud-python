from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from mud.config import HOST, PORT, CORS_ORIGINS
from mud.world.world_state import initialize_world, create_test_character
from mud.account import load_character, save_character
from mud.commands import process_command
from .websocket_session import WebSocketPlayerSession

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    initialize_world(None)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "info", "text": "Welcome to PythonMUD. What is your name?"})
    try:
        data = await websocket.receive_json()
    except WebSocketDisconnect:
        return
    name = data.get("text", "guest")
    char = load_character(name, name)
    if not char:
        char = create_test_character(name, 3001)
    elif char.room:
        char.room.add_character(char)

    session = WebSocketPlayerSession(websocket=websocket, character=char, name=name)
    char.connection = session

    try:
        while True:
            try:
                message = await session.recv()
            except WebSocketDisconnect:
                break
            if message.get("type") != "command":
                continue
            command = message.get("text", "").strip()
            if not command:
                continue
            response = process_command(char, command)
            await session.send({
                "type": "output",
                "text": response,
                "room": char.room.vnum if getattr(char, "room", None) else None,
                "hp": char.hit,
            })
            while char.messages:
                msg = char.messages.pop(0)
                await session.send({
                    "type": "output",
                    "text": msg,
                    "room": char.room.vnum if getattr(char, "room", None) else None,
                    "hp": char.hit,
                })
    finally:
        save_character(char)
        if char.room:
            char.room.remove_character(char)


def run(host: str = HOST, port: int = PORT) -> None:
    uvicorn.run("mud.network.websocket_server:app", host=host, port=port)


if __name__ == "__main__":
    run()
