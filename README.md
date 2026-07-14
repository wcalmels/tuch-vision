# tuch-vision

**Manuscript agents** for *any* book or long-form document: vision/OCR of figures, screenshot QA, and PhiCS health on chapter progress.

A specific theory (e.g. TTH) is an optional **profile**, not the product.

## Idea

| Layer | Job |
|-------|-----|
| Vision | Figures + captions in any DOCX / folder |
| Screens | UI captures for companion apps / sites |
| TOC | Audit / Word field / static rebuild from Headings |
| Health | Outline fill / approval / promises → local PhiCS |
| Spectral (optional) | Integration of signal matrices (`phi_spectral`) |

Writing (director/writer/critic) can live in Cursor or a private agent repo. This package is the **perception + health** slice you reuse across manuscripts.

## Install

```bash
pip install -e .
pip install -e ".[ocr]"
```

## Start a manuscript (generic)

```bash
tuch-vision init ./my-book --name "My Book"
cd my-book
# edit state/style_guide.md, state/constraints.md, drafts/
tuch-vision health --project .
tuch-vision figures --folder ./figures --project .
tuch-vision screens ./screenshots --project .
tuch-vision toc --docx ./book.docx
```

Theory-specific OCR soft priors (example only):

```bash
tuch-vision init ./tth-draft --name "TTH" \
  --hints-from ../tuch-vision/examples/profiles/tth/hints.json
```

## CLI

```bash
tuch-vision init PATH --name "..."
tuch-vision figures --docx book.docx [--project .]
tuch-vision figures --folder ./figures --no-phics
tuch-vision screens ./screenshots [--project .]
tuch-vision health [--project .] [--outline ...]
tuch-vision toc --docx book.docx                 # audit manual TOC vs Headings
tuch-vision toc --docx book.docx --replace --output-docx book_toc.docx
tuch-vision toc --docx book.docx --rebuild-static --output-docx book_toc.docx
```

After `--replace`, open the file in Word and **Update Field** (`Ctrl+A`, `F9`) so page numbers appear.

## Profile (`manuscript.toml`)

```toml
[project]
name = "My Book"
language = "en"

[paths]
outline = "state/manuscript_outline.json"
drafts = "drafts"
approved = "approved"
figures = "figures"
screenshots = "screenshots"

[vision]
ocr_hints = []   # optional domain numbers/tokens
```

## Vocabulary

| Tag | Meaning |
|-----|---------|
| OCR / vision checks | Capture + caption hygiene |
| PhiCS fidelity | Local familiarity vs baselines (`sentinel-edge`) |
| `phi_spectral` | Matrix integration (`tuch-phi-bridge`) — not a science constant |

Sibling overrides: `BOOK_AGENT_ROOT`, `TUCH_SENTINEL_ROOT`, `TUCH_PHI_BRIDGE_ROOT`, `CONSCIOUSAI_ROOT`.

## Tech report

[`docs/paper/tuch_vision_draft.md`](docs/paper/tuch_vision_draft.md)

## License

MIT
