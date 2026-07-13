#!/usr/bin/env python3
"""UI / screenshot-specific checks on top of base image quality + OCR."""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Tuple

from .docx_figures import FigureUnit
from .ocr import ocr_image


def run_ui_checks(unit: FigureUnit, *, do_ocr: bool = True, ocr_backend: str = "auto") -> FigureUnit:
    notes: List[str] = []
    status = "ok"

    if not unit.image_path or not unit.image_path.exists():
        unit.checks = ["FAIL: missing screenshot file"]
        unit.status = "fail"
        unit.signals = {"presence": 0.0, "ocr_ok": 0.0, "align": 0.5, "quality": 0.0, "text_density": 0.0}
        return unit

    w, h = unit.width_px, unit.height_px
    if unit.bytes < 3_000:
        notes.append("FAIL: screenshot file very small (<3KB)")
        status = "fail"
    if w < 200 or h < 200:
        notes.append("WARN: low resolution for UI review (<200px)")
        status = "warn" if status == "ok" else status
    if unit.luma_std < 4.0:
        notes.append("FAIL: near-blank / flat capture (low contrast)")
        status = "fail"
    elif unit.luma_std < 10.0:
        notes.append("WARN: low-contrast UI (hard to read / washed out)")
        status = "warn" if status == "ok" else status

    aspect = (w / h) if h else 1.0
    form = _form_factor(aspect, w, h)
    notes.append(f"viewport guess: {form} ({w}×{h}, aspect={aspect:.2f})")

    ocr_ok = 0.5
    text_density = 0.0
    align = 0.6  # screenshots rarely have captions; reuse as "UI text presence"
    if do_ocr:
        ocr = ocr_image(unit.image_path, backend=ocr_backend)
        unit.ocr_backend = ocr.backend
        unit.ocr_text = ocr.text
        if not ocr.ok:
            notes.append(f"WARN: OCR unavailable ({ocr.error})")
            status = "warn" if status == "ok" else status
            ocr_ok = 0.35
        elif not ocr.lines:
            notes.append("WARN: no OCR text — empty state, image-heavy UI, or capture issue")
            status = "warn" if status == "ok" else status
            ocr_ok = 0.4
            align = 0.35
        else:
            n_lines = len(ocr.lines)
            n_chars = sum(len(ln) for ln in ocr.lines)
            text_density = _clamp01(n_lines / 40.0)
            ocr_ok = _clamp01(0.3 + 0.02 * n_lines + 0.0005 * n_chars)
            align = _clamp01(0.4 + 0.5 * text_density)
            notes.append(f"OCR: {n_lines} lines, {n_chars} chars")

            # Truncation / overflow heuristics
            long_lines = [ln for ln in ocr.lines if len(ln) >= 48]
            if long_lines:
                notes.append(
                    f"WARN: {len(long_lines)} very long OCR line(s) — possible overflow/ellipsis"
                )
                status = "warn" if status != "fail" else status
                align *= 0.85

            # Repeated labels (stuck toast / duplicate widgets)
            counts = Counter(_normalize_label(ln) for ln in ocr.lines if len(ln.strip()) >= 4)
            dups = [(lab, c) for lab, c in counts.items() if c >= 3 and lab]
            if dups:
                top = ", ".join(f"'{a}'×{c}" for a, c in sorted(dups, key=lambda x: -x[1])[:3])
                notes.append(f"WARN: repeated UI strings ({top}) — check overlays/stacks")
                status = "warn" if status != "fail" else status

            # Error/crash cues
            blob = " ".join(ocr.lines).lower()
            for needle, tag in (
                ("exception", "exception"),
                ("traceback", "traceback"),
                ("fatal error", "fatal error"),
                ("not responding", "not responding"),
                ("404", "404"),
                ("500", "500"),
                ("access denied", "access denied"),
            ):
                if needle in blob:
                    notes.append(f"WARN: OCR mentions '{tag}'")
                    status = "warn" if status != "fail" else status
                    break

            # Expected tokens from filename (settings, login, dashboard…)
            hits, expected = _filename_token_hits(unit.figure_id or unit.caption, ocr.text)
            if expected:
                notes.append(f"filename token hits in OCR: {hits}/{len(expected)} ({expected[:5]})")
                if hits == 0:
                    notes.append("WARN: filename theme not found in OCR (wrong screen or bad capture?)")
                    status = "warn" if status != "fail" else status
                    align *= 0.7
                else:
                    align = _clamp01(align + 0.15)

    quality = _clamp01((unit.luma_std / 45.0) * 0.55 + (min(w, 1920) / 1920) * 0.45)
    presence = 1.0  # screenshots are the artifact

    if not notes:
        notes.append("OK: UI capture gates passed")

    unit.checks = notes
    unit.status = status
    unit.signals = {
        "presence": presence,
        "ocr_ok": float(ocr_ok),
        "align": float(align),
        "quality": float(quality),
        "text_density": float(text_density),
    }
    # stash form for report
    unit.h2 = form
    return unit


def _form_factor(aspect: float, w: int, h: int) -> str:
    if aspect < 0.7:
        return "mobile-portrait"
    if aspect < 0.95:
        return "tablet-portrait"
    if aspect <= 1.1:
        return "square"
    if aspect < 1.6:
        return "laptop-landscape"
    if w >= 1600:
        return "desktop-wide"
    return "landscape"


def _normalize_label(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())[:80]


def _filename_token_hits(name: str, ocr_text: str) -> Tuple[int, List[str]]:
    stop = {
        "screen", "screenshot", "ui", "mock", "shot", "img", "image", "png", "jpg",
        "capture", "window", "app", "page", "view", "final", "new", "old", "v1", "v2",
    }
    tokens = [t for t in re.findall(r"[A-Za-z]{3,}", name or "") if t.lower() not in stop]
    # de-dupe preserve order
    seen = set()
    expected: List[str] = []
    for t in tokens:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            expected.append(t)
        if len(expected) >= 8:
            break
    ocr_l = (ocr_text or "").lower()
    hits = sum(1 for t in expected if t.lower() in ocr_l)
    return hits, expected


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))
