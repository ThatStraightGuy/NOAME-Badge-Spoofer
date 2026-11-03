"""
NOAME badges — Headless Gateway Live Streamer Engine
Made by Yeti [ @despairlyf ]

Accumulates verified server-side streaming hours for the Discord Streaming Badge
via raw Gateway WebSocket + Voice WebSocket (v7) + Stream WebSocket (v7) + UDP keepalives.
"""

from __future__ import annotations

import base64
import json
import os
import select
import socket
import ssl
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Sequence

from core.state import LibsState
from core import ui

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

GATEWAY_URL = "gateway.discord.gg"
DISCORD_API = "https://discord.com/api/v9"
OPUS_SILENCE = b"\xf8\xff\xfe"

STREAM_TIERS = [
    (1, "Newcomer", 1),
    (2, "Fledgling", 5),
    (3, "Breakout", 20),
    (4, "Standout", 75),
    (5, "Trendsetter", 150),
    (6, "Headliner", 300),
    (7, "Star", 500),
    (8, "Sensation", 1000),
    (9, "Visionary", 2000),
    (10, "Phenomenon", 5000),
]

PERMISSION_ADMINISTRATOR = 1 << 3
PERMISSION_STREAM        = 1 << 9
PERMISSION_VIEW_CHANNEL  = 1 << 10
PERMISSION_CONNECT       = 1 << 20


