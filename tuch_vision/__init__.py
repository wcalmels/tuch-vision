"""tuch-vision — manuscript agents for any book."""

from tuch_vision.health import HealthReport, run_manuscript_health
from tuch_vision.profile import ManuscriptProfile, init_manuscript, load_profile
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
    "ManuscriptProfile",
    "load_profile",
    "init_manuscript",
]

__version__ = "0.2.0"
