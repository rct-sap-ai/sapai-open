"""Streamlit UI for SAPAI Open.

Three-step flow:
  1. setup    — pick provider, paste API key, pick model
  2. generate — upload protocol, run pipeline
  3. results  — download SAP .docx; restart

Entry point used by both:
  * the in-repo `streamlit_app.py` (for local development), and
  * the production shim in `rct-sap-ai/sapai-streamlit/streamlit_app_open.py`
    (which simply imports and calls main()).
"""

from __future__ import annotations

import json
from typing import Optional

import streamlit as st

from . import __version__
from .chat import ProviderChoice, get_chat
from .docx_writer import build_sap_docx
from .model_catalog import PICK_YOUR_OWN, catalog_updated, choices_for, models_for, resolve_choice
from .pipeline import run_pipeline
from .protocol import load_protocol_from_upload

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
}

KEY_HINTS = {
    "openai": "starts with `sk-…`",
    "anthropic": "starts with `sk-ant-…`",
    "google": "long alphanumeric string from aistudio.google.com",
}


# ── Session-state defaults ───────────────────────────────────────────────────

_DEFAULTS = {
    "provider": "openai",
    "api_key": "",
    "model": models_for("openai")[0],
    "custom_model": "",
    "step": "setup",
    "draft": None,
    "sap_docx_bytes": None,
    "sap_title": "",
    "model_label": "",
}


