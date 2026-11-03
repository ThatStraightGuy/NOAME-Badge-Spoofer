# ༒ NOAME BADGES ༒
<img width="35" height="16" alt="image" src="https://github.com/user-attachments/assets/7d141ee2-53d9-42d1-adeb-37efb4de84d8" />

### Discord Telemetry & Activity Spoofer — Universalist, Eternal & Streaming Badge Tool
*Crafted by Yeti [ `@despairlyf` ]*

---

> [!WARNING]
> This tool directly interacts with Discord's `/api/v9/science` telemetry endpoint and Voice Gateway protocol for research and educational purposes. Use at your own discretion.

---

## ✦ Overview
**NOAME badges** is a zero-dependency Discord telemetry and live activity spoofer. It simulates game launches, playtime tracking, and headless Go Live broadcasting to trigger tiered profile badges:

| Badge | Title | What it Spoofs |
| :---: | :---: | :---: |
| 🎮 | **The Universalist** | Emulates `launch_game` events across 100+ detectable Windows game titles |
| ⌛ | **The Eternal** | Dispatches `running_game_heartbeat` events accumulating 5,000+ hours of playtime |
| 📡 | **The Phenomenon** | Headless Voice Gateway + Go Live stream engine accumulating 5,000+ broadcast hours |

*Note: Discord evaluates badges asynchronously. Once events are dispatched or streamed, badges typically populate on your profile within 24 to 48 hours.*

<div align="center">
  <img width="254" height="164" alt="Universalist Badge" src="https://github.com/user-attachments/assets/33033262-a326-44d0-956a-acf08fa0e63d" />
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img width="262" height="172" alt="Eternal Badge" src="https://github.com/user-attachments/assets/75a47b89-60f3-4940-8e0f-b003da57705c" />
</div>
  <img width="1024" height="1024" alt="streaming_badge_vector" src="https://github.com/user-attachments/assets/56852d3f-0148-4f38-938a-7c9297f823e8" />

---

## ✦ Features
- ⚡ **Standalone Executable** — Run the compiled `.exe` directly with zero Python installation required.
- 📡 **Headless AFK Go Live Streamer** — Accumulate real streaming hours 24/7 with **0% GPU and 0% CPU** usage via silent Opus UDP keepalives.
- 🛡️ **Cross-Platform Fingerprint Engine** — Emulates Windows PE executable validation headers and XOR seeds to produce authentic telemetry payloads.
- 🍪 **Optional Cloudflare Bypass** — Direct mode enabled by default; attach `cf_clearance` whenever Cloudflare challenges appear.
- 🎨 **Gothic / YVL Cyber Terminal UI** — Dual-mode responsive ANSI banners, dark gradients, live telemetry feeds, and real-time progress bars.
- 💾 **State Caching** — Saves your credentials and total claimed stats locally in `noame_state.json`.

---

## ✦ How to Obtain Credentials

Before launching the tool, grab your Discord authorization token and (optional) Cloudflare clearance cookie.

### Step 1: Discord Account Token
1. Open Discord in your web browser (Chrome, Edge, Firefox, Brave) and go to **[https://discord.com/channels/@me](https://discord.com/channels/@me)**.
2. Press `Ctrl + Shift + I` (or `Cmd + Option + I` on macOS) to open **Developer Tools**.
3. Switch to the **Network** tab at the top.
4. In the filter box, type `science` or `messages?limit=10`.
   *(If the table is empty, click on any DM or channel to generate network traffic).*
5. Click on any outgoing request and open the **Headers** tab on the right.
6. Scroll down to **Request Headers** and locate **`authorization`**.
7. Copy the value of `authorization` — this is your Discord token.

---

### Step 2: Cloudflare Clearance Cookie (`cf_clearance`)
> [!NOTE]
> `cf_clearance` is **optional**. On normal home connections, you can press **Enter** to skip it. Only provide this if you are running on a datacenter IP/VPN that receives Cloudflare 403 blocks.

Choose either method below to copy your `cf_clearance` cookie:

#### Method 1: Via Application Tab (Recommended & Easiest)
1. In Developer Tools (`Ctrl + Shift + I`), click on the **Application** tab (or **Storage** tab in Firefox).
2. In the left sidebar, expand **Cookies** → click on **`https://discord.com`**.
3. In the cookie table, locate the row named **`cf_clearance`**.
4. Double-click the text under the **Value** column and copy it.

#### Method 2: Via Network Tab
1. In Developer Tools → **Network** tab, click on any filtered `science` request.
2. Under **Request Headers**, locate the **`cookie`** entry.
3. Find `cf_clearance=...;` within the header string.
4. Copy the value starting directly after `cf_clearance=` and ending right before the trailing `;` (or paste the entire cookie string; the tool parses it automatically).

---

## ✦ Usage

### Running the Executable (Easiest)
1. Head over to the **[Releases](../../releases)** tab on the right.
2. Download **`NOAME_badges.exe`**.
3. Double-click to run!

### Running from Source
```bash
# Clone the repository
git clone https://github.com/ThatStraightGuy/NOAME-Badge-Spoofer.git
cd NOAME-Badge-Spoofer

# Run directly (Python 3.10+)
python main.py
```

---

## ✦ Interactive Options

- **`<01> Claim Playtime & Games`** — Prompts for the number of games to spoof (e.g. `100`) and hours per game (e.g. `50` hrs each = `5,000` total hours). Dispatches events in batches with live telemetry logs.
- **`<02> AFK Headless Streamer`** — Enter your Server ID and Voice Channel ID to initiate a 24/7 headless Go Live broadcast for the Streaming Badge. *(Requires an alt in the voice channel to count viewer hours).*
- **`<03> Refresh Auth Token`** — Interactively update your account token or `cf_clearance` cookie and fetch fresh analytics tokens.
- **`<04> Regenerate Fingerprint`** — Computes a fresh cross-platform 146-byte executable hash tied to your Discord User ID.
- **`<05> View Account Status`** — Inspect active User ID, token preview, connection mode, fingerprint status, and total claimed game/stream metrics.
- **`<06> Exit NOAME badges`** — Safely persists current session progress to `noame_state.json` and closes the tool.

---

### ✦ Credits & Acknowledgments
- **Developer:** Yeti [ `@despairlyf` ]
- **Core Architecture:** Revere Group & dolfies (Reverse engineered client executable telemetry validation)
- **Streaming Handshake:** sonujana26 (Headless Gateway + Voice + Go Live stream engine)
