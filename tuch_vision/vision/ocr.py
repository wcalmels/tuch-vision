#!/usr/bin/env python3
"""OCR backends with graceful degradation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class OcrResult:
    text: str
    lines: List[str]
    backend: str
    ok: bool
    error: str = ""


@lru_cache(maxsize=1)
def _rapid_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def available_backends() -> List[str]:
    out: List[str] = []
    try:
        import rapidocr_onnxruntime  # noqa: F401

        out.append("rapidocr")
    except Exception:
        pass
    try:
        import pytesseract  # noqa: F401

        out.append("tesseract")
    except Exception:
        pass
    return out


def ocr_image(path: Path, *, backend: str = "auto") -> OcrResult:
    path = Path(path)
    if not path.exists():
        return OcrResult("", [], backend, False, f"missing file: {path}")

    order: List[str]
    if backend == "auto":
        order = available_backends() or ["none"]
    else:
        order = [backend]

    last_err = ""
    for name in order:
        try:
            if name == "rapidocr":
                return _ocr_rapid(path)
            if name == "tesseract":
                return _ocr_tesseract(path)
            if name == "none":
                return OcrResult(
                    "",
                    [],
                    "none",
                    False,
                    "No OCR backend installed (pip install rapidocr-onnxruntime)",
                )
        except Exception as exc:  # noqa: BLE001
            last_err = f"{name}: {exc}"
            continue
    return OcrResult("", [], backend, False, last_err or "OCR failed")


def _ocr_rapid(path: Path) -> OcrResult:
    engine = _rapid_engine()
    result, _ = engine(str(path))
    lines = [str(item[1]).strip() for item in (result or []) if item and item[1]]
    text = "\n".join(lines)
    return OcrResult(text=text, lines=lines, backend="rapidocr", ok=True)


def _ocr_tesseract(path: Path) -> OcrResult:
    import pytesseract
    from PIL import Image

    text = pytesseract.image_to_string(Image.open(path))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return OcrResult(text="\n".join(lines), lines=lines, backend="tesseract", ok=True)


def extract_numbers(text: str) -> List[float]:
    """Pull floats like 1.599, 7.83, 10^13-ish decimal forms."""
    import re

    nums: List[float] = []
    for m in re.finditer(r"(?<![A-Za-z_])(\d+\.\d+|\d+)(?![A-Za-z_])", text.replace(",", "")):
        try:
            nums.append(float(m.group(1)))
        except ValueError:
            continue
    return nums


def number_matches(caption_nums: List[float], ocr_nums: List[float], *, rel_tol: float = 0.02) -> Tuple[List[float], List[float]]:
    """Return (matched, missing) caption numbers against OCR."""
    matched: List[float] = []
    missing: List[float] = []
    for c in caption_nums:
        hit = False
        for o in ocr_nums:
            if c == 0 and abs(o) < 1e-9:
                hit = True
                break
            if c != 0 and abs(o - c) / max(abs(c), 1e-9) <= rel_tol:
                hit = True
                break
            # also allow near-int for labels like 1.70 vs 1.7
            if abs(o - c) <= 0.05 and abs(c) < 100:
                hit = True
                break
        (matched if hit else missing).append(c)
    return matched, missing
