"""Vercel entrypoint for the rules-only public demo."""

import os
import sys
from pathlib import Path

os.environ["INVESTIGERROR_PUBLIC_DEMO"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from investigerror.api import app as app  # noqa: E402
