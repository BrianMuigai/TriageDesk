"""Packaged agent skills shipped with the TriageDesk MCP server (CONVENTIONS §1).

The skill is package data, not a repo-only file: a wheel carries it, and both the
MCP installer and the ``triagedesk skill`` command read it through this module.
That keeps the skill installable from a checkout *and* from an installed package,
with the name and the recursive copy defined once.

The copy is deliberately byte-for-byte and idempotent. A locally edited skill is a
conflict, never a silent overwrite, unless the caller passes ``force``.
"""

from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

# The ONE skill this package ships, matching its directory name (the harness's skill id).
SKILL_NAME = "triagedesk-triage"


def skill_root() -> Traversable:
    """Return the package-resource root of the installed usage skill."""
    return files(__name__).joinpath(SKILL_NAME)


def _skill_files(node: Traversable, prefix: Path | None = None) -> dict[Path, bytes]:
    """Collect the packaged skill's files as ``relative path -> bytes``.

    ``importlib.resources`` has no ``rglob``, and the installer must work from a
    wheel (where the skill is not a plain directory), so the walk is explicit
    rather than a ``Path`` glob.
    """
    base = prefix or Path()
    collected: dict[Path, bytes] = {}
    for child in node.iterdir():
        relative = base / child.name
        if child.is_dir():
            collected.update(_skill_files(child, relative))
        elif child.is_file():
            collected[relative] = child.read_bytes()
    return collected


def install_skill(skills_dir: Path, *, force: bool = False) -> str:
    """Copy the packaged usage skill into *skills_dir*, idempotently.

    The skill lives at ``<skills_dir>/<SKILL_NAME>/``. An existing file with the
    same bytes is a no-op; a differing file is a conflict unless ``force`` is set,
    so a local edit is never silently overwritten. The whole directory is copied,
    including ``references/``.
    """
    destination = skills_dir / SKILL_NAME
    payload = _skill_files(skill_root())
    if not payload:
        raise ValueError(f"the packaged skill {SKILL_NAME!r} is empty")

    conflicts: list[Path] = []
    for relative, content in payload.items():
        target = destination / relative
        if target.exists() and not target.is_file():
            raise ValueError(f"{target} is not a file")
        if target.is_file() and target.read_bytes() != content:
            conflicts.append(target)
    if conflicts and not force:
        raise ValueError(
            f"{destination} already contains a different {SKILL_NAME} skill; "
            "re-run with --force to replace it"
        )

    written = 0
    for relative, content in payload.items():
        target = destination / relative
        if target.is_file() and target.read_bytes() == content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        written += 1
    if written == 0:
        return f"already installed: {destination}"
    return f"wrote {destination}"


__all__ = ["SKILL_NAME", "install_skill", "skill_root"]
