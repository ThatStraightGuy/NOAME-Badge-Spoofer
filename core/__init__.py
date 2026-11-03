"""
NOAME badges — Discord Game & Streaming Badge Spoofer
Made by Yeti [ @despairlyf ]

For educational and research purposes only.
"""

from core.state import LibsState, State, libs_user_id_from_token, user_id_from_token
from core.games import LibsGame, Game, libs_load_games, load_games, libs_select_games, select_games
from core.fingerprint import libs_generate_fingerprint, generate_fingerprint
from core.heart import (
    LibsScienceClient,
    ScienceClient,
    LibsSession,
    Session,
    LibsSpoofer,
    Spoofer,
    libs_ensure_token,
    ensure_token,
    libs_build_super_props,
    libs_read_analytics_token,
)
from core.streamer import GatewayStreamEngine, validate_stream_target, STREAM_TIERS
import core.ui as ui

__all__ = [
    # Primary exports
    "LibsState",
    "LibsGame",
    "LibsScienceClient",
    "LibsSession",
    "LibsSpoofer",
    "GatewayStreamEngine",
    "validate_stream_target",
    "STREAM_TIERS",
    "libs_load_games",
    "libs_select_games",
    "libs_generate_fingerprint",
    "libs_ensure_token",
    "libs_build_super_props",
    "libs_read_analytics_token",
    "libs_user_id_from_token",
    # Aliases
    "State",
    "Game",
    "load_games",
    "select_games",
    "generate_fingerprint",
    "ScienceClient",
    "Session",
    "Spoofer",
    "ensure_token",
    "user_id_from_token",
    "ui",
]
