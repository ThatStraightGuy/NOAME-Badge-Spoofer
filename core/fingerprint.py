"""
lib's magic — Discord Game Badge Spoofer
Made by Yeti [ @yvlsoul ]

For educational and research purposes only.
"""

from __future__ import annotations

import base64
import hashlib
import struct
import time
import uuid


def libs_generate_fingerprint(user_id: str) -> str:
    flags = 2
    file_size = 45_214_720
    timestamp = int(time.time()) - 86400 * 30
    size_of_image = 48_500_000
    header_hash = hashlib.sha256(b"discord_game_header_hash").digest()
    machine_guid = str(uuid.uuid4())
    machine_user_hash = hashlib.sha256(f"{machine_guid}{user_id}".encode("utf-8")).digest()
    section_hash = hashlib.sha256(b"discord_game_section_hash").digest()
    cert_hash = bytes(32)

    buf = bytearray()
    buf.append(1)
    buf.append(flags)
    buf.extend(struct.pack("<Q", file_size))
    buf.extend(struct.pack("<I", timestamp))
    buf.extend(struct.pack("<I", size_of_image))
    buf.extend(header_hash)
    buf.extend(machine_user_hash)
    buf.extend(section_hash)
    buf.extend(cert_hash)

    key = hashlib.sha256(f"{user_id}https://discord.com/careers".encode("utf-8")).digest()
    for i in range(1, len(buf)):
        buf[i] ^= key[(i - 1) & 31]

    return base64.b64encode(buf).decode("ascii")


generate_fingerprint = libs_generate_fingerprint
