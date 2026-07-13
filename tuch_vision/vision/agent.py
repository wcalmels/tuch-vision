#!/usr/bin/env python3
"""VisionAgent — figure audit with optional PhiCS scoring."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .checks import run_checks
from .docx_figures import FigureUnit, extract_docx_figures, load_folder_images
from .ocr import available_backends
from .report import FigureReport, build_report
from .screen_report import ScreenReport, build_screen_report
from .screens import load_screenshots
from .ui_checks import run_ui_checks


ROOT = Path(__file__).resolve().parents[2]  # tuch-vision repo root
DEFAULT_SENTINEL = None  # resolved lazily via paths.sentinel_root()


@dataclass
class VisionAgent:
    """
    Local-first vision/OCR auditor for manuscripts and UI screenshots.

    observe → check → (optional PhiCS process) → report
    Does not call cloud LLMs; Cursor/Critic can consume the markdown report.
    """

    name: str = "VisionAgent"
    do_ocr: bool = True
    ocr_backend: str = "auto"
    use_phics: bool = True
    sentinel_root: Optional[Path] = None
    work_dir: Optional[Path] = None
    verbose: bool = True
    ocr_hints: Optional[List[str]] = None
    units: List[FigureUnit] = field(default_factory=list)
    phics_notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.sentinel_root is None:
            from tuch_vision.paths import sentinel_root as _sr

            self.sentinel_root = _sr()

    def audit_docx(self, docx_path: Path) -> FigureReport:
        if self.work_dir is None:
            self.work_dir = ROOT / "output" / "vision_work" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.units = extract_docx_figures(Path(docx_path), self.work_dir)
        return self._finish(source=str(docx_path))

    def audit_folder(self, folder: Path) -> FigureReport:
        self.units = load_folder_images(Path(folder))
        return self._finish(source=str(folder))

    def audit_screens(self, folder: Path, *, recursive: bool = False) -> ScreenReport:
        self.name = "UIVisionAgent"
        self.units = load_screenshots(Path(folder), recursive=recursive)
        return self._finish_screens(source=str(folder))

    def _finish(self, source: str) -> FigureReport:
        backends = available_backends()
        if self.verbose:
            print(f"  [{self.name}] OCR backends: {backends or ['none']}")
            print(f"  [{self.name}] Units: {len(self.units)}")

        for u in self.units:
            run_checks(
                u,
                do_ocr=self.do_ocr,
                ocr_backend=self.ocr_backend,
                ocr_hints=self.ocr_hints,
            )
            if self.verbose and u.kind == "image":
                print(
                    f"  [{self.name}] Figure {u.figure_id:>6}  {u.status:4}  "
                    f"{u.width_px}x{u.height_px}  checks={len(u.checks)}"
                )

        if self.use_phics:
            self.phics_notes = self._score_phics()

        spectral_notes = self._score_spectral()

        return build_report(
            source=source,
            units=self.units,
            ocr_backends=backends,
            phics_notes=self.phics_notes,
            spectral_notes=spectral_notes,
        )

    def _finish_screens(self, source: str) -> ScreenReport:
        backends = available_backends()
        if self.verbose:
            print(f"  [{self.name}] OCR backends: {backends or ['none']}")
            print(f"  [{self.name}] Screens: {len(self.units)}")

        for u in self.units:
            run_ui_checks(u, do_ocr=self.do_ocr, ocr_backend=self.ocr_backend)
            if self.verbose:
                print(
                    f"  [{self.name}] {u.figure_id[:32]:<32}  {u.status:4}  "
                    f"{u.width_px}x{u.height_px}  {u.h2 or ''}"
                )

        if self.use_phics:
            self.phics_notes = self._score_phics(label="screen")
        spectral_notes = self._score_spectral(channels=["presence", "ocr_ok", "align", "quality", "text_density"])

        return build_screen_report(
            source=source,
            units=self.units,
            ocr_backends=backends,
            phics_notes=self.phics_notes,
            spectral_notes=spectral_notes,
        )

    def _score_spectral(self, channels: Optional[List[str]] = None) -> List[str]:
        images = [u for u in self.units if u.kind == "image" and u.signals]
        if len(images) < 3:
            return ["## Spectral Φ (ConsciousAI bridge)", "", "_Need ≥3 scored images._", ""]
        try:
            import numpy as np
            from tuch_vision.spectral import markdown_section, score_signal_matrix

            chans = channels or ["presence", "ocr_ok", "align", "quality"]
            mat = np.array(
                [[float(u.signals.get(ch, 0.5)) for ch in chans] for u in images],
                dtype=float,
            )
            sp = score_signal_matrix(mat, row_ids=[u.figure_id for u in images])
            return markdown_section(sp)
        except Exception as exc:  # noqa: BLE001
            return ["## Spectral Φ (ConsciousAI bridge)", "", f"_Skipped: {exc}_", ""]

    def _score_phics(self, label: str = "figure") -> List[str]:
        notes: List[str] = []
        try:
            root = str(self.sentinel_root.resolve())
            if root not in sys.path:
                sys.path.insert(0, root)
            from agent.local_phics import LocalPhiCSEngine  # type: ignore
        except Exception as exc:  # noqa: BLE001
            return [f"PhiCS skipped ({exc})"]

        images = [u for u in self.units if u.kind == "image" and u.signals]
        if len(images) < 2:
            return [f"PhiCS skipped (need ≥2 scored {label}s)"]

        import statistics

        channels = [c for c in ("presence", "ocr_ok", "align", "quality", "text_density") if any(c in u.signals for u in images)]
        if not channels:
            channels = ["presence", "ocr_ok", "align", "quality"]
        baselines: Dict[str, float] = {}
        for ch in channels:
            vals = [float(u.signals.get(ch, 0.5)) for u in images]
            baselines[ch] = float(statistics.median(vals))

        cortex = LocalPhiCSEngine()
        for ch, base in baselines.items():
            cortex.learn(f"normal_{ch}", [base], "generic")

        weak: List[str] = []
        for u in images:
            scores = []
            for ch in channels:
                v = float(u.signals.get(ch, 0.5))
                r = cortex.process([v], "generic", label=ch) or {}
                fid = float(r.get("fidelity", 1.0))
                anom = float(r.get("anomaly_score", 0.0))
                scores.append((ch, fid, anom))
            mean_fid = sum(s[1] for s in scores) / len(scores)
            max_anom = max(s[2] for s in scores)
            u.signals["phics_fid"] = mean_fid
            u.signals["phics_anom"] = max_anom
            if mean_fid < 0.97 or max_anom > 0.05 or u.status != "ok":
                weak.append(
                    f"{label} {u.figure_id}: fid={mean_fid:.4f} anom={max_anom:.4f} status={u.status}"
                )

        notes.append(
            "PhiCS baselines (median): "
            + ", ".join(f"{k}={v:.3f}" for k, v in baselines.items())
        )
        if weak:
            notes.append(f"Weak / flagged {label}s ({len(weak)}):")
            notes.extend(f"  - {w}" for w in weak[:12])
        else:
            notes.append(f"PhiCS: no weak {label}s beyond status gates.")
        return notes


def run_vision_audit(
    *,
    docx: Optional[Path] = None,
    folder: Optional[Path] = None,
    do_ocr: bool = True,
    use_phics: bool = True,
    verbose: bool = True,
    ocr_hints: Optional[List[str]] = None,
) -> FigureReport:
    agent = VisionAgent(
        do_ocr=do_ocr,
        use_phics=use_phics,
        verbose=verbose,
        ocr_hints=ocr_hints,
    )
    if docx:
        return agent.audit_docx(Path(docx))
    if folder:
        return agent.audit_folder(Path(folder))
    raise ValueError("Provide docx= or folder=")


def run_screen_audit(
    *,
    folder: Path,
    recursive: bool = False,
    do_ocr: bool = True,
    use_phics: bool = True,
    verbose: bool = True,
) -> ScreenReport:
    agent = VisionAgent(do_ocr=do_ocr, use_phics=use_phics, verbose=verbose)
    return agent.audit_screens(Path(folder), recursive=recursive)