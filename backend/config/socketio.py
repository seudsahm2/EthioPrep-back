from __future__ import annotations

from django.conf import settings
import socketio

from apps.analytics.gamification import leaderboard_rows


def _allowed_origins() -> list[str] | str:
    origins = list(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
    # Allow local/ngrok frontend clients in development without strict handshake failures.
    return origins if origins else "*"


from asgiref.sync import sync_to_async

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=_allowed_origins(),
)


@sio.event
async def connect(sid, environ, auth=None):
    await sio.enter_room(sid, "leaderboard")
    rows = await sync_to_async(leaderboard_rows)(limit=100)
    await sio.emit("leaderboard:update", {"rows": rows}, to=sid)


@sio.event
async def disconnect(sid):
    return None


@sio.on("leaderboard:subscribe")
async def leaderboard_subscribe(sid, data):
    await sio.enter_room(sid, "leaderboard")
    rows = await sync_to_async(leaderboard_rows)(limit=100)
    await sio.emit("leaderboard:update", {"rows": rows}, to=sid)


@sio.on("leaderboard:unsubscribe")
async def leaderboard_unsubscribe(sid, data):
    await sio.leave_room(sid, "leaderboard")


def create_socketio_application(django_asgi_application):
    return socketio.ASGIApp(
        socketio_server=sio,
        other_asgi_app=django_asgi_application,
        socketio_path="socket.io",
    )
