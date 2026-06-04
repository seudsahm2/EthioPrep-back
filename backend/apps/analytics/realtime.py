from asgiref.sync import async_to_sync
from django.utils import timezone

from config.socketio import sio

from .gamification import leaderboard_rows


def emit_leaderboard_update() -> None:
    payload = {"rows": leaderboard_rows(limit=100), "sent_at": timezone.now().isoformat()}
    try:
        async_to_sync(sio.emit)("leaderboard:update", payload, room="leaderboard")
    except Exception:
        # Realtime should never break core exam/practice flow.
        pass
