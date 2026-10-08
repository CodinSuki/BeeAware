"""Opt-in local personal-training cache protected by Windows DPAPI."""

from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes

from config import TRAINING_CACHE_PATH


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _protect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("The personal cache requires Windows DPAPI")
    source_buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    target = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(ctypes.byref(source), None, None, None, None, 4, ctypes.byref(target)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def _unprotect(data: bytes) -> bytes:
    if os.name != "nt":
        raise RuntimeError("The personal cache requires Windows DPAPI")
    source_buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    target = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 4, ctypes.byref(target)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def append_record(record: dict) -> None:
    os.makedirs(os.path.dirname(TRAINING_CACHE_PATH), exist_ok=True)
    encoded = base64.b64encode(_protect(json.dumps(record, ensure_ascii=False).encode("utf-8")))
    with open(TRAINING_CACHE_PATH, "a", encoding="ascii") as stream:
        stream.write(encoded.decode("ascii") + "\n")


def load_records() -> list[dict]:
    if not os.path.isfile(TRAINING_CACHE_PATH):
        return []
    records = []
    with open(TRAINING_CACHE_PATH, "r", encoding="ascii") as stream:
        for line in stream:
            try:
                records.append(json.loads(_unprotect(base64.b64decode(line.strip())).decode("utf-8")))
            except Exception:
                continue
    return records