class MiniWebSocket:
    """Minimal pure-Python SSL WebSocket client for Discord Gateway and Voice."""

    def __init__(self, host: str, port: int = 443, path: str = "/") -> None:
        host_clean = host.split("://")[-1].rstrip("/")
        if ":" in host_clean:
            h, p = host_clean.split(":", 1)
            self.host = h
            try:
                self.port = int(p)
            except ValueError:
                self.port = port
        else:
            self.host = host_clean
            self.port = port

        self.path = path
        self.sock: ssl.SSLSocket | None = None
        self.closed = True
        self._lock = threading.RLock()

    def connect(self) -> None:
        raw_sock = socket.create_connection((self.host, self.port), timeout=15)
        ctx = ssl.create_default_context()
        self.sock = ctx.wrap_socket(raw_sock, server_hostname=self.host)
        sec_key = base64.b64encode(os.urandom(16)).decode("ascii")

        host_hdr = self.host if self.port == 443 else f"{self.host}:{self.port}"
        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {host_hdr}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {sec_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Discord/1.0.9253\r\n\r\n"
        )
        self.sock.sendall(req.encode("utf-8"))

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket handshake failed")
            header_data += chunk

        first_line = header_data.split(b"\r\n")[0].decode("utf-8", "ignore")
        if "101" not in first_line:
            raise ConnectionError(f"Handshake rejected: {first_line}")
        self.closed = False

    def send(self, data: str) -> None:
        with self._lock:
            if self.closed or not self.sock:
                raise ConnectionError("Socket closed")
            try:
                payload = data.encode("utf-8")
                length = len(payload)
                mask_key = os.urandom(4)

                header = bytearray([0x81])
                if length <= 125:
                    header.append(0x80 | length)
                elif length <= 65535:
                    header.append(0x80 | 126)
                    header.extend(length.to_bytes(2, "big"))
                else:
                    header.append(0x80 | 127)
                    header.extend(length.to_bytes(8, "big"))

                header.extend(mask_key)
                masked = bytearray(payload[i] ^ mask_key[i % 4] for i in range(length))
                self.sock.sendall(header + masked)
            except Exception as e:
                self.close()
                raise ConnectionError(f"Socket write error: {e}") from e

    def _recv_exact(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed during read")
            buf.extend(chunk)
        return bytes(buf)

    def recv(self, timeout: float = 5.0) -> dict | None:
        if self.closed or not self.sock:
            return None
        try:
            r, _, _ = select.select([self.sock], [], [], timeout)
            if not r:
                return None
            head = self._recv_exact(2)
        except Exception:
            self.close()
            return None

        opcode = head[0] & 0x0F
        if opcode == 0x8:
            code = 0
            reason = ""
            try:
                c_len = head[1] & 0x7F
                if c_len >= 2:
                    p = self._recv_exact(c_len)
                    code = struct.unpack(">H", p[:2])[0]
                    reason = p[2:].decode("utf-8", "ignore")
            except Exception:
                pass
            self.close()
            return {"op": "close", "code": code, "reason": reason}
        if opcode == 0x9:
            try:
                with self._lock:
                    if self.sock and not self.closed:
                        pong = bytearray([0x8A, 0x80])
                        pong.extend(os.urandom(4))
                        self.sock.sendall(pong)
            except Exception:
                self.close()
            return {"op": "ping"}

        length = head[1] & 0x7F
        try:
            if length == 126:
                ext = self._recv_exact(2)
                length = int.from_bytes(ext, "big")
            elif length == 127:
                ext = self._recv_exact(8)
                length = int.from_bytes(ext, "big")

            payload = self._recv_exact(length)
            return json.loads(payload.decode("utf-8"))
        except Exception:
            self.close()
            return None

    def close(self) -> None:
        self.closed = True
        with self._lock:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None


class VoiceConnection:
    """Manages Voice WebSocket (v7) + UDP socket keepalive."""

    def __init__(
        self,
        endpoint: str,
        server_id: str,
        user_id: str,
        session_id: str,
        token: str,
        label: str = "voice",
        is_stream: bool = False,
    ) -> None:
        self.endpoint = endpoint
        self.server_id = server_id
        self.user_id = user_id
        self.session_id = session_id
        self.token = token
        self.label = label
        self.is_stream = is_stream

        self.ws: MiniWebSocket | None = None
        self.udp_sock: socket.socket | None = None
        self.running = False
        self.ssrc = 0
        self.voice_ip = ""
        self.voice_port = 0
        self.modes: list[str] = []
        self.heartbeat_interval = 20.0
        self.secret_key: list[int] | None = None
        self.encryption_mode = "aead_aes256_gcm_rtpsize"
        self.external_ip = ""
        self.external_port = 0
        self.nonce_counter = 0

        self._hb_thread: threading.Thread | None = None
        self._audio_thread: threading.Thread | None = None

    def connect(self) -> bool:
        ep = self.endpoint.split(":")[0].rstrip("/")
        ws_url = f"wss://{ep}/?v=7"
        self.ws = MiniWebSocket(ep, port=443, path="/?v=7")

        try:
            self.ws.connect()
        except Exception as exc:
            ui.libs_log_warn(f"[{self.label}] Voice WS connect error: {exc}")
            return False

        hello = self.ws.recv(timeout=10)
        if not hello or hello.get("op") != 8:
            ui.libs_log_warn(f"[{self.label}] Expected op 8 (Hello), got {hello}")
            return False

        self.heartbeat_interval = hello.get("d", {}).get("heartbeat_interval", 20000) / 1000.0

        identify_d: dict[str, Any] = {
            "server_id": self.server_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "token": self.token,
            "video": True,
            "streams": [{"type": "screen", "rid": "100", "quality": 100}],
        }
        self.ws.send(json.dumps({"op": 0, "d": identify_d}))

        ready = None
        for _ in range(30):
            msg = self.ws.recv(timeout=2)
            if msg and msg.get("op") == 2:
                ready = msg
                break
            if msg and msg.get("op") == 8:
                continue

        if not ready:
            ui.libs_log_warn(f"[{self.label}] Voice Ready (op 2) timeout")
            return False

        rd = ready.get("d", {})
        self.ssrc = rd.get("ssrc", 0)
        self.voice_ip = rd.get("ip", "")
        self.voice_port = rd.get("port", 0)
        self.modes = rd.get("modes", [])

        if not self._udp_discovery():
            ui.libs_log_warn(f"[{self.label}] UDP IP discovery failed")
            return False

        chosen_mode = None
        for m in ["aead_aes256_gcm_rtpsize", "aead_aes256_gcm", "xsalsa20_poly1305"]:
            if m in self.modes:
                chosen_mode = m
                break
        if not chosen_mode and self.modes:
            chosen_mode = self.modes[0]
        self.encryption_mode = chosen_mode or "aead_aes256_gcm_rtpsize"

        self.ws.send(json.dumps({
            "op": 1,
            "d": {
                "protocol": "udp",
                "data": {
                    "address": self.external_ip,
                    "port": self.external_port,
                    "mode": self.encryption_mode,
                },
            },
        }))

        desc = None
        for _ in range(30):
            msg = self.ws.recv(timeout=2)
            if msg and msg.get("op") == 4:
                desc = msg
                break

        if desc:
            self.secret_key = desc.get("d", {}).get("secret_key")

        self.running = True
        return True

    def _send_heartbeat(self) -> None:
        if self.ws and not self.ws.closed:
            try:
                nonce = int(time.time() * 1000)
                self.ws.send(json.dumps({"op": 3, "d": nonce}))
            except Exception:
                pass

    def _udp_discovery(self) -> bool:
        try:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.settimeout(5)

            packet = bytearray(74)
            struct.pack_into(">HHI", packet, 0, 0x0001, 70, self.ssrc)
            self.udp_sock.sendto(bytes(packet), (self.voice_ip, self.voice_port))

            data, _ = self.udp_sock.recvfrom(256)
            if len(data) < 74:
                return False

            ip_start = 8
            ip_end = data.index(0, ip_start)
            self.external_ip = data[ip_start:ip_end].decode("utf-8")
            self.external_port = struct.unpack_from(">H", data, 72)[0]
            return bool(self.external_ip)
        except Exception:
            if self.udp_sock:
                try:
                    self.udp_sock.close()
                except Exception:
                    pass
                self.udp_sock = None
            return False

    def start_heartbeat(self) -> None:
        def _loop():
            while self.running and self.ws and not self.ws.closed:
                self._send_heartbeat()
                try:
                    msg = self.ws.recv(timeout=0.5)
                    if msg and msg.get("op") == 3:
                        self._send_heartbeat()
                except Exception:
                    pass
                time.sleep(max(1.0, self.heartbeat_interval - 0.5))

        self._hb_thread = threading.Thread(target=_loop, daemon=True)
        self._hb_thread.start()

    def send_speaking(self, speaking: bool = True) -> None:
        if self.ws and not self.ws.closed:
            try:
                self.ws.send(json.dumps({
                    "op": 5,
                    "d": {
                        "speaking": 1 if speaking else 0,
                        "delay": 0,
                        "ssrc": self.ssrc,
                    },
                }))
            except Exception:
                pass

    def start_silence_pump(self) -> None:
        if not self.udp_sock or not self.secret_key:
            return

        def _pump():
            seq = 0
            ts = 0
            while self.running:
                try:
                    if HAS_CRYPTO and "aes256_gcm" in self.encryption_mode:
                        self._send_encrypted_silence_gcm(seq, ts)
                    else:
                        keepalive = struct.pack(">I", seq) + b"\xc9"
                        try:
                            self.udp_sock.sendto(keepalive, (self.voice_ip, self.voice_port))
                        except Exception:
                            pass
                    seq = (seq + 1) & 0xFFFF
                    ts = (ts + 960) & 0xFFFFFFFF
                    time.sleep(1.0)
                except Exception:
                    break

        self._audio_thread = threading.Thread(target=_pump, daemon=True)
        self._audio_thread.start()

    def _send_encrypted_silence_gcm(self, seq: int, ts: int) -> None:
        if not self.udp_sock or not self.secret_key:
            return
        try:
            rtp_header = struct.pack(
                ">BBHII",
                0x80,
                0x78,
                seq & 0xFFFF,
                ts & 0xFFFFFFFF,
                self.ssrc,
            )
            self.nonce_counter += 1
            nonce = struct.pack(">I", self.nonce_counter) + b"\x00" * 8

            cipher = AESGCM(bytes(self.secret_key[:32]))
            encrypted = cipher.encrypt(nonce, OPUS_SILENCE, rtp_header)
            packet = rtp_header + encrypted + struct.pack(">I", self.nonce_counter)
            self.udp_sock.sendto(packet, (self.voice_ip, self.voice_port))
        except Exception:
            pass

    def close(self) -> None:
        self.running = False
        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass
        if self.ws:
            self.ws.close()


def validate_stream_target(token: str, super_props: str, guild_id: str, channel_id: str) -> tuple[bool, str]:
    headers = {
        "authorization": token,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Discord/1.0.9253",
    }
    if super_props:
        headers["x-super-properties"] = super_props

    try:
        req = urllib.request.Request(f"{DISCORD_API}/channels/{channel_id}", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            ch_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False, "Channel not found (invalid ID or bot lacks access)"
        if exc.code == 403:
            return False, "Access denied (account cannot view this channel)"
        return False, f"HTTP Error {exc.code}"
    except Exception as exc:
        return False, str(exc)

    ch_type = ch_data.get("type")
    if ch_type not in (2, 13):
        return False, f"Channel is not a Voice or Stage channel (type: {ch_type})"

    raw_perms = ch_data.get("permissions")
    if raw_perms is not None:
        try:
            perms = int(raw_perms)
            is_admin = bool(perms & PERMISSION_ADMINISTRATOR)
            can_view = is_admin or bool(perms & PERMISSION_VIEW_CHANNEL)
            can_connect = is_admin or bool(perms & PERMISSION_CONNECT)
            can_stream = is_admin or bool(perms & PERMISSION_STREAM)

            if not can_view:
                return False, "Missing VIEW_CHANNEL permission"
            if not can_connect:
                return False, "Missing CONNECT permission"
            if not can_stream:
                return False, "Missing STREAM (Go Live) permission"
        except Exception:
            pass

    return True, ch_data.get("name", "voice")


class GatewayStreamEngine:
    """Headless Gateway Live Streamer Engine."""

    def __init__(self, state: LibsState, super_props: str) -> None:
        self.state = state
        self.super_props = super_props
        self.ws: MiniWebSocket | None = None
        self.voice_conn: VoiceConnection | None = None
        self.stream_conn: VoiceConnection | None = None
        self.running = False
        self.heartbeat_interval = 41.25
        self.sequence: int | None = None
        self.start_time = 0.0

        self.gateway_session_id = ""
        self.user_id = state.user_id
        self.stream_key = ""

        self.voice_session_id = ""
        self.voice_token = ""
        self.voice_endpoint = ""
        self.voice_connected = False

        self.stream_token = ""
        self.stream_endpoint = ""
        self.stream_connected = False
        self.stream_ever_active = False
        self._user_left_vc = False

        self._status_thread: threading.Thread | None = None

    def start_stream(self, guild_id: str, channel_id: str, state_path=None) -> float:
        ui.libs_log_divider("STARTING HEADLESS GO LIVE STREAM")
        ui.libs_log_info("Connecting to Discord Gateway (gateway.discord.gg)...")

        self.ws = MiniWebSocket(GATEWAY_URL, path="/?v=9&encoding=json")
        try:
            self.ws.connect()
        except Exception as exc:
            ui.libs_log_error(f"Gateway connection failed: {exc}")
            return 0.0

        ui.libs_log_success("Gateway connection established.")
        self.running = True
        self.start_time = time.time()
        self.stream_ever_active = False
        self._user_left_vc = False

        event_thread = threading.Thread(
            target=self._event_loop,
            args=(guild_id, channel_id),
            daemon=True,
        )
        event_thread.start()

        self._status_thread = threading.Thread(
            target=self._status_display,
            daemon=True,
        )
        self._status_thread.start()

        print()
        ui.libs_log_info("✦ Live AFK Stream running in background! Press Enter to stop streaming.")
        ui.libs_log_divider()

        try:
            import msvcrt
            while self.running:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b"\r", b"\n", b"\x03"):
                        break
                time.sleep(0.1)
        except Exception:
            while self.running:
                time.sleep(0.5)

        return self._cleanup(guild_id, state_path)

    def _status_display(self) -> None:
        while self.running:
            time.sleep(60)
            if not self.running:
                break
            elapsed = time.time() - self.start_time
            hours = elapsed / 3600.0
            mins = int(elapsed / 60)
            if self.stream_connected:
                status = "🔴 LIVE (Streaming)"
            elif self.voice_connected:
                status = "⏳ Connecting Go Live"
            else:
                status = "⏳ Reconnecting"
            ui.libs_log_sent("Stream Status", f"{status} · {mins}m ({hours:.2f}h) elapsed")

    def _event_loop(self, guild_id: str, channel_id: str) -> None:
        last_hb = time.time()

        while self.running:
            try:
                if not self.ws or self.ws.closed:
                    break

                now = time.time()
                if now - last_hb > self.heartbeat_interval:
                    if self.ws and not self.ws.closed:
                        try:
                            self.ws.send(json.dumps({"op": 1, "d": self.sequence}))
                            last_hb = now
                        except Exception:
                            break

                msg = self.ws.recv(timeout=1.0)
                if not msg:
                    continue

                if isinstance(msg, dict) and msg.get("op") == "close":
                    code = msg.get("code")
                    reason = msg.get("reason", "")
                    ui.libs_log_warn(f"Gateway closed ({code}: {reason})")
                    self.running = False
                    break

                op = msg.get("op")
                seq = msg.get("s")
                t = msg.get("t")
                d = msg.get("d") or {}

                if seq is not None:
                    self.sequence = seq

                if op == 10:
                    self.heartbeat_interval = d.get("heartbeat_interval", 41250) / 1000.0
                    last_hb = time.time()
                    self.ws.send(json.dumps({"op": 1, "d": self.sequence}))

                    # Decode properties or use defaults
                    try:
                        props_raw = json.loads(base64.b64decode(self.super_props).decode("utf-8"))
                    except Exception:
                        props_raw = {
                            "os": "Windows",
                            "browser": "Discord Client",
                            "release_channel": "stable",
                            "client_version": "1.0.9253",
                        }

                    self.ws.send(json.dumps({
                        "op": 2,
                        "d": {
                            "token": self.state.token,
                            "capabilities": 16381,
                            "properties": props_raw,
                            "presence": {
                                "status": "online",
                                "since": 0,
                                "activities": [],
                                "afk": False,
                            },
                        },
                    }))

                elif op == 1:
                    self.ws.send(json.dumps({"op": 1, "d": self.sequence}))
                    last_hb = now

                elif op == 0:
                    self._handle_dispatch(t, d, guild_id, channel_id)

                elif op == 7:
                    ui.libs_log_warn("Discord requested Gateway reconnect (op 7)")
                    break

                elif op == 9:
                    ui.libs_log_warn("Gateway session invalidated (op 9)")
                    break

            except Exception as exc:
                if not self.running:
                    break
                ui.libs_log_warn(f"Gateway loop drop: {exc}")
                break

    def _handle_dispatch(self, event_type: str, d: dict, guild_id: str, channel_id: str) -> None:
        if event_type == "READY":
            self.gateway_session_id = d.get("session_id", "")
            user_data = d.get("user", {})
            username = user_data.get("username", "?")
            self.user_id = str(user_data.get("id", self.user_id))
            ui.libs_log_success(f"Gateway Authenticated as @{username}")

            self.ws.send(json.dumps({
                "op": 4,
                "d": {
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "self_mute": False,
                    "self_deaf": False,
                    "self_video": False,
                },
            }))
            ui.libs_log_sent("Voice", f"Joining Voice Channel {channel_id}")

        elif event_type == "VOICE_STATE_UPDATE":
            if str(d.get("user_id")) == str(self.user_id):
                active_channel = d.get("channel_id")
                new_session = d.get("session_id", "")
                if new_session:
                    self.voice_session_id = new_session

                if (self.voice_connected or self.stream_connected or self.stream_ever_active):
                    if active_channel is None:
                        ui.libs_log_warn("User manually left the voice channel in Discord app.")
                        self._user_left_vc = True
                        self.running = False
                        return

        elif event_type == "VOICE_SERVER_UPDATE":
            token = d.get("token", "")
            endpoint = d.get("endpoint") or ""
            v_guild = d.get("guild_id", guild_id)

            if not endpoint or not token:
                return

            self.voice_token = token
            self.voice_endpoint = endpoint
            ui.libs_log_info(f"Voice Server Target: {endpoint}")

            session_id = self.voice_session_id or self.gateway_session_id
            self.voice_conn = VoiceConnection(
                endpoint=self.voice_endpoint,
                server_id=v_guild,
                user_id=self.user_id,
                session_id=session_id,
                token=self.voice_token,
                label="Voice",
                is_stream=False,
            )

            ui.libs_log_info("Performing Voice WebSocket Handshake (v7)...")
            if self.voice_conn.connect():
                self.voice_conn.start_heartbeat()
                self.voice_conn.send_speaking(False)
                self.voice_conn.start_silence_pump()
                self.voice_connected = True
                ui.libs_log_success("Voice connection established with UDP silence keepalive.")

                time.sleep(0.5)
                ui.libs_log_info("Requesting Go Live Stream broadcast (Opcode 18)...")
                try:
                    self.ws.send(json.dumps({
                        "op": 18,
                        "d": {
                            "type": "guild",
                            "guild_id": guild_id,
                            "channel_id": channel_id,
                            "preferred_region": None,
                        },
                    }))
                except Exception as exc:
                    ui.libs_log_warn(f"Stream Create send error: {exc}")

        elif event_type == "STREAM_CREATE":
            self.stream_key = d.get("stream_key", "")
            ui.libs_log_success(f"Go Live Created! Stream Key: {self.stream_key}")
            self.stream_connected = True
            self.stream_ever_active = True

            if self.voice_conn and self.voice_conn.ws and not self.voice_conn.ws.closed:
                try:
                    video_ssrc = self.voice_conn.ssrc + 1
                    rtx_ssrc = self.voice_conn.ssrc + 2
                    self.voice_conn.ws.send(json.dumps({
                        "op": 12,
                        "d": {
                            "audio_ssrc": self.voice_conn.ssrc,
                            "video_ssrc": video_ssrc,
                            "rtx_ssrc": rtx_ssrc,
                            "streams": [
                                {
                                    "type": "video",
                                    "rid": "100",
                                    "ssrc": video_ssrc,
                                    "active": True,
                                    "quality": 100,
                                    "rtx_ssrc": rtx_ssrc,
                                    "max_bitrate": 8000000,
                                    "max_framerate": 60,
                                    "max_resolution": {"type": "fixed", "width": 1920, "height": 1080},
                                }
                            ],
                        },
                    }))
                except Exception:
                    pass

        elif event_type == "STREAM_SERVER_UPDATE":
            token = d.get("token", "")
            endpoint = d.get("endpoint") or ""
            stream_key = d.get("stream_key", self.stream_key)

            if not endpoint or not token:
                return

            self.stream_token = token
            self.stream_endpoint = endpoint
            ui.libs_log_info(f"Stream Media Server Target: {endpoint}")

            self.stream_conn = VoiceConnection(
                endpoint=self.stream_endpoint,
                server_id=stream_key,
                user_id=self.user_id,
                session_id=self.voice_session_id or self.gateway_session_id,
                token=self.stream_token,
                label="Stream",
                is_stream=True,
            )

            if self.stream_conn.connect():
                self.stream_conn.start_heartbeat()
                self.stream_conn.send_speaking(True)
                self.stream_conn.start_silence_pump()
                self.stream_connected = True
                ui.libs_log_success("✦ Dedicated Stream WebSocket & UDP Pipeline Active! (0% CPU / 0% GPU)")

    def _cleanup(self, guild_id: str, state_path=None) -> float:
        self.running = False

        if self.ws and not self.ws.closed and self.stream_key:
            try:
                self.ws.send(json.dumps({"op": 19, "d": {"stream_key": self.stream_key}}))
            except Exception:
                pass

        if self.ws and not self.ws.closed and not self._user_left_vc:
            try:
                self.ws.send(json.dumps({
                    "op": 4,
                    "d": {
                        "guild_id": guild_id,
                        "channel_id": None,
                        "self_mute": False,
                        "self_deaf": False,
                        "self_video": False,
                    },
                }))
            except Exception:
                pass

        if self.stream_conn:
            self.stream_conn.close()
        if self.voice_conn:
            self.voice_conn.close()
        if self.ws:
            time.sleep(0.3)
            self.ws.close()

        elapsed = time.time() - self.start_time if self.start_time > 0 else 0.0
        hours = elapsed / 3600.0

        if (self.stream_connected or self.stream_ever_active) and elapsed >= 10:
            ui.libs_log_divider("STREAM SUMMARY")
            ui.libs_log_success(f"Stream Ended! Streamed for {elapsed:.0f}s ({hours:.2f} hours).")
            ui.libs_log_info("✦ Discord backend syncs streaming badge tiers within 24 to 48 hours.")
        else:
            ui.libs_log_info("Stream session ended.")

        print()
        ui.libs_prompt_input("Press Enter to return to main menu...")
        return hours
