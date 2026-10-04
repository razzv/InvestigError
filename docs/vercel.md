# Vercel rules demo

The root `app.py` exports the FastAPI app for Vercel and enables a public-demo mode. The hosted UI offers bundled synthetic examples, validation, deterministic rules, linked evidence, and browser-generated JSON/Markdown downloads. It does not call an AI provider. A direct `/api/explain` request returns 403 even if a caller supplies cloud consent or provider credentials.

The browser sends uploaded bytes to a Vercel Function. The app rejects uploads above 2 MiB, limits a bundle to 1,000 records, and does not deliberately persist uploads or reports. Public hosting is still unsuitable for confidential incident data: the platform processes requests, and redaction is best-effort. Use synthetic or non-confidential data. The app has no account system or abuse controls beyond the input bounds; review traffic, cost and platform logs before wider exposure.

Vercel detects the root FastAPI entrypoint and installs dependencies from `pyproject.toml`. Deploy this branch to a preview deployment with the Vercel CLI or Git integration. The deployment URL normally ends in `.vercel.app`; for a custom domain, set `INVESTIGERROR_ALLOWED_HOSTS` to the exact hostname (or comma-separated hostnames) in the Vercel project environment and redeploy. Do not set `ANTHROPIC_API_KEY` or `AI_MODEL` on this demo; provider calls are disabled even if those values exist.

After deployment, open the URL, choose `example-001.json`, click **Run rules**, and check for an R3 finding with linked evidence. Also check `/health` for `{"status":"ok"}`. Run a bounded upload only with synthetic or non-confidential data. The local UI and CLI remain available for optional, explicitly authorized AI explanation.
