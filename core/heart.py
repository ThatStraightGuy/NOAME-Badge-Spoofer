"""
lib's magic — Discord Game Badge Spoofer
Made by Yeti [ @yvlsoul ]

For educational and research purposes only.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Callable, Iterator, Sequence

from core.games import LibsGame
from core.state import LibsState

LIBS_ME_URL = "https://discord.com/api/v9/users/@me?with_analytics_token=true"
LIBS_SCIENCE_URL = "https://discord.com/api/v9/science"
LIBS_PROPERTIES_URL = "https://cordapi.dolfi.es/api/v2/properties/windows"

LIBS_CLIENT_VERSION = "1.0.9253"
LIBS_CLIENT_BUILD_NUMBER = 594031
LIBS_NATIVE_BUILD_NUMBER = 88414
LIBS_OS_VERSION = "10.0.26200"
LIBS_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)

LIBS_BATCH_SIZE = 50
LIBS_BATCH_DELAY = 0.3

BATCH_SIZE = LIBS_BATCH_SIZE
BATCH_DELAY = LIBS_BATCH_DELAY


def libs_local_props() -> dict:
    return {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": LIBS_CLIENT_VERSION,
        "os_version": LIBS_OS_VERSION,
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "has_client_mods": False,
        "browser_user_agent": LIBS_USER_AGENT,
        "browser_version": "42.7.1",
        "os_sdk_version": "26200",
        "client_build_number": LIBS_CLIENT_BUILD_NUMBER,
        "native_build_number": LIBS_NATIVE_BUILD_NUMBER,
        "client_event_source": None,
        "client_app_state": "focused",
    }


def libs_build_super_props(launch_signature: str, heartbeat_session: str) -> str:
    try:
        req = urllib.request.Request(
            LIBS_PROPERTIES_URL,
            method="POST",
            data=b"{}",
            headers={"content-type": "application/json", "user-agent": LIBS_USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            props = json.loads(response.read().decode("utf-8"))["properties"]
    except Exception:
        props = libs_local_props()

    props["client_launch_id"] = str(uuid.uuid4())
    props["launch_signature"] = launch_signature
    props["client_heartbeat_session_id"] = heartbeat_session
    raw = json.dumps(props, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def libs_read_analytics_token(auth_token: str, super_props: str) -> str:
    req = urllib.request.Request(
        LIBS_ME_URL,
        headers={
            "authorization": auth_token,
            "user-agent": LIBS_USER_AGENT,
            "x-super-properties": super_props,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Token rejected by Discord ({exc.code})") from exc

    token = data.get("analytics_token")
    if not token:
        raise RuntimeError("No analytics_token returned in Discord response")
    return token


def libs_ensure_token(state: LibsState, super_props: str, state_path=None) -> None:
    if not state.is_stale:
        return
    state.analytics_token = libs_read_analytics_token(state.token, super_props)
    state.fetched_at = int(time.time())
    if state_path:
        state.libs_save(state_path)


@dataclass(frozen=True)
class LibsSession:
    heartbeat_session: str
    launch_signature: str
    super_props: str

    @classmethod
    def libs_new(cls) -> LibsSession:
        hb = str(uuid.uuid4())
        sig = str(uuid.uuid4())
        return cls(hb, sig, libs_build_super_props(sig, hb))

    new = libs_new


class LibsScienceClient:
    def __init__(self, state: LibsState, session: LibsSession) -> None:
        self.state = state
        self.session = session
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def libs_build_launch(self, game: LibsGame) -> dict:
        now = int(time.time() * 1000)
        props = {
            "client_track_timestamp": now,
            "client_heartbeat_session_id": self.session.heartbeat_session,
            "event_sequence_number": self._next_seq(),
            "game": game.name,
            "game_id": game.id,
            "verified": True,
            "elevated": False,
            "is_launcher": False,
            "game_platform": "desktop",
            "detection_method": "verified_game",
            "is_overlay_enabled": False,
            "is_overlay_game_enabled": True,
            "is_overlay_game_source": "OOP_DEFAULT_DATABASE",
            "fullscreen_type": "UNKNOWN",
            "hardware_display_count": 1,
            "overlay_method": "Disabled",
            "activity_status_enabled": True,
            "activity_status_shared_guilds": [],
            "current_user_status": "online",
            "game_detection_enabled": True,
            "executable_path": game.exe,
            "voice_channel_id": None,
            "voice_channel_type": None,
            "voice_channel_bitrate": None,
            "voice_channel_guild_id": None,
            "hidden_by_distributor": False,
            "game_metadata": None,
            "executable_fingerprint": self.state.fingerprint,
            "client_performance_cpu": None,
            "client_performance_memory": None,
            "cpu_core_count": None,
            "accessibility_features": 0,
            "rendered_locale": "en-US",
            "launch_signature": self.session.launch_signature,
            "client_rtc_state": None,
            "client_app_state": "focused",
            "client_send_timestamp": now,
        }
        if not self.state.fingerprint:
            del props["executable_fingerprint"]
        return {"type": "launch_game", "properties": props}

    build_launch = libs_build_launch

    def libs_build_heartbeat(
        self, game: LibsGame, duration_ms: int, session_id: str, initial: bool, final: bool, ts: int | None = None
    ) -> dict:
        ts = int(time.time() * 1000) if ts is None else ts
        return {
            "type": "running_game_heartbeat",
            "properties": {
                "client_track_timestamp": ts,
                "client_heartbeat_session_id": self.session.heartbeat_session,
                "event_sequence_number": self._next_seq(),
                "game_id": game.id,
                "game_name": game.name,
                "game_metadata": None,
                "game_executable": game.exe,
                "game_detection_enabled": True,
                "initial_heartbeat": initial,
                "final_heartbeat": final,
                "game_session_id": session_id,
                "duration_tracked_ms": duration_ms,
                "rtc_connection_id": None,
                "media_session_id": None,
                "launch_signature": self.session.launch_signature,
                "client_app_state": "focused",
                "client_send_timestamp": ts,
            },
        }

    build_heartbeat = libs_build_heartbeat

    def libs_build_session(self, game: LibsGame, duration_ms: int) -> list[dict]:
        sid = str(uuid.uuid4())
        now = int(time.time() * 1000)
        start = now - duration_ms
        if start < 0:
            start = now
        return [
            self.libs_build_heartbeat(game, 0, sid, initial=True, final=False, ts=start),
            self.libs_build_launch(game),
            self.libs_build_heartbeat(game, duration_ms, sid, initial=False, final=True, ts=now),
        ]

    build_session = libs_build_session

    def libs_post(self, events: Sequence[dict]) -> int:
        payload = {"token": self.state.analytics_token, "events": list(events)}
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "accept": "*/*",
            "accept-language": "en-US",
            "authorization": self.state.token,
            "content-type": "application/json",
            "origin": "https://discord.com",
            "referer": "https://discord.com/channels/@me",
            "user-agent": LIBS_USER_AGENT,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": "en-US",
            "x-discord-timezone": "UTC",
            "x-super-properties": self.session.super_props,
        }
        if self.state.cookie and self.state.cookie.strip():
            raw_cookie = self.state.cookie.strip()
            if not raw_cookie.startswith("cf_clearance=") and "=" not in raw_cookie:
                headers["cookie"] = f"cf_clearance={raw_cookie}"
            else:
                headers["cookie"] = raw_cookie

        request = urllib.request.Request(LIBS_SCIENCE_URL, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except Exception:
            return 0

    post = libs_post


def _libs_chunked(items: Sequence[LibsGame], size: int) -> Iterator[Sequence[LibsGame]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class LibsSpoofer:
    def __init__(self, client: LibsScienceClient) -> None:
        self.client = client

    def libs_run(
        self,
        games: Sequence[LibsGame],
        build_events: Callable[[LibsGame], list[dict]],
        on_batch: Callable[[int, int, int, int], None] | None = None,
    ) -> int:
        total = len(games)
        sent_ok = 0
        for request_no, chunk in enumerate(_libs_chunked(games, LIBS_BATCH_SIZE), start=1):
            events = []
            for game in chunk:
                events.extend(build_events(game))
            status = self.client.libs_post(events)

            if status == 204:
                sent_ok += len(chunk)
                if on_batch:
                    on_batch(request_no, sent_ok, total, 204)
            elif status in (401, 403):
                if on_batch:
                    on_batch(request_no, sent_ok, total, status)
                return sent_ok
            else:
                if on_batch:
                    on_batch(request_no, sent_ok, total, status)
            time.sleep(LIBS_BATCH_DELAY)
        return sent_ok

    run = libs_run


Session = LibsSession
ScienceClient = LibsScienceClient
Spoofer = LibsSpoofer
build_super_props = libs_build_super_props
read_analytics_token = libs_read_analytics_token
ensure_token = libs_ensure_token
