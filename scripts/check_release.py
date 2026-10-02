"""Validate release metadata using only the standard library."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    args = parser.parse_args()
    try:
        version = validate(Path(__file__).resolve().parents[1], args.tag)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Release validation failed: {exc}\n")
    print(f"Release metadata valid: {version}")


if __name__ == "__main__":
    main()
