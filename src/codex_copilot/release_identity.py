"""Read-only project Git identity check; never changes global or local config."""
from __future__ import annotations

import subprocess


def check() -> dict[str, object]:
    def read(args: list[str]) -> str | None:
        result = subprocess.run(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, encoding="utf-8", timeout=5)
        return result.stdout.strip() if result.returncode == 0 else None

    name = read(["config", "--local", "--get", "user.name"])
    email = read(["config", "--local", "--get", "user.email"])
    expected = f"{name} <{email}> " if name and email else None
    author = read(["var", "GIT_AUTHOR_IDENT"]) if expected else None
    committer = read(["var", "GIT_COMMITTER_IDENT"]) if expected else None
    # Environment identities may override repository config. Validate effective values.
    matches = bool(expected and author and committer and author.startswith(expected) and committer.startswith(expected))
    return {"project_identity_configured": bool(expected), "effective_identity_matches": matches,
            "ready": matches, "next_step": None if matches else
            "Confirm and set the project-local author/committer identity before committing; do not change global Git identity."}
