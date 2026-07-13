# Manuscript agents: vision, health, and optional spectral Phi (theory-agnostic)

**Tech report (draft v0.2)**  
Walter Calmels / TUCH  
Artifact: [tuch-vision](https://github.com/wcalmels/tuch-vision)  
Date: 2026-07-13  

> Product thesis: improve and enrich **any** manuscript.  
> A scientific theory (e.g. TTH) is a **content profile**, not the agent core.

---

## Abstract

We describe `tuch-vision`, a local-first agent layer for long-form manuscripts: figure/OCR audits, screenshot QA, and PhiCS-based chapter health scoring. The stack is deliberately **theory-agnostic**. Domain constants and soft OCR priors load from an optional `manuscript.toml` (or example profiles), while writers/critics remain interchangeable (Cursor, private book agents, or other LLMs). Optional `phi_spectral` summarizes multi-unit signal matrices and must not be confused with theory-level \(\Phi\) symbols.

## 1. Motivation

Authors need the same operational loop for every book:

1. Are figures exportable and caption-aligned?  
2. Are chapters filling and approvable?  
3. Should a human (or LLM) review this unit next?

Hardcoding one monograph’s constants into the tool breaks reuse. Profiles invert that: **agent core generic, theory injectable**.

## 2. Architecture

```text
manuscript.toml  →  paths + optional ocr_hints
        │
        ├── figures/screens  → VisionAgent
        └── outline/drafts   → signals → PhiCS health
                                   └── optional spectral matrix
```

## 3. Init surface

`tuch-vision init ./my-book` creates outline, drafts, style/constraints stubs, and empty hint list. Example TTH priors live only under `examples/profiles/tth/`.

## 4. Related products

| Artifact | Role |
|----------|------|
| unicornio-screens | Product UI gates (engineering) |
| sentinel-edge | Industrial PhiCS edge |
| **tuch-vision** | Manuscript perception + health for any book |

## 5. Claim discipline

| Allowed | Disallowed |
|---------|------------|
| Generic manuscript QA agents | “This tool is the TTH theory” |
| Optional profile hints | Theory constants required for core to run |
| phi_spectral as integration diagnostic | Equating to book \(\Phi\) |

## 6. Future work

Multi-book workspaces; CI per profile; richer outline schemas; writer adapters as plugins.

## Citation

```bibtex
@techreport{calmels2026tuch-vision,
  title  = {Manuscript agents: vision, health, and optional spectral Phi (theory-agnostic)},
  author = {Calmels, Walter},
  year   = {2026},
  type   = {Tech report (draft v0.2)},
  note   = {https://github.com/wcalmels/tuch-vision}
}
```
