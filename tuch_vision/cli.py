"""CLI: tuch-vision init|figures|screens|health"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console

from tuch_vision.paths import book_agent_root, sentinel_root
from tuch_vision.profile import load_profile

app = typer.Typer(
    name="tuch-vision",
    help="Manuscript agents: vision/OCR + PhiCS health + optional spectral Phi (any book).",
    no_args_is_help=True,
)
console = Console()


def _project_profile(project: Path | None) -> "object":
    root = Path(project) if project else Path.cwd()
    return load_profile(root)


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="New manuscript project directory"),
    name: str = typer.Option("Untitled Manuscript", "--name", "-n"),
    language: str = typer.Option("en", "--language", "-l"),
    hints_from: Path | None = typer.Option(
        None,
        "--hints-from",
        help="Optional JSON list of OCR soft priors (e.g. examples/profiles/tth/hints.json)",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite manuscript.toml"),
) -> None:
    """Scaffold a generic manuscript project (theory-agnostic)."""
    from tuch_vision.profile import init_manuscript

    hints: list[str] = []
    if hints_from:
        hints = json.loads(Path(hints_from).read_text(encoding="utf-8"))
    try:
        profile_path = init_manuscript(
            path, name=name, language=language, ocr_hints=hints, force=force
        )
    except FileExistsError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(f"[green]Initialized[/green] {profile_path}")
    console.print("Next: edit state/style_guide.md and drafts/, then run health/figures/screens.")


@app.command()
def figures(
    docx: Path | None = typer.Option(None, "--docx", help="DOCX with figures"),
    folder: Path | None = typer.Option(None, "--folder", "-f", help="Image folder"),
    project: Path | None = typer.Option(
        None, "--project", "-p", help="Dir with manuscript.toml"
    ),
    no_ocr: bool = typer.Option(False, "--no-ocr"),
    no_phics: bool = typer.Option(False, "--no-phics"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Audit manuscript figures (DOCX or image folder)."""
    prof = _project_profile(project)
    if not docx and not folder:
        fig = prof.path("figures")
        if fig.exists() and any(fig.iterdir()):
            folder = fig
        else:
            console.print("[red]Provide --docx or --folder (or put images in project figures/)[/red]")
            raise typer.Exit(1)

    from tuch_vision.vision import run_vision_audit

    report = run_vision_audit(
        docx=docx,
        folder=folder,
        do_ocr=not no_ocr,
        use_phics=not no_phics,
        verbose=True,
        ocr_hints=list(prof.ocr_hints),
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
    folder: Path | None = typer.Argument(None, help="Screenshot folder"),
    project: Path | None = typer.Option(None, "--project", "-p"),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    no_ocr: bool = typer.Option(False, "--no-ocr"),
    no_phics: bool = typer.Option(False, "--no-phics"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Audit UI screenshots (OCR + quality + optional PhiCS)."""
    prof = _project_profile(project)
    folder = folder or prof.path("screenshots")
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
    project: Path | None = typer.Option(None, "--project", "-p"),
    outline: Path | None = typer.Option(None, "--outline"),
    drafts: Path | None = typer.Option(None, "--drafts"),
    approved: Path | None = typer.Option(None, "--approved"),
    no_explain: bool = typer.Option(False, "--no-explain"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Score manuscript chapter health via local PhiCS (needs sentinel-edge)."""
    prof = _project_profile(project)
    # Prefer project profile; fall back to sibling book_agent for legacy layouts
    book = book_agent_root()
    outline_path = outline or (
        prof.path("outline")
        if (project or (Path.cwd() / "manuscript.toml").exists())
        else (book / "state" / "manuscript_outline.json")
    )
    drafts_dir = drafts or (
        prof.path("drafts")
        if (project or (Path.cwd() / "manuscript.toml").exists())
        else (book / "drafts")
    )
    approved_dir = approved or (
        prof.path("approved")
        if (project or (Path.cwd() / "manuscript.toml").exists())
        else (book / "approved")
    )

    if not outline_path.exists():
        console.print(f"[red]Outline not found: {outline_path}[/red]")
        console.print("[dim]Run: tuch-vision init ./my-book[/dim]")
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
