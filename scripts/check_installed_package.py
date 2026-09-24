"""Smoke-check a built wheel in a fresh environment outside the repository."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    wheels = sorted((root / "dist").glob("investigerror-*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected exactly one investigerror wheel in dist/; clear old wheels and run uv build")

    with tempfile.TemporaryDirectory(prefix="investigerror-wheel-") as directory:
        outside = Path(directory)
        venv = outside / "venv"
        run("uv", "venv", str(venv), cwd=outside)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = venv / ("Scripts/investigerror.exe" if os.name == "nt" else "bin/investigerror")
        run("uv", "pip", "install", "--python", str(python), str(wheels[0]), cwd=outside)
        fixture = root / "examples/incidents/example-001.json"
        report = outside / "report.json"
        run(str(cli), "validate", str(fixture), cwd=outside)
        run(str(cli), "analyze", str(fixture), "--mode", "rules", "--out", str(report), cwd=outside)
        result = json.loads(report.read_text(encoding="utf-8"))
        if not result["findings"] or not report.with_suffix(".md").is_file():
            raise SystemExit("Installed CLI did not produce evidence-linked JSON and Markdown")
        run(
            str(python),
            "-c",
            "from importlib.resources import files; "
            "from investigerror import __name__ as package; "
            "root = files(package); "
            "assert root.joinpath('prompts/explain-v1.txt').is_file(); "
            "assert root.joinpath('static/index.html').is_file(); "
            "assert root.joinpath('static/examples/example-001.json').is_file()",
            cwd=outside,
        )
    print("Installed wheel CLI and package resources passed from a separate directory")


if __name__ == "__main__":
    main()
