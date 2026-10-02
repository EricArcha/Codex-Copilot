"""Capability probes: skip only the operation the host cannot perform."""
import os
from pathlib import Path


def require_symlinks(test, directory):
    target = Path(directory) / "symlink-probe-target"
    link = Path(directory) / "symlink-probe-link"
    target.write_text("probe", encoding="utf-8")
    try:
        link.symlink_to(target)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            test.skipTest("Windows account lacks symlink privilege (WinError 1314)")
        raise
    finally:
        link.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
