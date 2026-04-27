from __future__ import annotations

import asyncio

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from mud.config import CORS_ORIGINS, HOST, PORT
from mud.config import load_qmconfig
from mud.db.migrations import run_migrations
from mud.game_loop import async_game_loop
from mud.net.connection import handle_connection_with_stream
from mud.security import bans
from mud.world.world_state import initialize_world

from .websocket_stream import WebSocketStream

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
    load_qmconfig()
    run_migrations()
    initialize_world("area/area.lst")
    bans.load_bans_file()
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
    stream = WebSocketStream(websocket)
    await handle_connection_with_stream(
        stream,
        host_for_ban=stream.peer_host,
        connection_type="WebSocket",
    )


def run(host: str = HOST, port: int = PORT) -> None:
    uvicorn.run("mud.network.websocket_server:app", host=host, port=port)


if __name__ == "__main__":
    run()
