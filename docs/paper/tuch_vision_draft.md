# Book-facing vision agents with PhiCS health and spectral Φ

**Tech report (draft v0.1)**  
Walter Calmels / TUCH  
Artifact: [tuch-vision](https://github.com/wcalmels/tuch-vision)  
Date: 2026-07-13  

> Companion paper to Sentinel Edge and unicornio-screens.  
> Domain: **manuscripts + figure/UI captures**, not industrial I/O loops.

---

## Abstract

Long-form scientific books accumulate figures, captions, and chapter progress signals that are hard to QA by hand. We extract a local-first stack — **OCR vision audits** for DOCX figures and UI screenshots, **PhiCS manuscript health** from outline/file signals, and optional **spectral Φ** over signal matrices — into `tuch-vision`. The stack remains vocabulary-disciplined (`phi_spectral` ≠ PhiCS fidelity ≠ `Phi_TTH`) and depends optionally on sibling `sentinel-edge` / `tuch-phi-bridge`. Writing agents (Anthropic/Cursor) stay in private `book_agent`; this package is the reproducible perception layer.

## 1. Motivation

Book pipelines mix three monitoring problems:

1. **Visual fidelity of figures** (blank panels, caption mismatch, OCR vs expected symbols).  
2. **Structural health of chapters** (fill, approval, broken promises) as numeric channels.  
3. **Cross-unit integration** of those channels (spectral summary).

Cloud VLMs can help, but offline OCR + local PhiCS already catch many defects before a human or LLM review.

## 2. Architecture

```text
DOCX / image folder / screenshots
        │
        ▼
   VisionAgent (OCR + checks + UI checks)
        │
        ├── optional LocalPhiCS on per-unit signals
        └── optional phi_spectral on signal matrix

manuscript_outline.json + drafts/approved
        │
        ▼
   signals.py → chapter channels
        │
        ▼
   PhiCSBackend + SensorPolicy (+ DialogAgent notes)
        └── optional spectral section
```

## 3. Commands

`tuch-vision figures|screens|health` — see README.

## 4. Relation to other papers

| Artifact | Domain |
|----------|--------|
| unicornio-screens | Product UI screenshot gates |
| sentinel-edge | Industrial sensors + dual gate |
| **tuch-vision** | Book figures + manuscript health |

## 5. Claim discipline

Allowed: offline figure/screenshot hygiene; outline-derived PhiCS health demos.  
Disallowed: equating manuscript PhiCS scores with consciousness or `Phi_TTH`.

## 6. Future work

Real TTH figure regression suite; human labels; CI; thin re-export wrappers inside `book_agent`.

## Citation

```bibtex
@techreport{calmels2026tuch-vision,
  title  = {Book-facing vision agents with PhiCS health and spectral Φ},
  author = {Calmels, Walter},
  year   = {2026},
  type   = {Tech report (draft)},
  note   = {https://github.com/wcalmels/tuch-vision}
}
```
