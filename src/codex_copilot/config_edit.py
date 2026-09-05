from __future__ import annotations

import copy
import re
import tomllib
from dataclasses import dataclass
from typing import Any


MISSING = object()
_SECTION_RE = re.compile(r"^\s*\[([^\]]+)]\s*(?:#.*)?$")


@dataclass(frozen=True)
class ConfigChange:
    path: str
    previous_present: bool
    previous_value: Any
    installed_value: Any


def parse_toml(text: str) -> dict[str, Any]:
    return tomllib.loads(text) if text.strip() else {}


def get_path(data: dict[str, Any], path: str, default: Any = MISSING) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def toml_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"Unsupported managed TOML value: {type(value).__name__}")


def _section_bounds(lines: list[str], section: str) -> tuple[int, int] | None:
    start = None
    for index, line in enumerate(lines):
        match = _SECTION_RE.match(line)
        if match and match.group(1).strip() == section:
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if _SECTION_RE.match(lines[index]):
            end = index
            break
    return start, end


def _assignment_re(key: str) -> re.Pattern[str]:
    return re.compile(rf"^(\s*){re.escape(key)}\s*=.*$")


def _set_one(lines: list[str], path: str, value: Any) -> list[str]:
    parts = path.split(".")
    section = ".".join(parts[:-1])
    key = parts[-1]
    replacement = None if value is MISSING else f"{key} = {toml_literal(value)}\n"

    if not section:
        end = next((i for i, line in enumerate(lines) if _SECTION_RE.match(line)), len(lines))
        pattern = _assignment_re(key)
        for index in range(end):
            if pattern.match(lines[index]):
                if replacement is None:
                    del lines[index]
                else:
                    lines[index] = replacement
                return lines
        if replacement is not None:
            insert_at = end
            lines.insert(insert_at, replacement)
        return lines

    # Root-level dotted keys are valid TOML and must be updated in place rather
    # than followed by a duplicate table declaration.
    dotted = f"{section}.{key}"
    root_end = next((i for i, line in enumerate(lines) if _SECTION_RE.match(line)), len(lines))
    dotted_pattern = _assignment_re(dotted)
    for index in range(root_end):
        if dotted_pattern.match(lines[index]):
            if replacement is None:
                del lines[index]
            else:
                lines[index] = f"{dotted} = {toml_literal(value)}\n"
            return lines

    bounds = _section_bounds(lines, section)
    if bounds is None:
        if replacement is None:
            return lines
        prefix_pattern = re.compile(rf"^\s*{re.escape(section)}\.[A-Za-z0-9_-]+\s*=")
        if any(prefix_pattern.match(line) for line in lines[:root_end]):
            lines.insert(root_end, f"{dotted} = {toml_literal(value)}\n")
            return lines
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend([f"[{section}]\n", replacement])
        return lines

    start, end = bounds
    pattern = _assignment_re(key)
    for index in range(start + 1, end):
        if pattern.match(lines[index]):
            if replacement is None:
                del lines[index]
            else:
                lines[index] = replacement
            return lines
    if replacement is not None:
        lines.insert(end, replacement)
    return lines


def apply_updates(text: str, updates: dict[str, Any]) -> tuple[str, list[ConfigChange]]:
    before = parse_toml(text)
    lines = text.splitlines(keepends=True)
    if text and not text.endswith("\n"):
        lines[-1] += "\n"
    changes: list[ConfigChange] = []
    for path, value in updates.items():
        previous = get_path(before, path)
        changes.append(
            ConfigChange(
                path=path,
                previous_present=previous is not MISSING,
                previous_value=None if previous is MISSING else copy.deepcopy(previous),
                installed_value=value,
            )
        )
        lines = _set_one(lines, path, value)
    result = "".join(lines)
    parse_toml(result)
    return result, changes


def restore_updates(text: str, recorded: list[dict[str, Any]]) -> tuple[str, list[str]]:
    current = parse_toml(text)
    updates: dict[str, Any] = {}
    warnings: list[str] = []
    for item in recorded:
        path = item["path"]
        now = get_path(current, path)
        if now is MISSING or now != item["installed_value"]:
            warnings.append(f"Preserved user-modified config key: {path}")
            continue
        updates[path] = item["previous_value"] if item["previous_present"] else MISSING
    lines = text
    for path, value in updates.items():
        raw_lines = lines.splitlines(keepends=True)
        lines = "".join(_set_one(raw_lines, path, value))
    parse_toml(lines)
    return lines, warnings
