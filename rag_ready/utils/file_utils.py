from __future__ import annotations

import hashlib
import os
from typing import Any


def get_file_extension(name: str) -> str:
    return os.path.splitext(name)[1].lstrip(".").lower()


def calculate_file_md5(path: str, chunk_size: int = 1024 * 1024) -> str:
    m = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            m.update(b)
    return m.hexdigest()


def dhash(image: Any, hash_size: int = 8) -> str:
    resized = image.resize((hash_size + 1, hash_size)).convert("L")
    pixels = list(resized.getdata())
    rows = [pixels[i : i + hash_size + 1] for i in range(0, len(pixels), hash_size + 1)]
    diff = []
    for row in rows:
        for col in range(hash_size):
            diff.append(row[col] > row[col + 1])
    decimal_value = 0
    hex_string = []
    for i, v in enumerate(diff):
        if v:
            decimal_value |= 1 << (i % 8)
        if (i % 8) == 7:
            hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
            decimal_value = 0
    return "".join(hex_string)


def hamming_distance(hash1: str, hash2: str) -> int:
    if len(hash1) != len(hash2):
        return max(len(hash1), len(hash2))
    distance = 0
    for c1, c2 in zip(hash1, hash2):
        if c1 != c2:
            distance += 1
    return distance

