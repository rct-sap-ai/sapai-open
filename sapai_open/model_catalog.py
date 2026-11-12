"""The five newest text models each provider still offers, plus a free-text choice.

`models_catalog.json` is what the app shows. `scripts/refresh_models.py` rewrites
it from the provider model lists. A monthly GitHub Action runs that script.
"""

from __future__ import annotations

import json
import re
from datetime import date
from importlib.resources import files
from typing import Any

LATEST_COUNT = 5
PICK_YOUR_OWN = "Pick your own model"
PROVIDERS = ("openai", "anthropic", "google")

_OPENAI_SKIP = (
    "audio", "realtime", "transcribe", "tts", "image", "embed", "moderation",
    "instruct", "search", "whisper", "dall-e", "sora", "cyber", "rosalind",
    "daybreak",
)
_GOOGLE_SKIP = ("tts", "live", "image", "imagen", "embed", "aqa", "veo", "robot")


def load_catalog() -> dict[str, Any]:
    raw = files("sapai_open").joinpath("models_catalog.json").read_text(encoding="utf-8")
    return json.loads(raw)


def catalog_updated() -> str:
    return str(load_catalog().get("updated") or "")


def models_for(provider: str) -> list[str]:
    ids = load_catalog()["providers"][provider]
    if not ids:
        raise ValueError(f"No models listed for {provider}")
    return list(ids)


def choices_for(provider: str) -> list[str]:
    return models_for(provider) + [PICK_YOUR_OWN]


def resolve_choice(selected: str, custom: str) -> str:
    if selected == PICK_YOUR_OWN:
        text = custom.strip()
        if not text:
            raise ValueError("Type a model id, or pick one from the list.")
        return text
    return selected


def latest_ids(candidates: list[dict[str, Any]], n: int = LATEST_COUNT) -> list[str]:
    """Newest in-use ids. `sort_key` is larger for a newer model."""
    usable = [item for item in candidates if item.get("in_use")]
    usable.sort(key=lambda item: item["sort_key"], reverse=True)
    chosen: list[str] = []
    for item in usable:
        model_id = item["id"]
        if model_id in chosen:
            continue
        chosen.append(model_id)
        if len(chosen) == n:
            break
    return chosen


def openai_candidates(models: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    out = []
    for model in models:
        model_id = str(model.get("id") or "")
        lowered = model_id.lower()
        if model_id.startswith("ft:"):
            continue
        if not (lowered.startswith("gpt-") or lowered.startswith("o")):
            continue
        if any(part in lowered for part in _OPENAI_SKIP):
            continue
        shutdown = model.get("shutdown_date") or ""
        in_use = not shutdown or shutdown > today.isoformat()
        out.append({"id": model_id, "sort_key": model.get("created") or 0, "in_use": in_use})
    return out


def anthropic_candidates(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for index, model in enumerate(models):
        model_id = str(model.get("id") or "")
        if not model_id.startswith("claude-") or "mythos" in model_id:
            continue
        lifecycle = str(model.get("lifecycle") or "")
        deprecated = model.get("deprecated_at")
        in_use = lifecycle not in {"deprecated", "retired"} and not deprecated
        created = str(model.get("created_at") or "")
        # The list is newest-first. A missing date stays behind any real timestamp.
        sort_key = (1, created) if created else (0, 1_000_000 - index)
        out.append({"id": model_id, "sort_key": sort_key, "in_use": in_use})
    return out


def google_candidates(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for model in models:
        name = str(model.get("name") or "")
        model_id = name.split("/")[-1]
        methods = model.get("supportedGenerationMethods") or model.get("supported_generation_methods") or []
        if "generateContent" not in methods and "generate_content" not in methods:
            continue
        if not model_id.startswith("gemini-"):
            continue
        if any(part in model_id for part in _GOOGLE_SKIP):
            continue
        numbers = tuple(int(part) for part in re.findall(r"\d+", model_id))
        out.append({"id": model_id, "sort_key": numbers, "in_use": True})
    return out
