from tuch_vision.paths import book_agent_root, phi_bridge_root, sentinel_root
from tuch_vision.vision.ui_checks import _clamp01


def test_clamp01():
    assert _clamp01(-1) == 0.0
    assert _clamp01(2) == 1.0
    assert _clamp01(0.5) == 0.5


def test_paths_point_to_desktop_siblings():
    # Soft expectations: functions return Path; siblings may or may not exist
    assert sentinel_root().name == "sentinel-edge" or "SENTINEL" in str(sentinel_root())
    assert phi_bridge_root().name == "tuch-phi-bridge" or "PHI" in str(phi_bridge_root())
    assert "book" in book_agent_root().name.lower() or book_agent_root().exists()


def test_import_package():
    import tuch_vision

    assert tuch_vision.__version__ == "0.1.0"
