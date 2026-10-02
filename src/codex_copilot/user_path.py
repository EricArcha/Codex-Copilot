"""Opt-in, reversible management of the Windows user's PATH (never system PATH)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def normalize(value: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.expandvars(value.strip().strip('"'))))


def read() -> dict[str, Any]:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            value, kind = winreg.QueryValueEx(key, "Path")
            if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) or not isinstance(value, str):
                raise ValueError("User PATH is not a string registry value")
            return {"present": True, "value": value, "type": kind}
        except FileNotFoundError:
            return {"present": False, "value": "", "type": winreg.REG_EXPAND_SZ}


def write(state: dict[str, Any]) -> None:
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        if state["present"]:
            winreg.SetValueEx(key, "Path", 0, state["type"], state["value"])
        else:
            try:
                winreg.DeleteValue(key, "Path")
            except FileNotFoundError:
                pass
    # New applications need to inherit the changed environment. Existing shells
    # retain their own environment; documentation gives a session command.
    import ctypes
    result = ctypes.c_size_t()
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 2, 1000, ctypes.byref(result))


def plan(directory: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    before = read()
    entry = str(directory.resolve())
    added = not any(normalize(part) == normalize(entry) for part in before["value"].split(";") if part)
    after = dict(before)
    if added:
        after.update(present=True, value=before["value"] + (";" if before["value"] else "") + entry)
    ownership = {"entry": entry, "added": added, "original_present": before["present"], "original_type": before["type"]}
    return before, after, ownership


def removal(ownership: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    before = read()
    after = dict(before)
    if ownership.get("added"):
        parts = before["value"].split(";")
        # Only remove our literal entry, once. Reformatted/user-added entries stay.
        if ownership["entry"] in parts:
            parts.remove(ownership["entry"])
            after["value"] = ";".join(parts)
            if not after["value"] and not ownership.get("original_present", True):
                after["present"] = False
    return before, after
