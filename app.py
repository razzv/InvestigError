"""Vercel entrypoint for the rules-only public demo."""

import os

os.environ["INVESTIGERROR_PUBLIC_DEMO"] = "1"

from investigerror.api import app as app  # noqa: E402
