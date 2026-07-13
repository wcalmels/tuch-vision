#!/usr/bin/env python3
"""Markdown report for UI / screenshot audits."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from .docx_figures import FigureUnit


@dataclass
class ScreenReport:
    generated_at: str
    source: str
    ocr_backends: List[str]
    units: List[FigureUnit]
    phics_notes: List[str] = field(default_factory=list)
    spectral_notes: List[str] = field(default_factory=list)
    summary: str = ""

    def to_markdown(self) -> str:
        fails = [u for u in self.units if u.status == "fail"]
        warns = [u for u in self.units if u.status == "warn"]
        oks = [u for u in self.units if u.status == "ok"]

        lines = [
            "# UI / Screenshot Vision Audit",
            "",
            f"Generated: {self.generated_at}",
            f"Source: `{self.source}`",
            f"OCR backends: {', '.join(self.ocr_backends) or 'none'}",
            "",
            f"**Summary:** {self.summary}",
            "",
            "## Counts",
            "",
            f"- Screens: **{len(self.units)}**",
            f"- FAIL: **{len(fails)}** · WARN: **{len(warns)}** · OK: **{len(oks)}**",
            "",
            "## Screens",
            "",
            "| ID | Status | Viewport | Size | OCR lines | Text dens | Quality | Notes |",
            "|----|--------|----------|------|----------:|---------:|--------:|-------|",
        ]
        for u in self.units:
            n_lines = len([ln for ln in (u.ocr_text or "").splitlines() if ln.strip()])
            size = f"{u.width_px}×{u.height_px}" if u.width_px else "—"
            note = "; ".join(u.checks[:2]).replace("|", "/")
            lines.append(
                f"| {u.figure_id} | {u.status} | {u.h2 or '—'} | {size} | {n_lines} | "
                f"{u.signals.get('text_density', 0):.2f} | {u.signals.get('quality', 0):.2f} | {note} |"
            )

        lines += ["", "## Detail", ""]
        for u in self.units:
            lines.append(f"### `{u.figure_id}` — {u.status}")
            if u.image_path:
                lines.append(f"- File: `{u.image_path}` ({u.bytes:,} B)")
            for c in u.checks:
                lines.append(f"- {c}")
            if u.ocr_text:
                preview = " · ".join(u.ocr_text.splitlines()[:10])
                lines.append(f"- OCR ({u.ocr_backend}): {preview}")
            lines.append("")

        if self.phics_notes:
            lines += ["## PhiCS notes", ""] + list(self.phics_notes) + [""]
        if self.spectral_notes:
            lines += list(self.spectral_notes)
            if lines[-1] != "":
                lines.append("")

        lines += [
            "## How to use",
            "",
            "- Drop PNG/JPG/WebP into `screenshots/` (or pass `--folder`).",
            "- FAIL → recapture; WARN → design/QA pass (overflow, contrast, wrong screen).",
            "- Feed this report to Critic/Cursor for product copy review.",
            "- Name files with theme tokens (`login_dark.png`) so OCR can cross-check.",
            "",
        ]
        return "\n".join(lines)


def build_screen_report(
    *,
    source: str,
    units: List[FigureUnit],
    ocr_backends: List[str],
    phics_notes: List[str],
    spectral_notes: List[str] | None = None,
) -> ScreenReport:
    fails = sum(1 for u in units if u.status == "fail")
    warns = sum(1 for u in units if u.status == "warn")
    n = len(units)
    if n == 0:
        summary = "No screenshots found."
    elif fails:
        summary = f"{fails} FAIL, {warns} WARN across {n} screens — fix captures before review."
    elif warns:
        summary = f"{warns} WARN across {n} screens — review overflow/contrast/OCR mismatches."
    else:
        summary = f"All {n} screens passed UI gates."
    return ScreenReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        source=source,
        ocr_backends=ocr_backends,
        units=units,
        phics_notes=phics_notes,
        spectral_notes=spectral_notes or [],
        summary=summary,
    )
