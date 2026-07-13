"""Manuscript project profile — any book, not a single theory."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROFILE_NAME = "manuscript.toml"


@dataclass
class ManuscriptProfile:
    name: str = "Untitled Manuscript"
    language: str = "en"
    outline: str = "state/manuscript_outline.json"
    drafts: str = "drafts"
    approved: str = "approved"
    figures: str = "figures"
    screenshots: str = "screenshots"
    ocr_hints: list[str] = field(default_factory=list)
    root: Path = field(default_factory=Path)

    def path(self, key: str) -> Path:
        rel = getattr(self, key)
        p = Path(rel)
        return p if p.is_absolute() else (self.root / p)

    @property
    def hint_set(self) -> set[str]:
        return {h.strip() for h in self.ocr_hints if h and str(h).strip()}


def _parse_toml(text: str) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore

    return tomllib.loads(text)


def load_profile(root: Path | None = None, path: Path | None = None) -> ManuscriptProfile:
    root = Path(root) if root else Path.cwd()
    path = Path(path) if path else (root / PROFILE_NAME)
    if not path.exists():
        return ManuscriptProfile(root=root)

    data = _parse_toml(path.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    paths = data.get("paths") or {}
    vision = data.get("vision") or {}
    return ManuscriptProfile(
        name=str(project.get("name") or "Untitled Manuscript"),
        language=str(project.get("language") or "en"),
        outline=str(paths.get("outline") or "state/manuscript_outline.json"),
        drafts=str(paths.get("drafts") or "drafts"),
        approved=str(paths.get("approved") or "approved"),
        figures=str(paths.get("figures") or "figures"),
        screenshots=str(paths.get("screenshots") or "screenshots"),
        ocr_hints=[str(x) for x in (vision.get("ocr_hints") or [])],
        root=path.parent.resolve(),
    )


def profile_toml(
    *,
    name: str,
    language: str = "en",
    ocr_hints: list[str] | None = None,
) -> str:
    hints = ocr_hints or []
    hint_lines = "\n".join(f'  "{h}",' for h in hints)
    hints_block = f"ocr_hints = [\n{hint_lines}\n]" if hints else "ocr_hints = []"
    return f"""# Manuscript profile for tuch-vision
# Domain theory (if any) lives in style/constraints docs — not in this tool core.

[project]
name = {json.dumps(name)}
language = {json.dumps(language)}

[paths]
outline = "state/manuscript_outline.json"
drafts = "drafts"
approved = "approved"
figures = "figures"
screenshots = "screenshots"

[vision]
# Optional soft priors for OCR↔caption checks (numbers, tokens). Empty = generic.
{hints_block}
"""


SAMPLE_OUTLINE = {
    "title": "Untitled Manuscript",
    "parts": [
        {
            "id": "part1",
            "title": "Part I",
            "chapters": [
                {
                    "id": "ch01",
                    "title": "Chapter 1",
                    "status": "draft",
                    "words_target": 2000,
                    "words_current": 0,
                    "needs_expansion": [],
                    "narrative_promises": [],
                },
                {
                    "id": "ch02",
                    "title": "Chapter 2",
                    "status": "draft",
                    "words_target": 2000,
                    "words_current": 0,
                    "needs_expansion": [],
                    "narrative_promises": [],
                },
            ],
        }
    ],
}


def init_manuscript(
    root: Path,
    *,
    name: str = "Untitled Manuscript",
    language: str = "en",
    ocr_hints: list[str] | None = None,
    force: bool = False,
) -> Path:
    """Create a generic manuscript project scaffold."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    profile_path = root / PROFILE_NAME
    if profile_path.exists() and not force:
        raise FileExistsError(f"Already initialized: {profile_path}")

    for rel in (
        "state",
        "drafts",
        "approved",
        "figures",
        "screenshots",
        "output",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)

    outline = dict(SAMPLE_OUTLINE)
    outline["title"] = name
    (root / "state" / "manuscript_outline.json").write_text(
        json.dumps(outline, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "state" / "style_guide.md").write_text(
        f"# Style guide — {name}\n\nVoice, audience, terminology — fill for your book.\n",
        encoding="utf-8",
    )
    (root / "state" / "constraints.md").write_text(
        f"# Constraints — {name}\n\n"
        "Domain facts, notation, and must-not-contradict rules.\n"
        "Keep theory-specific constants here (not in the vision tool core).\n",
        encoding="utf-8",
    )
    (root / "drafts" / "ch01.md").write_text(
        f"# Chapter 1\n\nDraft for **{name}**.\n",
        encoding="utf-8",
    )
    (root / "screenshots" / "README.md").write_text(
        "Drop UI screenshots here, then run:\n\n"
        "```bash\ntuch-vision screens ./screenshots --project .\n```\n",
        encoding="utf-8",
    )
    profile_path.write_text(
        profile_toml(name=name, language=language, ocr_hints=ocr_hints),
        encoding="utf-8",
    )
    return profile_path
