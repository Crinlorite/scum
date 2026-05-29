"""
Minimal pure-Python parser for Unreal Engine .locres files (v1-v4).

Reference: Crauzer/UnrealLocres (C#) and the UE4 source for
FTextLocalizationResource. The format is:

    [16] magic GUID (0E 14 74 75 67 4A 03 FC 4A 15 90 9D C3 37 7F 1B)
    [1]  version byte  (1=Legacy, 2=Compact, 3=Optimized, 4=Optimized_CityHash64_UTF16)
    [8]  uint64 strings_offset

    if version >= 4:
        [4] uint32 entries_count   (unused by us)

    [4] uint32 namespace_count
    for namespace_count:
        if version >= 3: [4] uint32 namespace_hash   (Optimized)
        FString namespace
        [4] uint32 key_count
        for key_count:
            if version >= 3: [4] uint32 key_hash     (Optimized)
            FString key
            [4] uint32 source_string_hash
            [4] int32  string_array_index

    At strings_offset:
        [4] uint32 string_array_count
        for string_array_count:
            FString text
            [4] int32 refcount   (only when version >= 2)

FString encoding:
    [4] int32 length
    if length > 0: UTF-8, `length` bytes (includes trailing NUL byte)
    if length < 0: UTF-16-LE, `-length` code units (includes trailing NUL)
    if length == 0: empty string

Output of parse(): { namespace_str: { key_str: value_str, ... }, ... }
"""

from __future__ import annotations
import io
import struct
from typing import BinaryIO

MAGIC = bytes.fromhex("0E147475674A03FC4A15909DC3377F1B")


def _read_fstring(f: BinaryIO) -> str:
    raw_len = f.read(4)
    if len(raw_len) < 4:
        raise ValueError("Unexpected EOF reading FString length")
    (length,) = struct.unpack("<i", raw_len)
    if length == 0:
        return ""
    if length > 0:
        data = f.read(length)
        if len(data) != length:
            raise ValueError(f"Short UTF-8 FString read ({len(data)}/{length})")
        return data.rstrip(b"\x00").decode("utf-8", errors="replace")
    # length < 0 → UTF-16-LE, -length code units (2 bytes each)
    nbytes = -length * 2
    data = f.read(nbytes)
    if len(data) != nbytes:
        raise ValueError(f"Short UTF-16 FString read ({len(data)}/{nbytes})")
    text = data.decode("utf-16-le", errors="replace")
    # Strip the trailing NUL the count includes.
    return text.rstrip("\x00")


def parse(path: str) -> dict[str, dict[str, str]]:
    with open(path, "rb") as f:
        magic = f.read(16)
        if magic != MAGIC:
            raise ValueError(
                f"Bad locres magic in {path}: got {magic.hex()} expected {MAGIC.hex()}"
            )
        (version,) = struct.unpack("<B", f.read(1))
        if version < 1 or version > 4:
            raise ValueError(f"Unsupported locres version {version}")
        (strings_offset,) = struct.unpack("<Q", f.read(8))

        # First, jump to the strings table so we can resolve indices.
        cur = f.tell()
        f.seek(strings_offset)
        (str_count,) = struct.unpack("<I", f.read(4))
        strings: list[str] = []
        for _ in range(str_count):
            s = _read_fstring(f)
            if version >= 2:
                f.read(4)  # refcount, ignored
            strings.append(s)
        f.seek(cur)

        if version >= 4:
            f.read(4)  # entries_count, ignored

        (ns_count,) = struct.unpack("<I", f.read(4))
        out: dict[str, dict[str, str]] = {}
        for _ in range(ns_count):
            if version >= 3:
                f.read(4)  # namespace hash (Optimized format), ignored
            ns = _read_fstring(f)
            (key_count,) = struct.unpack("<I", f.read(4))
            bucket: dict[str, str] = out.setdefault(ns, {})
            for _ in range(key_count):
                if version >= 3:
                    f.read(4)  # key hash (Optimized format), ignored
                key = _read_fstring(f)
                f.read(4)  # source_string_hash
                (idx,) = struct.unpack("<i", f.read(4))
                if 0 <= idx < len(strings):
                    bucket[key] = strings[idx]
                else:
                    bucket[key] = ""
        return out


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("usage: python locres.py <file.locres> [<file.locres> ...]")
        sys.exit(1)
    for path in sys.argv[1:]:
        data = parse(path)
        print(json.dumps({"file": path, "namespaces": len(data),
                          "keys": sum(len(v) for v in data.values())},
                         ensure_ascii=False))
