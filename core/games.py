"""
lib's magic — Discord Game Badge Spoofer
Made by Yeti [ @despairlyf ]

For educational and research purposes only.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

LIBS_GAMES_CDN_URL = "https://cdn.discordapp.com/detectables/games.json"
GAMES_CDN_URL = LIBS_GAMES_CDN_URL


@dataclass(frozen=True)
class LibsGame:
    id: str
    name: str
    exe: str


Game = LibsGame


def libs_win_exe(game: dict) -> str:
    for entry in game.get("executables", []):
        if entry.get("os") == "win32" and entry.get("name"):
            return entry["name"]
    return "game.exe"


def libs_download_games(file_path: Path) -> str:
    req = urllib.request.Request(LIBS_GAMES_CDN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8")
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(raw, encoding="utf-8")
    except OSError:
        pass
    return raw


def libs_parse_games(raw: str) -> list[LibsGame]:
    data = json.loads(raw)
    games: list[LibsGame] = []
    seen: set[str] = set()
    for entry in data:
        gid = str(entry.get("id", ""))
        if not gid.isdigit() or gid in seen:
            continue
        if not any(e.get("os") == "win32" and e.get("name") for e in entry.get("executables", [])):
            continue
        seen.add(gid)
        games.append(LibsGame(gid, entry.get("name", "Unknown"), libs_win_exe(entry)))
    return games


def libs_load_games(file_path: Path) -> list[LibsGame]:
    raw = ""
    if file_path.exists():
        try:
            raw = file_path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    if raw:
        try:
            games = libs_parse_games(raw)
            if games:
                return games
        except (json.JSONDecodeError, ValueError):
            pass

    try:
        return libs_parse_games(libs_download_games(file_path))
    except Exception:
        return []


def libs_select_games(
    all_games: list[LibsGame], used_ids: list[str], count: int
) -> tuple[list[LibsGame], list[str]]:
    available_ids = {g.id for g in all_games}
    unused_ids = [g.id for g in all_games if g.id not in used_ids]
    valid_used_ids = [gid for gid in used_ids if gid in available_ids]

    if len(unused_ids) >= count:
        selected_ids = unused_ids[:count]
    else:
        selected_ids = list(unused_ids)
        if valid_used_ids:
            remaining = count - len(selected_ids)
            rotated = valid_used_ids[remaining:] + valid_used_ids[:remaining]
            selected_ids.extend(rotated[:remaining])

    id_map = {g.id: g for g in all_games}
    selected = [id_map[gid] for gid in selected_ids if gid in id_map]
    new_used = list(dict.fromkeys(used_ids + selected_ids))
    return selected, new_used


load_games = libs_load_games
select_games = libs_select_games
