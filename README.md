# tuch-vision

Local-first **manuscript vision + PhiCS health + optional spectral Φ**.

Extracted from the Book Agent line (figures/screens/health) into a public package so it stands next to `sentinel-edge` and `tuch-phi-bridge` — without shipping private drafts or Anthropic writers.

## Vocabulary

| Tag | Meaning |
|-----|---------|
| OCR / vision checks | Figure & screenshot quality |
| PhiCS fidelity | Local associative familiarity (`sentinel-edge`) |
| `phi_spectral` | ConsciousAI-compatible matrix integration (`tuch-phi-bridge`) |
| `Phi_TTH` | Book theory only — **never equated** here |

## Layout (Desktop siblings)

```text
Escritorio/
  tuch-vision/        ← this repo
  book_agent/         ← optional outline/drafts for `health`
  sentinel-edge/      ← PhiCS
  tuch-phi-bridge/    ← spectral Φ
  consciousai/        ← optional preferred math
```

Overrides: `BOOK_AGENT_ROOT`, `TUCH_SENTINEL_ROOT`, `TUCH_PHI_BRIDGE_ROOT`, `CONSCIOUSAI_ROOT`.

## Install

```bash
pip install -e .
pip install -e ".[ocr]"
```

## CLI

```bash
tuch-vision figures --docx book.docx
tuch-vision figures --folder ./figures --no-phics
tuch-vision screens ./screenshots --no-ocr
tuch-vision health --outline path/to/manuscript_outline.json
```

## Library

```python
from pathlib import Path
from tuch_vision import run_vision_audit, run_screen_audit, run_manuscript_health
```

## What stays in `book_agent`

Writer/director/critic prompts, drafts, Anthropic automation, TTH build scripts. This repo is the **perception + health** slice.

## Tech report

[`docs/paper/tuch_vision_draft.md`](docs/paper/tuch_vision_draft.md)

## License

MIT
