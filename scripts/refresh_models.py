"""Rewrite sapai_open/models_catalog.json from the three provider model lists.

Keeps the five newest text models that are still offered. A provider whose key
is missing, or whose list comes back short, keeps the ids already in the file.

    OPENAI_API_KEY=... ANTHROPIC_API_KEY=... GOOGLE_API_KEY=... python scripts/refresh_models.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sapai_open.model_catalog import (  # noqa: E402
    LATEST_COUNT,
    anthropic_candidates,
    google_candidates,
    latest_ids,
    openai_candidates,
)

CATALOG_PATH = ROOT / "sapai_open" / "models_catalog.json"


def _get(url: str, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _openai(api_key: str, today: date) -> list[str]:
    payload = _get(
        "https://api.openai.com/v1/models",
        {"Authorization": f"Bearer {api_key}"},
    )
    return latest_ids(openai_candidates(payload.get("data") or [], today))


def _anthropic(api_key: str) -> list[str]:
    query = urllib.parse.urlencode({"lifecycle": "active", "limit": "100"})
    payload = _get(
        f"https://api.anthropic.com/v1/models?{query}",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    return latest_ids(anthropic_candidates(payload.get("data") or []))


def _google(api_key: str) -> list[str]:
    query = urllib.parse.urlencode({"key": api_key, "pageSize": "200"})
    payload = _get(
        f"https://generativelanguage.googleapis.com/v1beta/models?{query}",
        {},
    )
    return latest_ids(google_candidates(payload.get("models") or []))


def main() -> int:
    today = datetime.now(timezone.utc).date()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    fetchers = {
        "openai": ("OPENAI_API_KEY", lambda key: _openai(key, today)),
        "anthropic": ("ANTHROPIC_API_KEY", _anthropic),
        "google": ("GOOGLE_API_KEY", _google),
    }
    failed = []
    for provider, (env_name, fetch) in fetchers.items():
        api_key = (os.environ.get(env_name) or "").strip()
        if not api_key:
            failed.append(f"{provider}: {env_name} is not set")
            continue
        try:
            ids = fetch(api_key)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            failed.append(f"{provider}: {exc}")
            continue
        if len(ids) < LATEST_COUNT:
            failed.append(f"{provider}: only {len(ids)} current text models, left the saved list")
            continue
        catalog["providers"][provider] = ids

    catalog["updated"] = today.isoformat()
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CATALOG_PATH}")
    for provider, ids in catalog["providers"].items():
        print(f"  {provider}: {', '.join(ids)}")
    if failed:
        print("refresh incomplete:", file=sys.stderr)
        for line in failed:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
