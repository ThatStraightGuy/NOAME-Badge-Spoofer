"""
lib's magic — Discord Game Badge Spoofer
Made by Yeti [ @despairlyf ]

For educational and research purposes only.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

LIBS_AUTH_MAX_AGE = 12 * 3600


def libs_user_id_from_token(token: str) -> str:
    try:
        first = token.split(".", 1)[0]
        pad = "=" * (-len(first) % 4)
        return base64.b64decode(first + pad).decode("utf-8")
    except Exception:
        return ""


@dataclass
class LibsState:
    token: str = ""
    cookie: str = ""
    fingerprint: str = ""
    analytics_token: str = ""
    fetched_at: int = 0
    used_games: list[str] = field(default_factory=list)
    total_games_claimed: int = 0
    total_hours_claimed: float = 0.0
    total_stream_hours_claimed: float = 0.0
    last_guild_id: str = ""
    last_channel_id: str = ""

    @classmethod
    def libs_load(cls, file_path: Path) -> LibsState:
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                state = cls()
                for key in cls().__dict__:
                    if key in data:
                        setattr(state, key, data[key])
                return state
            except Exception:
                pass
        return cls()

    load = libs_load

    def libs_save(self, file_path: Path) -> None:
        try:
            file_path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except Exception:
            pass

    save = libs_save

    @property
    def user_id(self) -> str:
        return libs_user_id_from_token(self.token)

    @property
    def is_stale(self) -> bool:
        return not self.analytics_token or (time.time() - self.fetched_at) > LIBS_AUTH_MAX_AGE

    @property
    def has_cookie(self) -> bool:
        return bool(self.cookie and self.cookie.strip())

    @property
    def has_token(self) -> bool:
        return bool(self.token.strip())


State = LibsState
AUTH_MAX_AGE = LIBS_AUTH_MAX_AGE
user_id_from_token = libs_user_id_from_token
