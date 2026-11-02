# ⸸ NOAME BADGES ⸸
### Discord Telemetry & Activity Spoofer — Universalist & Eternal Badge Tool
*Crafted by Yeti [ @yvlsoul ]*

---

> [!WARNING]
> This tool directly interacts with Discord's `/api/v9/science` telemetry endpoint for research and educational purposes. Use at your own discretion.

---

## ✦ Overview
**NOAME badges** is a zero-dependency Discord telemetry spoofer. It simulates game launches and playtime tracking across Discord's verified database to help trigger profile badges:

| Badge | Title | What it Spoofs |
| :---: | :---: | :---: |
| 🎮  Emulates `launch_game` events across 100+ detectable Windows game titles |
| ⌛  Dispatches `running_game_heartbeat` events accumulating 5,000+ hours of playtime |

*Note: Discord evaluates badges asynchronously. Once events are dispatched, badges typically populate on your profile within 24 to 48 hours.*

---

## ✦ Features
- ⚡ **Standalone Executable** — Run the compiled `.exe` directly with zero Python installation required.
- 🛡️ **Cross-Platform Fingerprint Engine** — Emulates Windows PE executable validation headers and XOR seeds to produce authentic telemetry payloads.
- 🍪 **Optional Cloudflare Bypass** — Direct mode enabled by default; attach `cf_clearance` whenever Cloudflare challenges appear.
- 💾 **State Caching** — Saves your credentials and total claimed stats locally in `noame_state.json`.

---

## ✦ Usage

### Running the Executable (Easiest)
1. Head over to the **Releases** tab on the right.
2. Download `NOAME_badges.exe`.
3. Double-click to run.
