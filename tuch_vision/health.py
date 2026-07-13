"""
Manuscript health via PhiCS (local) + DialogAgent insight.

1. Collect chapter signals from outline
2. Learn baselines from approved chapters (median per channel)
3. Score every chapter → fidelity / anomaly / action
4. Optional DialogAgent.analyze on weakest channels
5. Write markdown report
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .signals import collect_chapters, book_aggregate


def _ensure_sentinel_path(sentinel_root: Path) -> None:
    root = str(sentinel_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)


@dataclass
class ChapterHealth:
    chapter_id: str
    title: str
    status: str
    signals: Dict[str, float]
    channel_scores: Dict[str, dict] = field(default_factory=dict)
    mean_fidelity: float = 1.0
    max_anomaly: float = 0.0
    action: str = "monitor"
    level: str = "NORMAL"


@dataclass
class HealthReport:
    generated_at: str
    book_signals: Dict[str, float]
    chapters: List[ChapterHealth]
    alerts: List[dict]
    dialog_notes: List[str]
    summary: str
    phics_ok: bool = True
    error: str = ""
    spectral_notes: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# Manuscript Health (PhiCS)",
            "",
            f"Generated: {self.generated_at}",
            "",
            f"**Summary:** {self.summary}",
            "",
            "## Book-level signals (0–1, higher = healthier)",
            "",
            "| Channel | Value |",
            "|---------|------:|",
        ]
        for k, v in self.book_signals.items():
            lines.append(f"| `{k}` | {v:.3f} |")

        lines += [
            "",
            "## Chapters",
            "",
            "| ID | Status | Mean fid | Max anomaly | Action | Level |",
            "|----|--------|---------:|------------:|--------|-------|",
        ]
        for ch in sorted(self.chapters, key=lambda c: c.mean_fidelity):
            lines.append(
                f"| {ch.chapter_id} | {ch.status} | {ch.mean_fidelity:.4f} | "
                f"{ch.max_anomaly:.4f} | {ch.action} | {ch.level} |"
            )

        if self.alerts:
            lines += ["", "## Alerts", ""]
            for a in self.alerts:
                lines.append(
                    f"- **{a['chapter_id']}** `{a['channel']}`: "
                    f"val={a['value']:.3f} fid={a['fidelity']:.4f} "
                    f"→ {a['action']}/{a['level']}"
                )

        if self.dialog_notes:
            lines += ["", "## DialogAgent notes", ""]
            for note in self.dialog_notes:
                lines.append(f"- {note}")

        if self.spectral_notes:
            lines += ["", "## Spectral Φ (ConsciousAI bridge)", ""]
            for note in self.spectral_notes:
                lines.append(note if note.startswith("#") or note.startswith("-") or note.startswith(">") or note.startswith("_") else f"- {note}")
            # notes already include markdown from helper; keep simple list
            lines.append("")

        if self.error:
            lines += ["", f"> Error: {self.error}", ""]

        lines.append("")
        return "\n".join(lines)


def _median(vals: List[float]) -> float:
    if not vals:
        return 0.5
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return 0.5 * (s[mid - 1] + s[mid])


def run_manuscript_health(
    outline: dict,
    drafts_dir: Path,
    approved_dir: Path,
    sentinel_root: Path,
    explain: bool = True,
) -> HealthReport:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    chapters = collect_chapters(outline, drafts_dir, approved_dir)
    book_sig = book_aggregate(chapters)

    if not sentinel_root.exists():
        return HealthReport(
            generated_at=now,
            book_signals=book_sig,
            chapters=[],
            alerts=[],
            dialog_notes=[],
            summary="PhiCS unavailable (sentinel-edge not found)",
            phics_ok=False,
            error=f"Missing: {sentinel_root} (set TUCH_SENTINEL_ROOT)",
        )

    _ensure_sentinel_path(sentinel_root)

    try:
        from agent.phics_backend import PhiCSBackend
        from agent.sensor_policy import SensorPolicy
    except Exception as e:
        return HealthReport(
            generated_at=now,
            book_signals=book_sig,
            chapters=[],
            alerts=[],
            dialog_notes=[],
            summary="PhiCS import failed",
            phics_ok=False,
            error=str(e),
        )

    import asyncio

    async def _score() -> HealthReport:
        backend = PhiCSBackend(lattice_size=10, encoding_dim=128, evolve_steps=2)
        policy = SensorPolicy(warmup_samples=3, auto_relearn=False)
        policy._in_warmup = False

        async with backend:
            await backend.reset()

            # Baseline = median of approved chapters per channel
            approved = [c for c in chapters if c.status == "approved"]
            baseline_src = approved if len(approved) >= 3 else chapters
            channels = [
                "fill_ratio",
                "approval",
                "expansion_ok",
                "promises_ok",
                "file_ready",
            ]
            baselines = {
                ch: _median([getattr(c, ch) for c in baseline_src])
                for ch in channels
            }
            for ch, base in baselines.items():
                await backend.learn(f"normal_{ch}", [base], "generic")

            # Also learn book aggregate as patterns
            for ch, val in book_sig.items():
                await backend.learn(f"book_{ch}", [val], "generic")

            results: List[ChapterHealth] = []
            alerts: List[dict] = []

            for unit in chapters:
                sig = unit.as_dict()
                samples = [
                    {"values": [sig[ch]], "label": ch, "stimulus_type": "generic"}
                    for ch in channels
                ]
                batch = await backend.batch(samples)
                scores = {}
                fids = []
                anoms = []
                worst_action = "monitor"
                worst_level = "NORMAL"
                rank = {"monitor": 0, "alert_low": 1, "alert_medium": 2,
                        "alert_high": 3, "emergency": 4}

                for i, ch in enumerate(channels):
                    r = (batch or {}).get("results", [{}])[i]
                    fid = float(r.get("fidelity", 1.0))
                    anom = float(r.get("anomaly_score", 0.0))
                    decision = policy.decide(
                        fid, anom, warn_thresh=0.998, crit_thresh=0.990
                    )
                    scores[ch] = {
                        "value": sig[ch],
                        "fidelity": fid,
                        "anomaly": anom,
                        "action": decision.action,
                        "level": decision.level,
                    }
                    fids.append(fid)
                    anoms.append(anom)
                    if rank.get(decision.action, 0) > rank.get(worst_action, 0):
                        worst_action = decision.action
                        worst_level = decision.level
                    if decision.should_alert:
                        alerts.append({
                            "chapter_id": unit.chapter_id,
                            "channel": ch,
                            "value": sig[ch],
                            "fidelity": fid,
                            "action": decision.action,
                            "level": decision.level,
                        })

                mean_fid = sum(fids) / len(fids) if fids else 1.0
                results.append(
                    ChapterHealth(
                        chapter_id=unit.chapter_id,
                        title=unit.title,
                        status=unit.status,
                        signals=sig,
                        channel_scores=scores,
                        mean_fidelity=mean_fid,
                        max_anomaly=max(anoms) if anoms else 0.0,
                        action=worst_action,
                        level=worst_level,
                    )
                )

            dialog_notes: List[str] = []
            if explain:
                try:
                    from agents.dialog_agent import DialogAgent
                    dialog = DialogAgent(
                        name="ManuscriptHealth",
                        domain="industrial",
                        verbose=False,
                    )
                    for ch, base in baselines.items():
                        dialog.learn_explicitly(f"normal_{ch}", base, "generic")
                    # Explain up to 3 weakest book channels vs baseline
                    weakest = sorted(
                        book_sig.items(),
                        key=lambda kv: abs(kv[1] - baselines.get(kv[0], 0.5)),
                        reverse=True,
                    )[:3]
                    for name, val in weakest:
                        insight = dialog.analyze(val, name.replace("_", " "))
                        dialog_notes.append(
                            f"{name}={val:.3f} → label={insight.get('label')} "
                            f"fid={insight.get('fidelity', 0):.4f} "
                            f"level={insight.get('anomaly_level')}"
                        )
                except Exception as e:
                    dialog_notes.append(f"(DialogAgent skipped: {e})")

            n_alert_ch = len({a["chapter_id"] for a in alerts})
            if not alerts:
                summary = (
                    f"Healthy — {len(chapters)} units scored against "
                    f"{len(baseline_src)} baseline chapters; no alerts"
                )
            else:
                summary = (
                    f"{len(alerts)} channel alerts across {n_alert_ch} units "
                    f"(baseline from {len(baseline_src)} approved/draft chapters)"
                )

            spectral_notes: List[str] = []
            try:
                from .spectral import markdown_section, score_signal_matrix
                import numpy as np

                # Matrix: one row per chapter, columns = channel values
                mat = np.array(
                    [[float(unit.as_dict().get(ch, 0.5)) for ch in channels] for unit in chapters],
                    dtype=float,
                )
                sp = score_signal_matrix(
                    mat, row_ids=[u.chapter_id for u in chapters]
                )
                spectral_notes = markdown_section(sp)
                # Drop the duplicate ## header — to_markdown adds its own
                spectral_notes = [
                    ln for ln in spectral_notes
                    if not ln.startswith("## Spectral")
                ]
            except Exception as e:
                spectral_notes = [f"_Spectral Φ skipped: {e}_"]

            return HealthReport(
                generated_at=now,
                book_signals=book_sig,
                chapters=results,
                alerts=alerts,
                dialog_notes=dialog_notes,
                summary=summary,
                phics_ok=True,
                spectral_notes=spectral_notes,
            )

    return asyncio.run(_score())
