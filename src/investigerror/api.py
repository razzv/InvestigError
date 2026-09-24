"""Loopback-only HTTP interface over the CLI analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .analysis import analyze
from .context import ContextLimitError, select_context
from .explanation import explain
from .ingestion import MAX_BYTES, InputError, parse_bundle
from .models import IncidentBundle
from .redaction import sanitize
from .reporting import markdown

STATIC = Path(__file__).parent / "static"
EXAMPLES = {path.stem: path for path in sorted((STATIC / "examples").glob("*.json"))}
EXAMPLES.update({f"{path.stem}-jsonl": path for path in sorted((STATIC / "examples").glob("*.jsonl"))})

app = FastAPI(title="InvestigError local API", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def local_request_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD"} and origin:
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin != expected:
            return JSONResponse({"detail": "Cross-origin requests are not allowed."}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/examples")
def examples() -> list[dict[str, str]]:
    return [{"id": key, "filename": path.name} for key, path in EXAMPLES.items()]


@app.get("/api/examples/{example_id}")
def example(example_id: str) -> FileResponse:
    path = EXAMPLES.get(example_id)
    if path is None:
        raise HTTPException(404, "Unknown example.")
    return FileResponse(path, media_type="application/json" if path.suffix == ".json" else "application/x-ndjson")


async def _bundle(file: UploadFile) -> IncidentBundle:
    suffix = Path(file.filename or "").suffix.lower()
    try:
        raw = await file.read(MAX_BYTES + 1)
        return parse_bundle(raw, suffix)
    except InputError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()


def _preview(bundle: IncidentBundle) -> dict[str, object]:
    safe = sanitize(bundle)
    report = analyze(safe)
    try:
        selected = select_context(safe, report)
        provider_context: object = json.loads(selected.text)
        preview_error = None
    except ContextLimitError as exc:
        provider_context = None
        preview_error = str(exc)
    return {
        "bundle": safe.model_dump(mode="json"),
        "provider_context": provider_context,
        "preview_error": preview_error,
        "limitations": report.evidence_limitations,
    }


@app.post("/api/validate")
async def validate(file: Annotated[UploadFile, File()]) -> dict[str, object]:
    return _preview(await _bundle(file))


def _report_response(report) -> dict[str, object]:  # type: ignore[no-untyped-def]
    return {"report": report.model_dump(mode="json"), "markdown": markdown(report)}


@app.post("/api/analyze")
async def analyze_upload(file: Annotated[UploadFile, File()]) -> dict[str, object]:
    return _report_response(analyze(await _bundle(file)))


@app.post("/api/explain")
async def explain_upload(
    file: Annotated[UploadFile, File()],
    allow_cloud: Annotated[bool, Form()] = False,
) -> dict[str, object]:
    if not allow_cloud:
        raise HTTPException(400, "Explicit cloud consent is required; no data was transmitted.")
    return _report_response(explain(await _bundle(file), allow_cloud=True))
