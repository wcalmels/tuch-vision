import json
from pathlib import Path

from tuch_vision import __version__
from tuch_vision.profile import init_manuscript, load_profile
from tuch_vision.vision.checks import run_checks
from tuch_vision.vision.docx_figures import FigureUnit


def test_version():
    assert __version__ == "0.2.0"


def test_init_and_profile(tmp_path: Path):
    root = tmp_path / "book"
    init_manuscript(root, name="Demo Book", ocr_hints=["alpha"])
    prof = load_profile(root)
    assert prof.name == "Demo Book"
    assert "alpha" in prof.ocr_hints
    assert (root / "state" / "manuscript_outline.json").exists()
    outline = json.loads((root / "state" / "manuscript_outline.json").read_text(encoding="utf-8"))
    assert outline["title"] == "Demo Book"


def test_checks_without_tth_hints():
    # conceptual unit should not require any theory priors
    u = FigureUnit(
        figure_id="c1",
        kind="conceptual",
        caption="A conceptual diagram",
    )
    out = run_checks(u, do_ocr=False, ocr_hints=None)
    assert out.status == "ok"
