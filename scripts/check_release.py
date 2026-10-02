"""Validate release metadata using only the standard library."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tomllib


def validate(root: Path, tag: str | None = None) -> str:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
        raise ValueError("VERSION must contain a stable major.minor.patch version")
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if metadata["project"]["version"] != version:
        raise ValueError("pyproject.toml version does not match VERSION")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(r"^## \[" + re.escape(version) + r"\] - \d{4}-\d{2}-\d{2}$", changelog, re.MULTILINE):
        raise ValueError("CHANGELOG.md must have a dated entry for VERSION")
    if tag is not None and tag != f"v{version}":
        raise ValueError("Release tag does not match VERSION")
    return version


def check_product_tree(root: Path) -> None:
    """Release sources must be committed; never print potentially private paths."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all", "--",
             "src", "skill", "agents", "bin", "VERSION"],
            cwd=root, capture_output=True, text=True, check=True, timeout=10,
        )
        ignored = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--",
             "src", "skill", "agents", "bin", "VERSION"],
            cwd=root, capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError("Cannot verify committed product trees for release") from None
    if any(path and not path.endswith((".pyc", ".pyo"))
           for path in ignored.stdout.split("\0")):
        raise ValueError("Release product trees contain ignored non-runtime content")
    if result.stdout.strip():
        raise ValueError("Release product trees contain uncommitted or untracked content")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[1]
        version = validate(root, args.tag)
        if args.tag:
            check_product_tree(root)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")
    print(f"Release metadata valid: {version}")


if __name__ == "__main__":
    main()
