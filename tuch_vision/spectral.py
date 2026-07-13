#!/usr/bin/env python3
"""Optional spectral Φ for manuscript / vision signal matrices."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from tuch_vision.paths import consciousai_root, phi_bridge_root


def _ensure() -> bool:
    ok = False
    for p in (phi_bridge_root(), consciousai_root()):
        if p.exists():
            s = str(p.resolve())
            if s not in sys.path:
                sys.path.insert(0, s)
            ok = True
    return phi_bridge_root().exists()


def spectral_available() -> bool:
    if not _ensure():
        return False
    try:
        import phi_bridge  # noqa: F401

        return True
    except Exception:
        return False


def score_signal_matrix(
    matrix: np.ndarray,
    *,
    row_ids: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Score a (units x channels) matrix -> phi_spectral summary (not Phi_TTH)."""
    if not _ensure():
        return {"ok": False, "error": "tuch-phi-bridge missing"}
    try:
        from phi_bridge import SpectralPhiMonitor

        mon = SpectralPhiMonitor(
            window=max(8, matrix.shape[0]),
            prefer_consciousai=True,
            consciousai_root=consciousai_root(),
        )
        r = mon.score_matrix(np.asarray(matrix, dtype=np.float64))
        return {
            "ok": True,
            "phi_spectral": r.phi_spectral,
            "phi_norm": r.phi_norm,
            "level": r.level_name,
            "alert": r.alert,
            "critical": r.critical,
            "backend": r.backend,
            "n_units": int(matrix.shape[0]),
            "n_channels": int(matrix.shape[1]),
            "note": (
                "phi_spectral = ConsciousAI-compatible integration of "
                "document signals - not Phi_TTH / Phi_crit"
            ),
            "row_ids": list(row_ids) if row_ids else [],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def markdown_section(result: Dict[str, object]) -> List[str]:
    lines = ["## Spectral Phi (ConsciousAI bridge)", ""]
    if not result.get("ok"):
        lines += [f"_Unavailable: {result.get('error')}_", ""]
        return lines
    lines += [
        f"- phi_spectral: **{float(result['phi_spectral']):.4f}**",
        f"- phi_norm: **{float(result['phi_norm']):.4f}**",
        f"- level: `{result.get('level')}` (alert={result.get('alert')}, "
        f"critical={result.get('critical')})",
        f"- backend: `{result.get('backend')}`",
        f"- matrix: {result.get('n_units')} x {result.get('n_channels')}",
        f"- _{result.get('note')}_",
        "",
    ]
    return lines
