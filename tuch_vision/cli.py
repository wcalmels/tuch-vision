"""CLI: tuch-vision figures|screens|health"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from tuch_vision.paths import book_agent_root, sentinel_root

app = typer.Typer(
    name="tuch-vision",
    help="Manuscript vision/OCR + PhiCS health + optional spectral Phi (local-first).",
    no_args_is_help=True,
)
console = Console()


@app.command()
def figures(
    docx: Path | None = typer.Option(None, "--docx", help="DOCX with figures"),
    folder: Path | None = typer.Option(None, "--folder", "-f", help="Image folder"),
    no_ocr: bool = typer.Option(False, "--no-ocr"),
    no_phics: bool = typer.Option(False, "--no-phics"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Audit manuscript figures (DOCX or image folder)."""
    if not docx and not folder:
        console.print("[red]Provide --docx or --folder[/red]")
        raise typer.Exit(1)

    from tuch_vision.vision import run_vision_audit

    report = run_vision_audit(
        docx=docx,
        folder=folder,
        do_ocr=not no_ocr,
        use_phics=not no_phics,
        verbose=True,
    )
    md = report.to_markdown()
    if out is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        out = Path("output") / f"vision_audit_{stamp}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    console.print(report.summary)
    console.print(f"[dim]Report: {out}[/dim]")


@app.command()
def screens(
    folder: Path = typer.Argument(..., help="Screenshot folder"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    no_ocr: bool = typer.Option(False, "--no-ocr"),
    no_phics: bool = typer.Option(False, "--no-phics"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Audit UI screenshots (OCR + quality + optional PhiCS)."""
    if not folder.exists():
        console.print(f"[red]Not found: {folder}[/red]")
        raise typer.Exit(1)

    from tuch_vision.vision import run_screen_audit

    report = run_screen_audit(
        folder=folder,
        recursive=recursive,
        do_ocr=not no_ocr,
        use_phics=not no_phics,
        verbose=True,
    )
    md = report.to_markdown()
    if out is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        out = Path("output") / f"screen_audit_{stamp}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    console.print(report.summary)
    console.print(f"[dim]Report: {out}[/dim]")


@app.command()
def health(
    outline: Path | None = typer.Option(
        None,
        "--outline",
        help="manuscript_outline.json (default: sibling book_agent/state/...)",
    ),
    drafts: Path | None = typer.Option(None, "--drafts"),
    approved: Path | None = typer.Option(None, "--approved"),
    no_explain: bool = typer.Option(False, "--no-explain"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Score manuscript chapter health via local PhiCS (needs sentinel-edge)."""
    book = book_agent_root()
    outline_path = outline or (book / "state" / "manuscript_outline.json")
    drafts_dir = drafts or (book / "drafts")
    approved_dir = approved or (book / "approved")

    if not outline_path.exists():
        console.print(f"[red]Outline not found: {outline_path}[/red]")
        console.print("[dim]Set BOOK_AGENT_ROOT or pass --outline[/dim]")
        raise typer.Exit(1)

    data = json.loads(outline_path.read_text(encoding="utf-8"))
    from tuch_vision.health import run_manuscript_health

    report = run_manuscript_health(
        outline=data,
        drafts_dir=drafts_dir,
        approved_dir=approved_dir,
        sentinel_root=sentinel_root(),
        explain=not no_explain,
    )
    md = report.to_markdown()
    if out is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        out = Path("output") / f"manuscript_health_{stamp}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    console.print(report.summary)
    console.print(f"[dim]Report: {out}[/dim]")
    if not report.phics_ok:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
