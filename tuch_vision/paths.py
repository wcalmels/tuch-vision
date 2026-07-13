"""Sibling repo path resolution (Desktop layout or env overrides)."""

from __future__ import annotations

import os
from pathlib import Path

# tuch-vision/tuch_vision/paths.py → parents[2] = Escritorio
_DESKTOP = Path(__file__).resolve().parents[2]


def sentinel_root() -> Path:
    env = os.environ.get("TUCH_SENTINEL_ROOT") or os.environ.get("SENTINEL_EDGE")
    if env:
        return Path(env)
    return _DESKTOP / "sentinel-edge"


def phi_bridge_root() -> Path:
    env = os.environ.get("TUCH_PHI_BRIDGE_ROOT")
    if env:
        return Path(env)
    return _DESKTOP / "tuch-phi-bridge"


def consciousai_root() -> Path:
    env = os.environ.get("CONSCIOUSAI_ROOT")
    if env:
        return Path(env)
    return _DESKTOP / "consciousai"


def book_agent_root() -> Path:
    env = os.environ.get("BOOK_AGENT_ROOT")
    if env:
        return Path(env)
    return _DESKTOP / "book_agent"