def _init_state() -> None:
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Shared CSS (lifted from the original open app for visual continuity) ────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap');
[data-testid="stAppViewContainer"] { font-family: 'Plus Jakarta Sans', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.open-hero { text-align:center; padding:3rem 2rem 1.5rem; background:linear-gradient(180deg,#f0faf4 0%,#fafafa 100%); }
.open-chip { display:inline-flex; align-items:center; gap:0.5rem; padding:0.28rem 0.9rem; background:#fff; border:1px solid #e5e7eb; border-radius:100px; font-size:0.68rem; font-weight:700; color:#2d6a4f; letter-spacing:0.07em; text-transform:uppercase; margin-bottom:1.25rem; box-shadow:0 1px 3px rgba(0,0,0,0.04); }
.open-chip-dot { width:6px; height:6px; border-radius:50%; background:#2d6a4f; display:inline-block; }
.open-hero h1 { font-size:clamp(2rem,4vw,2.8rem); font-weight:800; line-height:1.1; letter-spacing:-0.03em; color:#111; margin-bottom:0.7rem; }
.open-hero h1 span { color:#2d6a4f; }
.open-hero-sub { font-size:0.95rem; color:#6b7280; max-width:520px; margin:0 auto 0.5rem; line-height:1.7; }
.open-step-header { font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#2d6a4f; margin-bottom:0.3rem; }
.open-disclaimer { font-size:0.72rem; color:#9ca3af; line-height:1.6; text-align:center; margin-top:0.4rem; }
.section-divider { border:none; border-top:1px solid #f0f0f0; margin:2.5rem 0; }
</style>
"""


# ── Pages ────────────────────────────────────────────────────────────────────


def _render_setup() -> None:
    st.html("""
    <div class="open-hero">
        <div class="open-chip"><span class="open-chip-dot"></span>Paper companion · Open access</div>
        <h1>Statistical Analysis Plans,<br><span>from your protocol.</span></h1>
        <p class="open-hero-sub">
            Reproducible draft SAPs using the section-by-section pipeline validated in
            <a href="https://doi.org/10.64898/2026.03.19.26348626" style="color:#2d6a4f;">Jafari et al. (medRxiv 2026)</a>.
            Bring your own API key from OpenAI, Anthropic, or Google.
        </p>
    </div>
    """)

    st.html('<div style="height:1.25rem;"></div>')

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.html('<div class="open-step-header">Step 1 of 2 — Pick a provider and paste your key</div>')

        provider = st.radio(
            "Provider",
            options=list(PROVIDER_LABELS.keys()),
            format_func=lambda p: PROVIDER_LABELS[p],
            horizontal=True,
            index=list(PROVIDER_LABELS.keys()).index(st.session_state.provider),
            label_visibility="collapsed",
        )

        if provider != st.session_state.provider:
            st.session_state.provider = provider
            st.session_state.model = models_for(provider)[0]
            st.session_state.custom_model = ""

        st.caption(f"API key — {KEY_HINTS[provider]}")
        key_input = st.text_input(
            "API key",
            type="password",
            placeholder="paste your key here",
            value=st.session_state.api_key,
            label_visibility="collapsed",
        )

        options = choices_for(provider)
        current = st.session_state.model if st.session_state.model in options else PICK_YOUR_OWN
        model_choice = st.selectbox(
            "Model",
            options=options,
            index=options.index(current),
            help=(
                f"The five newest {PROVIDER_LABELS[provider]} text models still offered, "
                f"refreshed monthly (list dated {catalog_updated()}). "
                "Pick your own model if you need a different id."
            ),
        )
        custom_model = ""
        if model_choice == PICK_YOUR_OWN:
            custom_model = st.text_input(
                "Model id",
                value=st.session_state.custom_model,
                placeholder="paste the provider's model id",
            )

        st.html('<div style="height:0.4rem;"></div>')

        if st.button("Continue →", type="primary", use_container_width=True):
            if not key_input.strip():
                st.error("Please paste an API key.")
            else:
                try:
                    model = resolve_choice(model_choice, custom_model)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.provider = provider
                    st.session_state.api_key = key_input.strip()
                    st.session_state.model = model
                    st.session_state.custom_model = custom_model.strip()
                    st.session_state.step = "generate"
                    st.rerun()

        st.html(
            """
            <p class="open-disclaimer">
                Your API key is held only in your browser session and never stored or logged.
                All requests are sent directly from this server to your chosen provider.
            </p>
            """
        )


def _render_generate() -> None:
    _header_bar(
        right=(
            f"{PROVIDER_LABELS[st.session_state.provider]} · {st.session_state.model} · "
            f"key ···{st.session_state.api_key[-4:] if len(st.session_state.api_key) >= 4 else '****'}"
        )
    )

    st.html('<div style="height:1.5rem;"></div>')

    _, mid, _ = st.columns([1, 2.2, 1])
    with mid:
        st.html('<div class="open-step-header">Step 2 of 2 — Upload your protocol</div>')

        uploaded = st.file_uploader(
            "Upload protocol (.pdf or .txt)",
            type=["pdf", "txt"],
            label_visibility="collapsed",
        )

        if uploaded:
            try:
                protocol_text = load_protocol_from_upload(uploaded)
            except Exception as e:
                st.error(f"Could not read protocol: {e}")
                return

            st.html(
                f"""
                <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;
                            padding:0.85rem 1.1rem;margin:0.6rem 0;font-size:0.78rem;
                            color:#6b7280;line-height:1.6;">
                    <span style="font-weight:600;color:#111;">📄 {uploaded.name}</span>
                    &nbsp;·&nbsp;{len(protocol_text):,} characters extracted
                </div>
                """
            )

            with st.expander("Preview extracted text", expanded=False):
                st.text(protocol_text[:1500] + (" …" if len(protocol_text) > 1500 else ""))

            st.html('<div style="height:0.6rem;"></div>')

            if st.button("Generate SAP", type="primary", use_container_width=True):
                _run_and_store(protocol_text)
        else:
            st.html(
                """
                <div style="text-align:center;padding:2rem;color:#9ca3af;font-size:0.85rem;">
                    Upload a PDF or TXT file to get started.
                </div>
                """
            )

        st.html('<div style="height:1rem;"></div>')
        if st.button("← Change provider / key / model", key="back_to_setup"):
            st.session_state.step = "setup"
            st.rerun()


def _render_results() -> None:
    _header_bar(
        right_html=(
            '<div style="background:#d1fae5;border-radius:100px;padding:0.3rem 1rem;'
            'font-size:0.7rem;font-weight:700;color:#2d6a4f;letter-spacing:0.06em;">'
            "✓ Generation complete</div>"
        )
    )

    st.html('<div style="height:1.5rem;"></div>')

    st.html(
        """
        <div style="max-width:900px;margin:0 auto;padding:0 1rem;">
            <div class="open-step-header">Downloads</div>
            <h2 style="font-size:1.5rem;font-weight:800;letter-spacing:-0.02em;color:#111;
                       margin-bottom:0.3rem;">Your SAP draft is ready</h2>
            <p style="font-size:0.88rem;color:#6b7280;margin-bottom:1.2rem;">
                Review carefully with a qualified statistician before use in a live trial.
            </p>
        </div>
        """
    )

    safe_name = (st.session_state.sap_title or "SAP").replace(" ", "_")[:60]

    if st.session_state.sap_docx_bytes:
        st.download_button(
            label="⬇ Download SAP (.docx)",
            data=st.session_state.sap_docx_bytes,
            file_name=f"{safe_name}_SAPAI_draft.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            type="primary",
        )

    if st.session_state.draft and st.session_state.draft.errors:
        st.warning(
            f"{len(st.session_state.draft.errors)} section(s) failed to generate — "
            "they're marked in the docx. You can try re-running with a different model."
        )
        with st.expander("Failed sections", expanded=False):
            for key, msg in st.session_state.draft.errors.items():
                st.write(f"**{key}** — {msg}")

    st.html('<hr class="section-divider">')

    if st.session_state.draft and st.session_state.draft.sections:
        for section in st.session_state.draft.section_order:
            content = st.session_state.draft.sections.get(section.key, "")
            with st.expander(section.title, expanded=False):
                if content.strip():
                    st.markdown(content)
                else:
                    st.caption("_no content generated for this section_")

    st.html('<hr class="section-divider">')

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("← Process another protocol", use_container_width=True):
            st.session_state.draft = None
            st.session_state.sap_docx_bytes = None
            st.session_state.sap_title = ""
            st.session_state.step = "generate"
            st.rerun()
    with c2:
        if st.button("Start over", use_container_width=True):
            for k, v in _DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _header_bar(right: Optional[str] = None, right_html: Optional[str] = None) -> None:
    rhtml = right_html or (
        f'<span style="font-size:0.72rem;font-weight:600;color:#6b7280;">{right}</span>'
        if right else ""
    )
    st.html(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:0.85rem 2rem;border-bottom:1px solid #f0f0f0;background:#fff;">
            <span style="font-weight:800;color:#111;letter-spacing:-0.01em;">SAPAI Open</span>
            <div style="display:flex;align-items:center;gap:0.6rem;">
                <div style="width:8px;height:8px;border-radius:50%;background:#2d6a4f;"></div>
                {rhtml}
            </div>
        </div>
        """
    )


def _run_and_store(protocol_text: str) -> None:
    choice = ProviderChoice(
        provider=st.session_state.provider,
        model=st.session_state.model,
        api_key=st.session_state.api_key,
    )
    chat = get_chat(choice)

    progress = st.progress(0.0, text="Starting generation…")

    def cb(i: int, n: int, title: str) -> None:
        progress.progress(i / n, text=f"[{i}/{n}] {title}")

    try:
        draft = run_pipeline(
            protocol_text=protocol_text, chat=chat, progress_callback=cb
        )
    except Exception as e:
        progress.empty()
        st.error(f"Generation failed: {e}")
        if any(t in str(e).lower() for t in ("invalid api key", "incorrect api key", "401", "unauthorized")):
            st.warning("Your API key appears to be invalid — go back and check it.")
        return

    progress.empty()
    st.session_state.draft = draft
    st.session_state.model_label = f"{PROVIDER_LABELS[choice.provider]} · {choice.model}"
    st.session_state.sap_docx_bytes = build_sap_docx(draft, st.session_state.model_label)
    st.session_state.sap_title = draft.trial_title or "SAP"
    st.session_state.step = "results"
    st.rerun()


# ── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    st.set_page_config(
        page_title="SAPAI Open",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.html(_CSS)
    _init_state()

    step = st.session_state.step
    if step == "setup":
        _render_setup()
    elif step == "generate":
        _render_generate()
    elif step == "results":
        _render_results()
    else:
        st.session_state.step = "setup"
        st.rerun()
