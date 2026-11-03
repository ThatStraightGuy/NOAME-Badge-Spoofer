"""
lib's magic — Discord Game Badge Spoofer
Made by Yeti [ @despairlyf ]

For educational and research purposes only.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

LIBS_ROOT       = Path(__file__).resolve().parent
LIBS_GAMES_FILE = LIBS_ROOT / "games.json"
LIBS_STATE_FILE = LIBS_ROOT / "noame_state.json"

ROOT        = LIBS_ROOT
GAMES_FILE  = LIBS_GAMES_FILE
STATE_FILE  = LIBS_STATE_FILE

from core import (
    LibsGame,
    LibsScienceClient,
    LibsSession,
    LibsSpoofer,
    LibsState,
    GatewayStreamEngine,
    validate_stream_target,
    STREAM_TIERS,
    libs_ensure_token,
    libs_generate_fingerprint,
    libs_load_games,
    libs_select_games,
    ui,
)


class LibsApp:
    def __init__(self) -> None:
        self.state   = LibsState.libs_load(LIBS_STATE_FILE)
        self.session: LibsSession | None = None
        self.client:  LibsScienceClient | None = None
        self.games:   list[LibsGame] = []

    # ── Internal helpers ───────────────────────────────────────────────────

    def _new_session(self) -> None:
        self.session = LibsSession.libs_new()
        self.client  = LibsScienceClient(self.state, self.session)

    # ── Start / Init ───────────────────────────────────────────────────────

    def start(self) -> None:
        ui.libs_clear_screen()
        print(ui.libs_render_header(
            games_count=len(self.games),
            claimed_games=self.state.total_games_claimed,
            claimed_hours=self.state.total_hours_claimed,
            user_id=self.state.user_id,
        ))

        # Token setup
        if not self.state.has_token:
            ui.libs_log_info("Discord account token is required.")
            token = ui.libs_prompt_input("Paste your Discord token:")
            if not token:
                ui.libs_log_error("Token is required to proceed. Exiting NOAME badges.")
                return
            self.state.token = token
            uid = self.state.user_id
            if uid:
                self.state.fingerprint = libs_generate_fingerprint(uid)
            self.state.libs_save(LIBS_STATE_FILE)
            ui.libs_log_success(f"Token saved  ✦  User ID: {uid}")
            time.sleep(0.5)
        else:
            ui.libs_log_success(f"Token loaded  ✦  User ID: {self.state.user_id}")
            time.sleep(0.3)

        # Optional Cloudflare cookie
        if not self.state.has_cookie:
            ui.libs_log_info("Cloudflare clearance cookie (cf_clearance) is optional.")
            cookie = ui.libs_prompt_input("Paste cf_clearance cookie  [Optional — Enter to skip]:")
            if cookie and cookie.strip():
                self.state.cookie = cookie.strip()
                self.state.libs_save(LIBS_STATE_FILE)
                ui.libs_log_success("cf_clearance cookie saved.")
            else:
                self.state.cookie = ""
                ui.libs_log_info("No cookie provided — direct mode enabled.")
            time.sleep(0.3)
        else:
            ui.libs_log_success("cf_clearance cookie loaded.")
            time.sleep(0.3)

        # Load game catalog
        ui.libs_log_info("Loading detectable games database...")
        self.games = libs_load_games(LIBS_GAMES_FILE)
        if not self.games:
            ui.libs_log_error("Failed to load games. Check connection or place games.json here.")
            return
        ui.libs_log_success(f"Loaded {len(self.games):,} detectable Windows games.")
        time.sleep(0.4)

        # Fingerprint
        if not self.state.fingerprint:
            uid = self.state.user_id
            if uid:
                self.state.fingerprint = libs_generate_fingerprint(uid)
                self.state.libs_save(LIBS_STATE_FILE)
                ui.libs_log_success(f"Executable fingerprint generated for {uid}.")
            else:
                ui.libs_log_warn("Could not parse User ID from token — fingerprint skipped.")
            time.sleep(0.4)
        else:
            ui.libs_log_success("Executable fingerprint loaded.")
            time.sleep(0.3)

        # Validate session
        ui.libs_log_info("Validating Discord session & analytics token...")
        self._new_session()
        try:
            libs_ensure_token(self.state, self.session.super_props, LIBS_STATE_FILE)
            ui.libs_log_success("Session validated  ✦  NOAME badges telemetry engine ready.")
        except Exception as exc:
            ui.libs_log_error(f"Authentication error: {exc}")
            return
        time.sleep(0.8)

        self._menu()

    # ── Menu actions ───────────────────────────────────────────────────────

    def _claim_games(self) -> None:
        ui.libs_log_divider("CLAIM PLAYTIME & GAMES")
        ui.libs_log_info(f"Available games: {len(self.games):,} titles.")

        raw_count = ui.libs_prompt_input(f"How many games to spoof?  [all / 1–{len(self.games)}]:")
        try:
            count = int(raw_count) if raw_count else len(self.games)
        except ValueError:
            ui.libs_log_error("Invalid game count.")
            time.sleep(1)
            return
        count = max(1, min(count, len(self.games)))

        raw_hours = ui.libs_prompt_input("Hours per game?  [Default: 1.0]:")
        try:
            hours = float(raw_hours) if raw_hours else 1.0
        except ValueError:
            ui.libs_log_error("Invalid hours value.")
            time.sleep(1)
            return
        hours = max(0.1, hours)

        selected, new_used = libs_select_games(self.games, self.state.used_games, count)
        if not selected:
            ui.libs_log_error("No games could be selected.")
            time.sleep(1)
            return

        self.state.used_games = new_used
        duration_ms  = int(hours * 3600 * 1000)
        total_hours  = len(selected) * hours

        from core.ui import fg_rgb, GOLD_BRIGHT, RESET, WHITE_BRIGHT
        print(
            f"   {fg_rgb(*GOLD_BRIGHT)}✦{RESET}  "
            f"{fg_rgb(*WHITE_BRIGHT)}{len(selected):,} games × {hours:g}h "
            f"= {total_hours:,.0f} hours total{RESET}"
        )

        ui.libs_log_divider("DISPATCHING BATCHES")

        batch_results: list[tuple[int, int, int]] = []  # (batch_no, sent_ok, status)

        def on_batch(batch_no: int, sent_ok: int, total: int, status: int) -> None:
            batch_results.append((batch_no, sent_ok, status))
            if status == 204:
                ui.libs_log_sent(f"Batch {batch_no:>3}", f"{sent_ok}/{total} games credited  [HTTP 204]")
            elif status in (401, 403):
                ui.libs_log_error(f"Batch {batch_no} rejected  [HTTP {status}] — check token.")
            else:
                ui.libs_log_warn(f"Batch {batch_no} returned  [HTTP {status}].")
            ui.libs_log_progress("Progress", sent_ok, total)

        spoofer  = LibsSpoofer(self.client)
        credited = spoofer.libs_run(
            selected,
            lambda g: self.client.libs_build_session(g, duration_ms),
            on_batch=on_batch,
        )

        ui.libs_log_divider("SUMMARY")
        claimed_h = credited * hours
        ui.libs_log_success(
            f"Done! Credited {credited:,}/{len(selected):,} games  ✦  {claimed_h:,.0f} hours total."
        )

        self.state.total_games_claimed += credited
        self.state.total_hours_claimed += claimed_h
        self.state.libs_save(LIBS_STATE_FILE)

        print()
        ui.libs_prompt_input("Press Enter to return to menu...")

    def _stream_afk(self) -> None:
        ui.libs_log_divider("AFK HEADLESS STREAMER (STREAMING BADGE)")
        ui.libs_log_info("✦ Streaming Badge Milestones (Go Live Broadcast):")
        for tier, name, req_hours in STREAM_TIERS:
            has_tier = self.state.total_stream_hours_claimed >= req_hours
            mark = "●" if has_tier else "○"
            ui.libs_log_info(f"   {mark} Tier {tier:2d} · {name:<12} {req_hours:>5,d}h")
        print()
        ui.libs_log_info("This runs a headless Go Live broadcast via Gateway & Voice WebSockets.")
        ui.libs_log_warn("Rule 1: An alt or friend MUST be in the VC — 0 viewer streams do NOT count!")
        ui.libs_log_warn("Rule 2: Discord Settings → Data & Privacy → 'Personalize my experience' must be ON!")
        print()

        guild_id = ui.libs_prompt_input(f"Server (Guild) ID [{self.state.last_guild_id or 'required'}]:")
        if not guild_id:
            guild_id = self.state.last_guild_id
        channel_id = ui.libs_prompt_input(f"Voice Channel ID [{self.state.last_channel_id or 'required'}]:")
        if not channel_id:
            channel_id = self.state.last_channel_id

        if not guild_id or not channel_id:
            ui.libs_log_error("Server ID and Voice Channel ID are required.")
            time.sleep(1.5)
            return

        ui.libs_log_info("Verifying server, voice channel, and streaming permissions...")
        valid, ch_name = validate_stream_target(
            token=self.state.token,
            super_props=self.session.super_props,
            guild_id=guild_id,
            channel_id=channel_id,
        )

        if not valid:
            ui.libs_log_error(f"Validation failed: {ch_name}")
            time.sleep(2)
            return

        self.state.last_guild_id = guild_id
        self.state.last_channel_id = channel_id
        self.state.libs_save(LIBS_STATE_FILE)
        ui.libs_log_success(f"Channel verified: #{ch_name} · Starting stream engine...")
        time.sleep(0.5)

        engine = GatewayStreamEngine(self.state, self.session.super_props)
        streamed_hours = engine.start_stream(guild_id, channel_id, LIBS_STATE_FILE)
        if streamed_hours > 0:
            self.state.total_stream_hours_claimed += streamed_hours
            self.state.libs_save(LIBS_STATE_FILE)

    def _refresh_auth(self) -> None:
        ui.libs_log_divider("REFRESH CREDENTIALS")
        choice = ui.libs_prompt_input("Update cf_clearance cookie?  [Optional]  [y/N]:").lower()
        if choice in ("y", "yes"):
            new_cookie = ui.libs_prompt_input("Paste new cf_clearance cookie  [Enter to clear]:")
            if new_cookie.strip():
                self.state.cookie = new_cookie.strip()
                ui.libs_log_success("cf_clearance cookie updated.")
            else:
                self.state.cookie = ""
                ui.libs_log_info("Cookie cleared — direct mode enabled.")
            self.state.libs_save(LIBS_STATE_FILE)

        tok_choice = ui.libs_prompt_input("Update account token?  [y/N]:").lower()
        if tok_choice in ("y", "yes"):
            new_token = ui.libs_prompt_input("Paste new Discord token:")
            if new_token:
                self.state.token = new_token
                uid = self.state.user_id
                if uid:
                    self.state.fingerprint = libs_generate_fingerprint(uid)
                ui.libs_log_success(f"Token updated  ✦  User ID: {uid}")

        ui.libs_log_info("Fetching fresh analytics token from Discord...")
        try:
            self.state.fetched_at = 0
            self._new_session()
            libs_ensure_token(self.state, self.session.super_props, LIBS_STATE_FILE)
            self.state.libs_save(LIBS_STATE_FILE)
            ui.libs_log_success("Session credentials refreshed successfully.")
        except Exception as exc:
            ui.libs_log_error(f"Failed to refresh session: {exc}")
        time.sleep(1.5)

    def _regen_fingerprint(self) -> None:
        ui.libs_log_divider("REGENERATE FINGERPRINT")
        uid = self.state.user_id
        if not uid:
            ui.libs_log_error("No valid User ID — please set token first.")
            time.sleep(1.5)
            return

        ui.libs_log_info(f"Generating fresh fingerprint for: {uid}...")
        self.state.fingerprint = libs_generate_fingerprint(uid)
        self.state.libs_save(LIBS_STATE_FILE)
        ui.libs_log_success(f"New fingerprint saved  ✦  {len(self.state.fingerprint)} chars.")
        time.sleep(1.5)

    def _view_status(self) -> None:
        ui.libs_log_divider("ACCOUNT STATUS & DIAGNOSTICS")
        uid = self.state.user_id or "Unknown"
        token_preview = (
            f"{self.state.token[:12]}...{self.state.token[-6:]}"
            if len(self.state.token) > 20
            else "Not set"
        )
        cookie_status = (
            f"Active  ({len(self.state.cookie)} chars)"
            if self.state.has_cookie
            else "None  [Direct Mode]"
        )
        fp_status = (
            f"Valid  ({len(self.state.fingerprint)} chars)"
            if self.state.fingerprint
            else "Not generated"
        )

        ui.libs_log_info(f"User ID         : {uid}")
        ui.libs_log_info(f"Token Preview   : {token_preview}")
        ui.libs_log_info(f"cf_clearance    : {cookie_status}")
        ui.libs_log_info(f"Fingerprint     : {fp_status}")
        ui.libs_log_info(
            f"Game Claims     : {self.state.total_games_claimed:,} games  ✦  "
            f"{self.state.total_hours_claimed:,.0f} hours"
        )
        ui.libs_log_info(
            f"Stream Claims   : {self.state.total_stream_hours_claimed:,.2f} hours (Go Live Broadcast)"
        )
        if self.state.last_channel_id:
            ui.libs_log_info(f"Last Stream Target: Guild {self.state.last_guild_id} · Channel {self.state.last_channel_id}")
        ui.libs_log_info(f"Games Catalog   : {len(self.games):,} titles  [{LIBS_GAMES_FILE.name}]")
        ui.libs_log_info(f"State File      : {LIBS_STATE_FILE}")
        print()
        ui.libs_prompt_input("Press Enter to return to menu...")

    # ── Main menu loop ─────────────────────────────────────────────────────

    def _menu(self) -> None:
        while True:
            ui.libs_clear_screen()
            print(ui.libs_render_header(
                games_count=len(self.games),
                claimed_games=self.state.total_games_claimed,
                claimed_hours=self.state.total_hours_claimed,
                stream_hours=self.state.total_stream_hours_claimed,
                user_id=self.state.user_id,
            ))

            choice = ui.libs_prompt_input("Select an option  [1–6]:")
            if choice in ("1", "01"):
                self._claim_games()
            elif choice in ("2", "02"):
                self._stream_afk()
            elif choice in ("3", "03"):
                self._refresh_auth()
            elif choice in ("4", "04"):
                self._regen_fingerprint()
            elif choice in ("5", "05"):
                self._view_status()
            elif choice in ("6", "06", "exit", "q"):
                ui.libs_log_info("Exiting NOAME badges. Happy badge hunting! ✦")
                break
            else:
                ui.libs_log_warn("Invalid option — choose 1 through 6.")
                time.sleep(1)


App = LibsApp


def main() -> None:
    try:
        LibsApp().start()
    except KeyboardInterrupt:
        print()
        ui.libs_log_warn("Interrupted by user. Exiting NOAME badges safely. ✦")
        sys.exit(0)


if __name__ == "__main__":
    main()
