#!/usr/bin/env python3
"""Extract figures and captions from DOCX in document order."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from PIL import Image

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

FIGURE_ID_RE = re.compile(r"Figure\s+([0-9A]+)\.(\d+)\b", re.I)
NUMBERED_CAP_RE = re.compile(r"^Figure\s+[0-9A]+\.\d+\b", re.I)
CONCEPTUAL_CAP_RE = re.compile(r"^Figure\s+(\(|S|[IVX]+-)", re.I)


@dataclass
class FigureUnit:
    figure_id: str  # e. and "13.1" or "A.1" or "orphan_img_3"
    kind: str  # image | caption_only | conceptual
    image_path: Optional[Path] = None
    caption: str = ""
    h1: str = ""
    h2: str = ""
    width_px: int = 0
    height_px: int = 0
    bytes: int = 0
    mean_luma: float = 0.0
    luma_std: float = 0.0
    checks: List[str] = field(default_factory=list)
    status: str = "ok"  # ok | warn | fail
    ocr_text: str = ""
    ocr_backend: str = ""
    signals: dict = field(default_factory=dict)


def _para_text(p: ET.Element) -> str:
    return "".join((t.text or "") for t in p.iter(f"{W}t")).strip()


def _heading_level(p: ET.Element) -> Optional[int]:
    p_pr = p.find(f"{W}pPr")
    if p_pr is None:
        return None
    style = p_pr.find(f"{W}pStyle")
    if style is None:
        return None
    val = style.get(f"{W}val") or ""
    m = re.search(r"(\d+)", val)
    if val.lower().startswith("heading") and m:
        return int(m.group(1))
    return None


def figure_key(text: str) -> Optional[str]:
    m = FIGURE_ID_RE.search(text)
    if not m:
        return None
    return f"{m.group(1).upper()}.{m.group(2)}"


def _image_stats(path: Path) -> tuple[int, int, int, float, float]:
    data = path.read_bytes()
    with Image.open(path) as im:
        w, h = im.size
        gray = im.convert("L")
        # sample for speed
        gray = gray.resize((min(w, 320), max(1, int(min(w, 320) * h / max(w, 1)))))
        import statistics

        pixels = list(gray.getdata())
        mean = float(statistics.fmean(pixels)) if pixels else 0.0
        std = float(statistics.pstdev(pixels)) if len(pixels) > 1 else 0.0
    return w, h, len(data), mean, std


def extract_docx_figures(docx_path: Path, work_dir: Optional[Path] = None) -> List[FigureUnit]:
    """
    Walk DOCX body; pair each embedded image with the following numbered caption
    when present. Conceptual captions (no image) are recorded separately.
    """
    docx_path = Path(docx_path)
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="vision_figs_"))
    else:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

    with ZipFile(docx_path) as z:
        media_names = [n for n in z.namelist() if n.startswith("word/media/")]
        for n in media_names:
            (work_dir / Path(n).name).write_bytes(z.read(n))
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
        doc_xml = z.read("word/document.xml")

    rid_map: dict[str, str] = {}
    for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels):
        rid, tgt = m.group(1), m.group(2)
        if "media/" in tgt:
            rid_map[rid] = Path(tgt).name

    root = ET.fromstring(doc_xml)
    body = root.find(f"{W}body")
    assert body is not None

    events: List[tuple] = []
    last_h1 = last_h2 = ""
    for p in body.iter(f"{W}p"):
        hl = _heading_level(p)
        tx = _para_text(p)
        if hl == 1 and tx:
            last_h1 = tx
        if hl == 2 and tx:
            last_h2 = tx
        blips = list(p.iter(f"{A}blip"))
        if blips:
            for b in blips:
                emb = b.get(f"{R}embed")
                fname = rid_map.get(emb or "", "")
                events.append(("img", fname, last_h1, last_h2, ""))
            continue
        if tx and NUMBERED_CAP_RE.match(tx):
            events.append(("cap", "", last_h1, last_h2, tx))
        elif tx and CONCEPTUAL_CAP_RE.match(tx):
            events.append(("conceptual", "", last_h1, last_h2, tx))

    units: List[FigureUnit] = []
    i = 0
    orphan_n = 0
    while i < len(events):
        kind, fname, h1, h2, caption = events[i]
        if kind == "img":
            path = work_dir / fname if fname else None
            cap = ""
            fid = ""
            if i + 1 < len(events) and events[i + 1][0] == "cap":
                cap = events[i + 1][4]
                fid = figure_key(cap) or ""
                i += 2
            else:
                orphan_n += 1
                fid = f"orphan_img_{orphan_n}"
                i += 1
            unit = FigureUnit(figure_id=fid or f"img_{orphan_n}", kind="image", caption=cap, h1=h1, h2=h2)
            if path and path.exists():
                unit.image_path = path
                unit.width_px, unit.height_px, unit.bytes, unit.mean_luma, unit.luma_std = _image_stats(path)
            units.append(unit)
            continue
        if kind == "cap":
            fid = figure_key(caption) or f"orphan_cap_{i}"
            units.append(
                FigureUnit(figure_id=fid, kind="caption_only", caption=caption, h1=h1, h2=h2)
            )
            i += 1
            continue
        if kind == "conceptual":
            units.append(
                FigureUnit(
                    figure_id=figure_key(caption) or f"conceptual_{i}",
                    kind="conceptual",
                    caption=caption,
                    h1=h1,
                    h2=h2,
                )
            )
            i += 1
            continue
        i += 1
    return units


def load_folder_images(folder: Path) -> List[FigureUnit]:
    """Treat a folder of PNGs as figure units (caption = filename stem)."""
    folder = Path(folder)
    units: List[FigureUnit] = []
    for path in sorted(folder.glob("*.png")) + sorted(folder.glob("*.jpg")):
        m = re.search(r"(?:fig|figure|image)?_?(\d+)", path.stem, re.I)
        fid = m.group(1) if m else path.stem
        unit = FigureUnit(figure_id=str(fid), kind="image", image_path=path, caption=path.stem)
        unit.width_px, unit.height_px, unit.bytes, unit.mean_luma, unit.luma_std = _image_stats(path)
        units.append(unit)
    return units
