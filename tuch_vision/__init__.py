"""tuch-vision — manuscript vision + PhiCS health + optional spectral Φ."""

from tuch_vision.health import HealthReport, run_manuscript_health
from tuch_vision.vision import (
    FigureReport,
    ScreenReport,
    VisionAgent,
    run_screen_audit,
    run_vision_audit,
)

__all__ = [
    "VisionAgent",
    "run_vision_audit",
    "run_screen_audit",
    "FigureReport",
    "ScreenReport",
    "run_manuscript_health",
    "HealthReport",
]

__version__ = "0.1.0"
