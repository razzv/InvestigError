"""Command-line entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .analysis import analyze
from .explanation import explain
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
    mode: Annotated[str, typer.Option(help="rules (offline) or ai (requires --allow-cloud)")] = "rules",
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
    report = analyze(bundle) if mode == "rules" else explain(bundle, allow_cloud=allow_cloud)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    sibling.write_text(markdown(report), encoding="utf-8")
    typer.echo(f"Wrote {out} and {sibling}")
    if mode == "ai" and report.ai_status != "completed":
        typer.echo(report.metadata.warnings[-1], err=True)
        raise typer.Exit(3)


app.command(name="analyze")(analyze_file)


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Loopback interface")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Local HTTP port")] = 8000,
) -> None:
    """Serve the local browser interface."""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        typer.echo("The local UI can only bind to a loopback address.", err=True)
        raise typer.Exit(2)
    import uvicorn

    uvicorn.run("investigerror.api:app", host=host, port=port)


if __name__ == "__main__":
    app()
