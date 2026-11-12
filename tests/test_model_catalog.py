import unittest
from datetime import date

from sapai_open.model_catalog import (
    LATEST_COUNT,
    PICK_YOUR_OWN,
    anthropic_candidates,
    choices_for,
    google_candidates,
    latest_ids,
    models_for,
    openai_candidates,
    resolve_choice,
)


class CatalogTests(unittest.TestCase):
    def test_each_provider_offers_five_plus_a_custom_choice(self):
        for provider in ("openai", "anthropic", "google"):
            self.assertEqual(len(models_for(provider)), LATEST_COUNT)
            self.assertEqual(choices_for(provider)[-1], PICK_YOUR_OWN)

    def test_custom_id_is_used_only_when_picked(self):
        self.assertEqual(resolve_choice("gpt-6-luna", ""), "gpt-6-luna")
        self.assertEqual(resolve_choice(PICK_YOUR_OWN, "  my-model  "), "my-model")
        with self.assertRaises(ValueError):
            resolve_choice(PICK_YOUR_OWN, "  ")

    def test_openai_drops_shut_down_and_non_text_models(self):
        today = date(2026, 11, 12)
        models = [
            {"id": "gpt-old", "created": 50, "shutdown_date": "2026-10-01"},
            {"id": "gpt-image-1", "created": 90},
            {"id": "whisper-1", "created": 80},
            {"id": "gpt-new-a", "created": 5},
            {"id": "gpt-new-b", "created": 4},
            {"id": "gpt-new-c", "created": 3},
            {"id": "gpt-new-d", "created": 2},
            {"id": "gpt-new-e", "created": 1},
            {"id": "gpt-newer", "created": 6, "shutdown_date": "2027-01-01"},
        ]
        chosen = latest_ids(openai_candidates(models, today))
        self.assertEqual(chosen, ["gpt-newer", "gpt-new-a", "gpt-new-b", "gpt-new-c", "gpt-new-d"])

    def test_anthropic_skips_retired_and_limited_models(self):
        models = [
            {"id": "claude-new", "created_at": "2026-11-01T00:00:00Z"},
            {"id": "claude-mythos-5", "created_at": "2026-12-01T00:00:00Z"},
            {"id": "claude-old", "created_at": "2024-01-01T00:00:00Z", "deprecated_at": "2026-01-01T00:00:00Z"},
            {"id": "claude-b", "created_at": "2026-10-01T00:00:00Z"},
            {"id": "claude-c", "created_at": "2026-09-01T00:00:00Z"},
            {"id": "claude-d", "created_at": "2026-08-01T00:00:00Z"},
            {"id": "claude-e", "created_at": "2026-07-01T00:00:00Z"},
        ]
        chosen = latest_ids(anthropic_candidates(models))
        self.assertEqual(chosen, ["claude-new", "claude-b", "claude-c", "claude-d", "claude-e"])

    def test_google_keeps_text_models_and_prefers_the_higher_version(self):
        models = [
            {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.8-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.8-flash-tts", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
            {"name": "models/gemini-3.6-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.1-pro-preview", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.1-flash-lite", "supportedGenerationMethods": ["generateContent"]},
        ]
        chosen = latest_ids(google_candidates(models))
        self.assertEqual(
            chosen,
            [
                "gemini-3.8-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-pro-preview",
                "gemini-3.1-flash-lite",
            ],
        )


if __name__ == "__main__":
    unittest.main()
