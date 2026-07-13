#!/usr/bin/env python3
"""Load UI screenshots from a folder for VisionAgent audit."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .docx_figures import FigureUnit, _image_stats

_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def load_screenshots(folder: Path, *, recursive: bool = False) -> List[FigureUnit]:
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(folder)
    paths: List[Path] = []
    if recursive:
        for p in sorted(folder.rglob("*")):
            if p.is_file() and p.suffix.lower() in _EXTS:
                paths.append(p)
    else:
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix.lower() in _EXTS:
                paths.append(p)

    units: List[FigureUnit] = []
    for path in paths:
        # id = relative stem for stable naming
        try:
            rel = path.relative_to(folder)
            fid = str(rel.with_suffix("")).replace("\\", "/")
        except ValueError:
            fid = path.stem
        unit = FigureUnit(
            figure_id=fid,
            kind="image",
            image_path=path,
            caption=path.stem.replace("_", " ").replace("-", " "),
            h1="UI screenshot",
        )
        unit.width_px, unit.height_px, unit.bytes, unit.mean_luma, unit.luma_std = _image_stats(path)
        units.append(unit)
    return units
