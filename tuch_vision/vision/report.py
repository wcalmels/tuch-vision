#!/usr/bin/env python3
"""Markdown report for VisionAgent audits."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from .docx_figures import FigureUnit


@dataclass
class FigureReport:
    generated_at: str
    source: str
    ocr_backends: List[str]
    units: List[FigureUnit]
    phics_notes: List[str] = field(default_factory=list)
    spectral_notes: List[str] = field(default_factory=list)
    summary: str = ""

    def to_markdown(self) -> str:
        imgs = [u for u in self.units if u.kind == "image"]
        caps = [u for u in self.units if u.kind == "caption_only"]
        conceptual = [u for u in self.units if u.kind == "conceptual"]
        fails = [u for u in self.units if u.status == "fail"]
        warns = [u for u in self.units if u.status == "warn"]

        lines = [
            "# Vision / OCR Figure Audit",
            "",
            f"Generated: {self.generated_at}",
            f"Source: `{self.source}`",
            f"OCR backends available: {', '.join(self.ocr_backends) or 'none'}",
            "",
            f"**Summary:** {self.summary}",
            "",
            "## Counts",
            "",
            f"- Images audited: **{len(imgs)}**",
            f"- Orphan captions (no image): **{len(caps)}**",
            f"- Conceptual captions (text-only): **{len(conceptual)}**",
            f"- FAIL: **{len(fails)}** · WARN: **{len(warns)}** · OK: **{len(self.units) - len(fails) - len(warns)}**",
            "",
            "## Figures",
            "",
            "| ID | Status | Size | OCR lines | Presence | Align | Notes |",
            "|----|--------|------|----------:|---------:|------:|-------|",
        ]
        for u in imgs:
            n_lines = len([ln for ln in (u.ocr_text or "").splitlines() if ln.strip()])
            size = f"{u.width_px}×{u.height_px}" if u.width_px else "—"
            note = "; ".join(u.checks[:2]).replace("|", "/")
            lines.append(
                f"| {u.figure_id} | {u.status} | {size} | {n_lines} | "
                f"{u.signals.get('presence', 0):.2f} | {u.signals.get('align', 0):.2f} | {note} |"
            )

        if caps:
            lines += ["", "## Orphan captions", ""]
            for u in caps:
                lines.append(f"- **{u.figure_id}** — {u.caption[:160]}")

        if conceptual:
            lines += ["", "## Conceptual (no artwork expected)", ""]
            for u in conceptual[:20]:
                lines.append(f"- {u.caption[:140]}")
            if len(conceptual) > 20:
                lines.append(f"- … +{len(conceptual) - 20} more")

        lines += ["", "## Per-figure detail", ""]
        for u in imgs:
            lines.append(f"### Figure {u.figure_id} — `{u.status}`")
            if u.h1:
                lines.append(f"- Section: {u.h1}" + (f" / {u.h2}" if u.h2 else ""))
            if u.caption:
                lines.append(f"- Caption: {u.caption}")
            if u.image_path:
                lines.append(f"- File: `{u.image_path.name}` ({u.bytes:,} B)")
            for c in u.checks:
                lines.append(f"- {c}")
            if u.ocr_text:
                preview = " · ".join(u.ocr_text.splitlines()[:8])
                lines.append(f"- OCR ({u.ocr_backend}): {preview}")
            lines.append("")

        if self.phics_notes:
            lines += ["## PhiCS notes", ""]
            lines.extend(self.phics_notes)
            lines.append("")

        if self.spectral_notes:
            lines += self.spectral_notes
            if not lines[-1].endswith("\n") and lines[-1] != "":
                lines.append("")

        lines += [
            "## How to use",
            "",
            "- FAIL → fix export / re-insert figure before submission.",
            "- WARN with missing caption numbers → check OCR misfires or wrong image under caption.",
            "- Feed this report to any editorial / Cursor critic for prose-level review.",
            "- `phi_spectral` is an integration summary of quality channels — not a theory constant.",
            "",
        ]
        return "\n".join(lines)


def build_report(
    *,
    source: str,
    units: List[FigureUnit],
    ocr_backends: List[str],
    phics_notes: List[str],
    spectral_notes: List[str] | None = None,
) -> FigureReport:
    fails = sum(1 for u in units if u.status == "fail")
    warns = sum(1 for u in units if u.status == "warn")
    imgs = sum(1 for u in units if u.kind == "image")
    if fails:
        summary = f"{fails} FAIL, {warns} WARN across {imgs} images — block publish until FAILs clear."
    elif warns:
        summary = f"{warns} WARN across {imgs} images — review OCR/caption mismatches."
    else:
        summary = f"All {imgs} images passed structural gates."

    return FigureReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        source=source,
        ocr_backends=ocr_backends,
        units=units,
        phics_notes=phics_notes,
        spectral_notes=spectral_notes or [],
        summary=summary,
    )
