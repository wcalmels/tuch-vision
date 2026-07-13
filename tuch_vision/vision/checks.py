#!/usr/bin/env python3
"""Structural + OCR consistency checks for figure units."""

from __future__ import annotations

import re
from typing import List

from .docx_figures import FigureUnit
from .ocr import extract_numbers, number_matches, ocr_image


# Numbers that often appear in TTH/AoE captions — soft prior for OCR alignment
CANONICAL_HINTS = {
    "1.599",
    "0.4009",
    "7.83",
    "76",
    "δ_F",
    "Phi",
    "Φ",
}


def run_checks(unit: FigureUnit, *, do_ocr: bool = True, ocr_backend: str = "auto") -> FigureUnit:
    notes: List[str] = []
    status = "ok"

    if unit.kind == "conceptual":
        notes.append("conceptual caption (no embedded artwork expected)")
        unit.checks = notes
        unit.status = "ok"
        unit.signals = {"presence": 1.0, "ocr_ok": 1.0, "align": 1.0, "quality": 1.0}
        return unit

    if unit.kind == "caption_only":
        notes.append("FAIL: numbered caption without preceding image")
        unit.checks = notes
        unit.status = "fail"
        unit.signals = {"presence": 0.0, "ocr_ok": 0.0, "align": 0.0, "quality": 0.0}
        return unit

    # image unit
    if not unit.image_path or not unit.image_path.exists():
        notes.append("FAIL: missing image file")
        unit.status = "fail"
        unit.checks = notes
        unit.signals = {"presence": 0.0, "ocr_ok": 0.0, "align": 0.0, "quality": 0.0}
        return unit

    if not unit.caption:
        notes.append("WARN: image without following numbered caption")
        status = "warn"

    if unit.bytes < 2_000:
        notes.append("FAIL: image file very small (<2KB)")
        status = "fail"
    if unit.width_px < 80 or unit.height_px < 40:
        notes.append("WARN: unusually small pixel dimensions")
        status = "warn" if status == "ok" else status
    if unit.luma_std < 4.0:
        notes.append("FAIL: near-blank / flat image (low contrast)")
        status = "fail"
    elif unit.luma_std < 12.0:
        notes.append("WARN: low-contrast image")
        status = "warn" if status == "ok" else status

    ocr_ok = 1.0
    align = 1.0
    if do_ocr:
        ocr = ocr_image(unit.image_path, backend=ocr_backend)
        unit.ocr_backend = ocr.backend
        unit.ocr_text = ocr.text
        if not ocr.ok:
            notes.append(f"WARN: OCR unavailable ({ocr.error})")
            status = "warn" if status == "ok" else status
            ocr_ok = 0.4
            align = 0.5
        elif not ocr.lines:
            notes.append("WARN: OCR returned no text (diagram may be purely graphical)")
            status = "warn" if status == "ok" else status
            ocr_ok = 0.5
            align = 0.6 if unit.caption else 0.5
        else:
            ocr_ok = min(1.0, 0.35 + 0.08 * len(ocr.lines))
            if unit.caption:
                align = _caption_alignment(unit.caption, ocr.text, notes)
                if align < 0.45:
                    status = "warn" if status != "fail" else status

    quality = _clamp01((unit.luma_std / 40.0) * 0.6 + (min(unit.width_px, 1600) / 1600) * 0.4)
    presence = 1.0 if unit.caption else 0.55

    if not notes:
        notes.append("OK: structure + quality gates passed")

    unit.checks = notes
    unit.status = status
    unit.signals = {
        "presence": presence,
        "ocr_ok": float(ocr_ok),
        "align": float(align),
        "quality": float(quality),
    }
    return unit


def _caption_alignment(caption: str, ocr_text: str, notes: List[str]) -> float:
    cap_nums = [n for n in extract_numbers(caption) if n >= 0.1]  # skip lonely zeros
    # Drop obvious figure ids like 13.1 / 9.2 if they dominate — keep scientific values
    # Heuristic: figure id is at start "Figure X.Y"
    m = re.match(r"Figure\s+([0-9A]+)\.(\d+)", caption, re.I)
    id_num = None
    if m and m.group(1).isdigit():
        id_num = float(f"{m.group(1)}.{m.group(2)}")
    sci_nums = [n for n in cap_nums if id_num is None or abs(n - id_num) > 1e-9]

    ocr_nums = extract_numbers(ocr_text)
    score = 0.7
    if sci_nums:
        matched, missing = number_matches(sci_nums, ocr_nums)
        if matched:
            notes.append(f"OCR matches caption numbers: {matched}")
        if missing:
            notes.append(f"WARN: caption numbers not seen in OCR: {missing}")
            score = 0.35 if not matched else 0.55
        else:
            score = 0.95 if matched else 0.7

    # keyword overlap (axis labels, state names)
    tokens = _keywords(caption)
    ocr_l = ocr_text.lower()
    hits = [t for t in tokens if t.lower() in ocr_l]
    if tokens:
        frac = len(hits) / len(tokens)
        notes.append(f"caption keyword hits in OCR: {len(hits)}/{len(tokens)} ({hits[:6]})")
        score = 0.5 * score + 0.5 * (0.3 + 0.7 * frac)
    return float(_clamp01(score))


def _keywords(caption: str) -> List[str]:
    stop = {
        "the", "a", "an", "of", "and", "with", "from", "into", "for", "to", "in",
        "on", "is", "are", "at", "by", "as", "or", "figure", "vs", "versus",
    }
    words = re.findall(r"[A-Za-zΦδ_]{3,}", caption)
    out = []
    for w in words:
        if w.lower() in stop:
            continue
        if w not in out:
            out.append(w)
    return out[:12]


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))
