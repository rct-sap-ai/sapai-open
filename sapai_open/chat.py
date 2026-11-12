"""Three-provider chat wrapper for the paper's validated models.

Per the paper (Jafari et al., 2026):
- OpenAI gpt-5 (gpt-5-2025-08-07): default verbosity and reasoning settings
- Anthropic Claude Sonnet 4 (claude-sonnet-4-20250514): temperature=0.2
- Google Gemini 2.5 Pro (gemini-2.5-pro): temperature=0.2

User-supplied keys are passed at construction time and never persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


# ── Paper-validated defaults ─────────────────────────────────────────────────

PAPER_MODELS = {
    "openai": "gpt-5-2025-08-07",
    "anthropic": "claude-sonnet-4-20250514",
    "google": "gemini-2.5-pro",
}

PAPER_TEMPERATURES = {
    # OpenAI's responses API for gpt-5 doesn't take temperature — paper used defaults
    "openai": None,
    "anthropic": 0.2,
    "google": 0.2,
}


class ChatBackend(Protocol):
    def get_response(self, prompt: str, system_message: str) -> str: ...


# ── OpenAI ───────────────────────────────────────────────────────────────────


class OpenAIChat:
    """Wrapper for OpenAI gpt-5 via the responses API (paper-faithful settings).

    For non-gpt-5 OpenAI models the responses API still works; reasoning/
    verbosity options are only used by reasoning-capable models and are
    ignored elsewhere.
    """

    def __init__(self, model: str, api_key: str):
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(api_key=api_key)

    def get_response(self, prompt: str, system_message: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=system_message,
            input=prompt,
        )
        return (response.output_text or "").strip()


# ── Anthropic ────────────────────────────────────────────────────────────────


class AnthropicChat:
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = PAPER_TEMPERATURES["anthropic"],
        max_tokens: int = 4096,
    ):
        from anthropic import Anthropic

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = Anthropic(api_key=api_key)

    def get_response(self, prompt: str, system_message: str) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_message,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.model == PAPER_MODELS["anthropic"]:
            kwargs["temperature"] = self.temperature
        response = self.client.messages.create(**kwargs)
        return (response.content[0].text or "").strip()


# ── Google Gemini ────────────────────────────────────────────────────────────


class GoogleChat:
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float = PAPER_TEMPERATURES["google"],
    ):
        from google import genai
        from google.genai import types

        self.model = model
        self.temperature = temperature
        self._types = types
        self.client = genai.Client(api_key=api_key)

    def get_response(self, prompt: str, system_message: str) -> str:
        config = {"system_instruction": system_message}
        if self.model == PAPER_MODELS["google"]:
            config["temperature"] = self.temperature
        response = self.client.models.generate_content(
            model=self.model,
            config=self._types.GenerateContentConfig(**config),
            contents=prompt,
        )
        return (response.text or "").strip()


# ── Factory ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProviderChoice:
    provider: str  # "openai" | "anthropic" | "google"
    model: str
    api_key: str


def get_chat(choice: ProviderChoice) -> ChatBackend:
    if choice.provider == "openai":
        return OpenAIChat(model=choice.model, api_key=choice.api_key)
    if choice.provider == "anthropic":
        return AnthropicChat(model=choice.model, api_key=choice.api_key)
    if choice.provider == "google":
        return GoogleChat(model=choice.model, api_key=choice.api_key)
    raise ValueError(f"Unknown provider: {choice.provider!r}")
