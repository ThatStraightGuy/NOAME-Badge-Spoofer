"""
NOAME badges — Discord Game Badge Spoofer
Made by Yeti [ @despairlyf ]

For educational and research purposes only.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time


def _enable_windows_vt() -> None:
    if os.name == "nt":
        try:
            import ctypes
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetStdHandle(-11)
                mode = ctypes.c_ulong()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    mode.value |= 0x0004
                    kernel32.SetConsoleMode(handle, mode)
        except Exception:
            pass


_enable_windows_vt()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── ANSI primitives ─────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
ITALIC = "\033[3m"

# ── Color palette — Gothic · Y2K · YVL ──────────────────────────────────────
BLOOD_RED    = (185,  28,  28)   # deep crimson
CRIMSON      = (220,  38,  38)   # bright vampire red
DEEP_VIOLET  = ( 76,  29, 149)   # dark gothic purple
AMETHYST     = (147,  51, 234)   # vivid purple
MUTED_LILAC  = (192, 132, 252)   # soft chrome lavender
SILVER       = (203, 213, 225)   # metallic silver
CHROME       = (241, 245, 249)   # bright chrome white
GHOST_WHITE  = (248, 250, 252)   # near white
ROSE_DARK    = (159,  18,  57)   # dark rose
DIM_SILVER   = (148, 163, 184)   # muted metallic
VOID_GRAY    = (100, 116, 139)   # slate gray
DARK_BORDER  = ( 51,  65,  85)   # dark gothic rule
GREEN_MINT   = ( 52, 211, 153)   # status ok
RED_SOFT     = (248, 113, 113)   # soft alert
RED_BRIGHT   = (239,  68,  68)   # bright error
CYAN_ACCENT  = (  6, 182, 212)   # cyan pulse

# Aliases for backwards compatibility
PURPLE_BRIGHT = AMETHYST
PURPLE_MID    = MUTED_LILAC
MAGENTA_NEON  = ROSE_DARK
MAGENTA_SOFT  = MUTED_LILAC
GOLD_BRIGHT   = CHROME
GOLD_MID      = SILVER
GREEN_EMERALD = GREEN_MINT
WHITE_BRIGHT  = GHOST_WHITE
GRAY_TEXT     = DIM_SILVER
GRAY_MUTED    = VOID_GRAY
GRAY_BORDER   = DARK_BORDER


def fg_rgb(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def bg_rgb(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


def strip_ansi(text: str) -> str:
    return re.sub(r"\033\[[0-9;]*[a-zA-Z]", "", text)


def libs_get_term_width(default: int = 86) -> int:
    try:
        w = shutil.get_terminal_size((default, 24)).columns
        return max(w, 55)
    except Exception:
        return default

get_term_width = libs_get_term_width


def libs_clear_screen() -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H\033[3J")
        sys.stdout.flush()

clear_screen = libs_clear_screen


def center(text: str, width: int | None = None) -> str:
    if width is None:
        width = libs_get_term_width()
    plain_len = len(strip_ansi(text))
    if plain_len >= width:
        return text
    pad = (width - plain_len) // 2
    return " " * pad + text


def center_block(lines: list[str], width: int | None = None) -> list[str]:
    if width is None:
        width = libs_get_term_width()
    clean_lines = [strip_ansi(l) for l in lines]
    non_empty = [l for l in clean_lines if l.strip()]
    if not non_empty:
        return lines
    max_len = max(len(l) for l in non_empty)
    pad = max(0, (width - max_len) // 2)
    return [(" " * pad + line) if line.strip() else "" for line in lines]


def lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def multi_gradient_color(colors: list[tuple[int, int, int]], t: float) -> tuple[int, int, int]:
    if not colors:
        return (255, 255, 255)
    if len(colors) == 1 or t <= 0.0:
        return colors[0]
    if t >= 1.0:
        return colors[-1]
    seg_len = 1.0 / (len(colors) - 1)
    seg_idx = min(int(t / seg_len), len(colors) - 2)
    local_t = (t - (seg_idx * seg_len)) / seg_len
    return lerp_color(colors[seg_idx], colors[seg_idx + 1], local_t)


def libs_colorize_gradient(text: str, colors: list[tuple[int, int, int]] | None = None) -> str:
    if colors is None:
        colors = [DEEP_VIOLET, AMETHYST, BLOOD_RED, CHROME]

    clean = strip_ansi(text)
    if not clean:
        return text

    n = len(clean)
    result = []
    clean_idx = 0
    in_ansi = False
    ansi_buf: list[str] = []

    for ch in text:
        if ch == "\033":
            in_ansi = True
            ansi_buf.append(ch)
            continue
        if in_ansi:
            ansi_buf.append(ch)
            if ch.isalpha():
                in_ansi = False
                result.append("".join(ansi_buf))
                ansi_buf = []
            continue

        t = clean_idx / max(n - 1, 1)
        r, g, b = multi_gradient_color(colors, t)
        result.append(f"{fg_rgb(r, g, b)}{ch}")
        clean_idx += 1

    result.append(RESET)
    return "".join(result)

colorize_gradient = libs_colorize_gradient


def libs_make_badge(
    text: str,
    bg_tuple: tuple[int, int, int],
    fg_tuple: tuple[int, int, int] = (0, 0, 0),
    width: int = 10,
) -> str:
    padded = f" {text} ".center(width)
    return f"{bg_rgb(*bg_tuple)}{fg_rgb(*fg_tuple)}{BOLD}{padded}{RESET}"

make_badge = libs_make_badge


# ── Gothic / Y2K NOAME Logo ──────────────────────────────────────────────────
LIBS_LOGO_WIDE = [
    r"  _  _  ___   _   __  __ ___   ___   _   ___   ____ ___ ___ ",
    r" | \| |/ _ \ /_\ |  \/  | __| | _ ) /_\ |   \ / ___| __/ __|",
    r" | .` | (_) / _ \| |\/| | _|  | _ \/ _ \| |) | (_ || _|\__ \\",
    r" |_|\_|\___/_/ \_\_|  |_|___| |___/_/ \_\___/ \___|___|___/",
]

LIBS_LOGO_STACKED = LIBS_LOGO_WIDE
LOGO_WIDE = LIBS_LOGO_WIDE
LOGO_STACKED = LIBS_LOGO_STACKED


def libs_render_progress_bar(current: int, total: int, width: int = 26) -> str:
    if total == 0:
        pct = 1.0
    else:
        pct = min(current / total, 1.0)
    filled = int(pct * width)
    empty  = width - filled

    bar_fill  = f"{fg_rgb(*BLOOD_RED)}{'█' * filled}{RESET}"
    bar_empty = f"{fg_rgb(*DARK_BORDER)}{'░' * empty}{RESET}"
    counter   = f"{fg_rgb(*CHROME)}{current}{fg_rgb(*VOID_GRAY)}/{fg_rgb(*SILVER)}{total}{RESET}"
    pct_label = f"{fg_rgb(*MUTED_LILAC)}{pct*100:5.1f}%{RESET}"

    return f"{fg_rgb(*DARK_BORDER)}[{RESET}{bar_fill}{bar_empty}{fg_rgb(*DARK_BORDER)}]{RESET}  {counter}  {pct_label}"

render_progress_bar = libs_render_progress_bar


def libs_render_header(
    games_count: int,
    claimed_games: int,
    claimed_hours: float,
    stream_hours: float = 0.0,
    user_id: str = "",
    width: int | None = None,
) -> str:
    if width is None:
        width = libs_get_term_width()

    lines_out = [""]

    # Gradient: Deep violet -> Blood crimson -> Chrome silver -> Amethyst
    grad_colors = [DEEP_VIOLET, AMETHYST, BLOOD_RED, CHROME, MUTED_LILAC]
    banner_grad = [libs_colorize_gradient(l, grad_colors) for l in LIBS_LOGO_WIDE]
    lines_out.extend(center_block(banner_grad, width))
    lines_out.append("")

    # Gothic / YVL subtitle line
    sub = (
        f"{fg_rgb(*DARK_BORDER)}── ✦ ──{RESET}   "
        f"{fg_rgb(*MUTED_LILAC)}{ITALIC}†  y v l   s c i e n c e   t e l e m e t r y  †{RESET}   "
        f"{fg_rgb(*DARK_BORDER)}── ✦ ──{RESET}"
    )
    lines_out.append(center(sub, width))
    lines_out.append("")

    # Stats row with clean diamond delimiters
    acc_display = (
        f"{fg_rgb(*CHROME)}{BOLD}{user_id}{RESET}"
        if user_id
        else f"{fg_rgb(*RED_SOFT)}NOT SET{RESET}"
    )
    sep_dot = f"  {fg_rgb(*DARK_BORDER)}◆{RESET}  "
    stats_line = (
        f"{fg_rgb(*VOID_GRAY)}user{RESET} {acc_display}"
        f"{sep_dot}{fg_rgb(*VOID_GRAY)}games{RESET} {fg_rgb(*GREEN_MINT)}{claimed_games:,}{RESET}"
        f"{sep_dot}{fg_rgb(*VOID_GRAY)}game hrs{RESET} {fg_rgb(*AMETHYST)}{claimed_hours:,.0f}h{RESET}"
        f"{sep_dot}{fg_rgb(*VOID_GRAY)}stream hrs{RESET} {fg_rgb(*CRIMSON)}{stream_hours:,.1f}h{RESET}"
    )
    lines_out.append(center(stats_line, width))

    # Author credit
    credit_line = (
        f"{fg_rgb(*BLOOD_RED)}†{RESET}  "
        f"{fg_rgb(*VOID_GRAY)}crafted by{RESET}  "
        f"{fg_rgb(*CHROME)}{BOLD}Yeti{RESET} "
        f"{fg_rgb(*DARK_BORDER)}[ {RESET}{fg_rgb(*MUTED_LILAC)}@despairlyf{RESET}{fg_rgb(*DARK_BORDER)} ]{RESET}  "
        f"{fg_rgb(*BLOOD_RED)}†{RESET}"
    )
    lines_out.append(center(credit_line, width))
    lines_out.append("")

    # Command menu
    menu_lines = libs_render_command_matrix(width=width)
    lines_out.extend(menu_lines)
    lines_out.append("")

    # Live telemetry divider
    div_label = f" {fg_rgb(*BLOOD_RED)}†{RESET}  {fg_rgb(*VOID_GRAY)}live telemetry feed{RESET}  {fg_rgb(*BLOOD_RED)}†{RESET} "
    div_plain = len(strip_ansi(div_label))
    box_w = min(width - 4, 76)
    left_len = 4
    right_len = max(0, box_w - left_len - div_plain)
    section_div = (
        f"{fg_rgb(*DARK_BORDER)}{'─' * left_len}{RESET}"
        f"{div_label}"
        f"{fg_rgb(*DARK_BORDER)}{'─' * right_len}{RESET}"
    )
    lines_out.append(center(section_div, width))
    lines_out.append("")

    return "\n".join(lines_out)

render_header = libs_render_header


def libs_render_command_matrix(width: int | None = None) -> list[str]:
    if width is None:
        width = libs_get_term_width()

    # (ID, Title, Subtitle/Desc)
    commands = [
        ("01", "Claim Playtime & Games", "farm 5k+ hrs · 100+ titles"),
        ("02", "AFK Headless Streamer",   "farm 5k hrs streaming badge"),
        ("03", "Refresh Auth Token",      "update analytics token"),
        ("04", "Regenerate Fingerprint",  "cross-platform pe hash"),
        ("05", "View Account Status",     "session diagnostics & metrics"),
        ("06", "Exit NOAME badges",       "persist state & terminate"),
    ]

    act_w = 26
    dsc_w = 32

    # Visual width: 2(sp) + 1(†) + 2(sp) + 2(num) + 3(gap) + 26(act) + 4(arrow) + 32(dsc) = 72
    row_visual_w = 72
    sym = " ⸸ ✦ ⸸ "
    sym_len = len(sym)
    half_l = max(4, (row_visual_w - sym_len) // 2)
    half_r = max(4, row_visual_w - sym_len - half_l)

    sep_line = (
        f"{fg_rgb(*BLOOD_RED)}{'━' * half_l}{RESET}"
        f"{fg_rgb(*MUTED_LILAC)}{BOLD}{sym}{RESET}"
        f"{fg_rgb(*BLOOD_RED)}{'━' * half_r}{RESET}"
    )

    rows_ansi: list[str] = []
    rows_ansi.append(sep_line)
    rows_ansi.append("")

    for num, action, desc in commands:
        bullet = f"{fg_rgb(*BLOOD_RED)}†{RESET}"
        num_c  = f"{fg_rgb(*CHROME)}{BOLD}{num}{RESET}"
        act_c  = f"{fg_rgb(*GHOST_WHITE)}{BOLD}{action:<{act_w}}{RESET}"
        arrow  = f"{fg_rgb(*DARK_BORDER)}:::{RESET}"
        dsc_c  = f"{fg_rgb(*VOID_GRAY)}{desc:<{dsc_w}}{RESET}"
        rows_ansi.append(f"  {bullet}  {num_c}   {act_c}  {arrow}  {dsc_c}")

    rows_ansi.append("")
    rows_ansi.append(sep_line)

    return center_block(rows_ansi, width)

render_command_matrix = libs_render_command_matrix


# ── Logging helpers ────────────────────────────────────────────────────────────

def libs_log_info(msg: str) -> None:
    badge = libs_make_badge("info", DEEP_VIOLET, CHROME, width=8)
    arrow = f"{fg_rgb(*AMETHYST)}──›{RESET}"
    print(f"   {badge} {arrow} {fg_rgb(*GHOST_WHITE)}{msg}{RESET}")

log_info = libs_log_info


def libs_log_success(msg: str) -> None:
    badge = libs_make_badge("ok", (22, 101, 52), (187, 247, 208), width=8)
    arrow = f"{fg_rgb(*GREEN_MINT)}──›{RESET}"
    print(f"   {badge} {arrow} {fg_rgb(*GREEN_MINT)}{msg}{RESET}")

log_success = libs_log_success


def libs_log_sent(target: str, detail: str) -> None:
    badge = libs_make_badge("sent", ROSE_DARK, (254, 205, 211), width=8)
    arrow = f"{fg_rgb(*BLOOD_RED)}──›{RESET}"
    ts    = f"{fg_rgb(*VOID_GRAY)}{time.strftime('%H:%M:%S')}{RESET}"
    print(f"   {badge} {arrow} {ts}  {fg_rgb(*SILVER)}{target:<16}{RESET}{fg_rgb(*GREEN_MINT)}{detail}{RESET}")

log_sent = libs_log_sent


def libs_log_progress(label: str, current: int, total: int) -> None:
    bar = libs_render_progress_bar(current, total, width=26)
    lbl = f"{fg_rgb(*VOID_GRAY)}{label}{RESET}"
    print(f"   {lbl}  {bar}")

log_progress = libs_log_progress


def libs_log_warn(msg: str) -> None:
    badge = libs_make_badge("warn", (120, 53, 15), (254, 215, 170), width=8)
    arrow = f"{fg_rgb(*SILVER)}──›{RESET}"
    print(f"   {badge} {arrow} {fg_rgb(*SILVER)}{msg}{RESET}")

log_warn = libs_log_warn


def libs_log_error(msg: str) -> None:
    badge = libs_make_badge("err", BLOOD_RED, (254, 226, 226), width=8)
    arrow = f"{fg_rgb(*CRIMSON)}──›{RESET}"
    print(f"   {badge} {arrow} {fg_rgb(*RED_SOFT)}{msg}{RESET}")

log_error = libs_log_error


def libs_log_divider(title: str | None = None) -> None:
    w = min(libs_get_term_width() - 4, 76)
    if title:
        badge = f"  {fg_rgb(*BLOOD_RED)}†{RESET}  {fg_rgb(*VOID_GRAY)}{title.lower()}{RESET}  {fg_rgb(*BLOOD_RED)}†{RESET}  "
        clean_len = len(strip_ansi(badge))
        left = 4
        right = max(0, w - left - clean_len)
        print(center(
            f"{fg_rgb(*DARK_BORDER)}{'─' * left}{RESET}{badge}{fg_rgb(*DARK_BORDER)}{'─' * right}{RESET}"
        ))
    else:
        print(center(f"{fg_rgb(*DARK_BORDER)}{'─' * w}{RESET}"))

log_divider = libs_log_divider


def libs_prompt_input(label: str) -> str:
    arrow = f"{fg_rgb(*BLOOD_RED)}❯{RESET}"
    return input(f"   {arrow} {fg_rgb(*GHOST_WHITE)}{label}{RESET} ").strip()

prompt_input = libs_prompt_input
