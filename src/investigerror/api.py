"""Loopback-only HTTP interface over the CLI analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .analysis import analyze
from .context import ContextLimitError, select_context
from .explanation import explain
from .ingestion import MAX_BYTES, InputError, parse_bundle
from .models import IncidentBundle, InvestigationReport
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


async def _bundle(request: Request) -> IncidentBundle:
    format_name = request.headers.get("x-incident-format")
    if format_name not in {"json", "jsonl"}:
        raise HTTPException(422, "X-Incident-Format must be json or jsonl.")
    size = 0
    parts: list[bytes] = []
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(413, f"input exceeds {MAX_BYTES} byte limit")
        parts.append(chunk)
    try:
        return parse_bundle(b"".join(parts), f".{format_name}")
    except InputError as exc:
        raise HTTPException(422, str(exc)) from exc


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
async def validate(request: Request) -> dict[str, object]:
    return _preview(await _bundle(request))


def _report_response(report: InvestigationReport) -> dict[str, object]:
    return {"report": report.model_dump(mode="json"), "markdown": markdown(report)}


@app.post("/api/analyze")
async def analyze_upload(request: Request) -> dict[str, object]:
    return _report_response(analyze(await _bundle(request)))


@app.post("/api/explain")
async def explain_upload(
    request: Request,
) -> dict[str, object]:
    if request.headers.get("x-allow-cloud") != "true":
        raise HTTPException(400, "Explicit cloud consent is required; no data was transmitted.")
    bundle = await _bundle(request)
    return _report_response(await run_in_threadpool(explain, bundle, allow_cloud=True))
