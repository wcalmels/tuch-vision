"""
Extract normalized [0,1] health signals from manuscript_outline.json.

Channels (higher ≈ healthier for a finished / near-finished book):
  fill_ratio      — words_current / words_target (capped at 1.05 → 1.0)
  approval        — approved=1.0, draft=0.55, other=0.15
  expansion_ok    — 1 − min(1, needs_expansion / 5)
  promises_ok     — 1 − min(1, open narrative_promises / 5)
  file_ready      — approved or draft file present
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ChapterSignals:
    chapter_id: str
    title: str
    status: str
    words_current: int
    words_target: int
    fill_ratio: float
    approval: float
    expansion_ok: float
    promises_ok: float
    file_ready: float
    needs_expansion: int = 0
    open_promises: int = 0
    has_file: bool = False

    def as_dict(self) -> Dict[str, float]:
        return {
            "fill_ratio": self.fill_ratio,
            "approval": self.approval,
            "expansion_ok": self.expansion_ok,
            "promises_ok": self.promises_ok,
            "file_ready": self.file_ready,
        }


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _iter_units(outline: dict):
    """Yield chapter/section dicts that have id + words fields."""
    for part in outline.get("parts", []):
        if "chapters" in part:
            for ch in part["chapters"]:
                yield ch
        if part.get("id") and "words_target" in part and "chapters" not in part:
            # e.g. preface / interludio as top-level part
            if "sections" not in part:
                yield part
        for sec in part.get("sections", []):
            yield sec


def collect_chapters(
    outline: dict,
    drafts_dir: Path,
    approved_dir: Path,
) -> List[ChapterSignals]:
    out: List[ChapterSignals] = []
    for unit in _iter_units(outline):
        cid = unit.get("id")
        if not cid:
            continue
        target = max(int(unit.get("words_target") or 1), 1)
        current = int(unit.get("words_current") or 0)
        fill = _clamp01(current / target)
        # slight overshoot still healthy
        if current > target:
            fill = _clamp01(0.85 + 0.15 * min(1.0, target / max(current, 1)))

        status = (unit.get("status") or "").lower()
        if status == "approved":
            approval = 1.0
        elif status in ("draft", "in_progress", "review"):
            approval = 0.55
        else:
            approval = 0.15

        needs = unit.get("needs_expansion") or []
        promises = unit.get("narrative_promises") or []
        n_needs = len(needs) if isinstance(needs, list) else 0
        n_prom = len(promises) if isinstance(promises, list) else 0

        has_file = (approved_dir / f"{cid}.md").exists() or (
            drafts_dir / f"{cid}.md"
        ).exists()

        out.append(
            ChapterSignals(
                chapter_id=cid,
                title=unit.get("title") or cid,
                status=status or "unknown",
                words_current=current,
                words_target=target,
                fill_ratio=fill,
                approval=approval,
                expansion_ok=_clamp01(1.0 - min(1.0, n_needs / 5.0)),
                promises_ok=_clamp01(1.0 - min(1.0, n_prom / 5.0)),
                file_ready=1.0 if has_file else 0.0,
                needs_expansion=n_needs,
                open_promises=n_prom,
                has_file=has_file,
            )
        )
    return out


def book_aggregate(chapters: List[ChapterSignals]) -> Dict[str, float]:
    if not chapters:
        return {
            "fill_ratio": 0.0,
            "approval": 0.0,
            "expansion_ok": 0.0,
            "promises_ok": 0.0,
            "file_ready": 0.0,
        }
    keys = ["fill_ratio", "approval", "expansion_ok", "promises_ok", "file_ready"]
    return {
        k: sum(getattr(c, k) for c in chapters) / len(chapters) for k in keys
    }
