"""Command-line entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .analysis import analyze
from .ingestion import InputError, read_bundle
from .reporting import markdown

app = typer.Typer(help="Investigate structured webhook incidents from local JSON or JSONL.")


@app.command()
def validate(path: Path) -> None:
    """Validate an incident bundle and report its record count."""
    try:
        bundle = read_bundle(path)
    except (InputError, OSError) as exc:
        typer.echo(f"Invalid input: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(f"Valid incident {bundle.incident_id}: {len(bundle.records)} records")


def analyze_file(
    path: Path,
    mode: Annotated[str, typer.Option(help="rules (offline); AI arrives in INV-002")] = "rules",
    out: Annotated[Path, typer.Option(help="JSON report path")] = Path("artifacts/report.json"),
    overwrite: Annotated[bool, typer.Option(help="Replace existing reports")] = False,
    allow_cloud: Annotated[bool, typer.Option(help="Explicit AI transmission permission")] = False,
) -> None:
    """Create evidence-linked JSON and Markdown reports."""
    if mode not in {"rules", "ai"}:
        typer.echo("Mode must be rules or ai", err=True)
        raise typer.Exit(2)
    if out.suffix.lower() != ".json":
        typer.echo("--out must end in .json", err=True)
        raise typer.Exit(2)
    sibling = out.with_suffix(".md")
    if not overwrite and (out.exists() or sibling.exists()):
        typer.echo("Report exists; pass --overwrite to replace it", err=True)
        raise typer.Exit(2)
    try:
        bundle = read_bundle(path)
    except (InputError, OSError) as exc:
        typer.echo(f"Invalid input: {exc}", err=True)
        raise typer.Exit(2) from exc
    report = analyze(bundle)
    if mode == "ai":
        report.requested_mode = "ai"
        report.ai_status = "unavailable"
        reason = "AI provider integration is not available until INV-002."
        if not allow_cloud:
            reason = "AI mode requires --allow-cloud; no data was transmitted."
        report.metadata.warnings.append(reason)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    sibling.write_text(markdown(report), encoding="utf-8")
    typer.echo(f"Wrote {out} and {sibling}")
    if mode == "ai":
        typer.echo(report.metadata.warnings[-1], err=True)
        raise typer.Exit(3)


app.command(name="analyze")(analyze_file)


if __name__ == "__main__":
    app()
