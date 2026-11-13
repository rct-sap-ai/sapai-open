# SAPAI Open

Paper-faithful open implementation of the **Statistical Analysis Plan AI (SAPAI)** pipeline.

This repository is the open companion to:

> Jafari H, Chu P, Lange M, Maher F, Glen C, Pearson O, Burges C, MacGregor L,
> Martyn M, Cross S, Carter B, Emsley R, Forbes G. *From Protocol to Analysis
> Plan: Development and Validation of a Large Language Model Pipeline for
> Statistical Analysis Plan Generation using Artificial Intelligence (SAPAI).*
> medRxiv 2026. <https://doi.org/10.64898/2026.03.19.26348626>

It implements the **section-by-section prompting pipeline** described in
the paper, using **only the prompts that were validated**, and supports the
three model families that the paper compared.

The paper compared `gpt-5-2025-08-07`, `claude-sonnet-4-20250514`, and
`gemini-2.5-pro`. The app lists the five newest text models each provider
still offers, and **Pick your own model** accepts any other id. A monthly
GitHub Action refreshes that list when `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
and `GOOGLE_API_KEY` are set as repository secrets.

## What this is

A minimal Streamlit app that:

1. accepts a user-supplied API key for OpenAI, Anthropic, or Google;
2. ingests a clinical trial protocol (.pdf or .txt);
3. runs the section-by-section SAP generation prompts from the paper; and
4. returns a draft SAP as a `.docx`.

That's it. No autocoding, no chat refinement, no analysis-method extraction.
The KCL production app (`rct-sap-ai/sap-kcl`) does all of that — it iterates
freely without breaking this repo.

## What this is **not**

- Not the live, iterating KCL tool. That lives at
  <https://github.com/rct-sap-ai/sap-kcl> and serves the King's College London
  Clinical Trials Unit.
- Not a replacement for human statistical review. The paper makes the
  strong, evidence-based case that current LLMs are reliable for descriptive
  SAP content (~81–83% accuracy) but only ~67–72% accurate for items
  requiring statistical reasoning. **Every SAP generated here must be
  reviewed by a qualified trial statistician.**

## Provenance of the prompts

`sapai_open/prompts_paper_v1.py` is **byte-identical** to the prompts used
in the validation study (verified by SHA-256, see commit message of initial
commit). The source of record is:

> <https://github.com/rct-sap-ai/sapai-jama-sap-validation> · `Prompts/prompts_05.py`

This file is treated as frozen. Future versions of the prompts will be
published as `prompts_paper_v2.py`, `v3.py`, … without modifying the v1
file.

## Running locally

```bash
git clone https://github.com/rct-sap-ai/sapai-open.git
cd sapai-open
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open <http://localhost:8501> and follow the two-step flow.

## Deployment

The hosted deployment lives at
<https://supportive-recreation-production.up.railway.app/>. Railway builds it
straight from this repo's `main` branch: `railway.json` sets the start command
(`streamlit run streamlit_app.py`) and healthcheck. The app needs no secrets;
users enter their own API keys.

To update the hosted app, merge to `main`; Railway redeploys automatically.

## Repository structure

```
sapai-open/
├── streamlit_app.py          # entry point: `streamlit run streamlit_app.py`
├── pyproject.toml            # pip-install-from-git friendly
├── requirements.txt          # for local dev / Railway pinning
└── sapai_open/
    ├── __init__.py
    ├── app.py                # full Streamlit UI (3-step flow)
    ├── chat.py               # OpenAI / Anthropic / Google wrappers + paper defaults
    ├── pipeline.py           # section-by-section orchestrator
    ├── docx_writer.py        # assembles section outputs into a .docx
    ├── protocol.py           # PDF / TXT protocol loader
    └── prompts_paper_v1.py   # FROZEN: byte-identical copy of validation prompts
```

## Citation

If you use SAPAI or this companion implementation in your work, please cite
the paper above and the relevant repositories
(`rct-sap-ai/sap-kcl`, `rct-sap-ai/validation-study-analysis`,
`rct-sap-ai/sapai-jama-sap-validation`).
