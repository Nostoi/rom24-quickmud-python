from __future__ import annotations

import asyncio

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from mud.account import load_character, save_character
from mud.commands import process_command
from mud.config import CORS_ORIGINS, HOST, PORT
from mud.game_loop import async_game_loop
from mud.world.world_state import create_test_character, initialize_world

from .websocket_session import WebSocketPlayerSession

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global game tick task
_game_task = None


@app.on_event("startup")
async def startup() -> None:
    global _game_task
    initialize_world(None)
    # Start game loop as background task
    _game_task = asyncio.create_task(async_game_loop())
    print("🎮 Game loop started for WebSocket server")


@app.on_event("shutdown")
async def shutdown() -> None:
    global _game_task
    if _game_task:
        _game_task.cancel()
        try:
            await _game_task
        except asyncio.CancelledError:
            print("Game loop stopped")
            pass


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
            await session.send(
                {
                    "type": "output",
                    "text": response,
                    "room": char.room.vnum if getattr(char, "room", None) else None,
                    "hp": char.hit,
                }
            )
            while char.messages:
                msg = char.messages.pop(0)
                await session.send(
                    {
                        "type": "output",
                        "text": msg,
                        "room": char.room.vnum if getattr(char, "room", None) else None,
                        "hp": char.hit,
                    }
                )
    finally:
        save_character(char)
        if char.room:
            char.room.remove_character(char)


def run(host: str = HOST, port: int = PORT) -> None:
    uvicorn.run("mud.network.websocket_server:app", host=host, port=port)


if __name__ == "__main__":
    run()
