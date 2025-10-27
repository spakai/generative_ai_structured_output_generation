# Subscription Plan Generator

Streaming subscription plan generator that orchestrates retrieval-augmented prompting, JSON schema validation, automatic repair, and a FastAPI service layer. Designed for OTT/telco style pricing workflows.

## Features

- Retrieval of curated OTT plan examples to ground prompts.
- YAML drafting via GitHub Models (with offline-safe mock fallback).
- JSON Schema + cross-field validation (e.g., `Basic` plans limited to 1 device).
- Automatic repair cycle that re-prompts with validation feedback.
- A/B proposal generation with short stakeholder justification blurbs.
- FastAPI service exposing `/generate` and `/generate-ab` endpoints.
- Pytest suite and GitHub Actions CI workflow.

## Getting Started

1. Create and activate a virtual environment (Python 3.10+):

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```

   (On Windows use `.venv\Scripts\activate`.)

2. Install dependencies:

   ```bash
   pip install -e .[dev]
   ```

3. Export a GitHub token with model access:

   ```bash
   export GITHUB_TOKEN=ghp_...
   ```

   The API first tries GitHub Models (`GITHUB_TOKEN` or `GH_TOKEN`); if unavailable it falls back to a static mock response (useful for offline/local development).

   > If you receive a 401/403/404 error when calling the API, ensure your token was created from the [GitHub Models beta](https://github.com/settings/tokens?type=beta) and includes access to the models endpoint. You can override the host with `GITHUB_MODELS_BASE_URL`, or supply a full path via `GITHUB_MODELS_ENDPOINT` (e.g., `https://models.github.ai/inference/chat/completions`) when targeting enterprise proxies.

4. Run the API service:

   ```bash
   uvicorn subscription_plans.api:create_app --factory
   ```

5. Call the API:

   ```bash
   curl -X POST http://localhost:8000/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Launch plans for the US holiday season"}'
   ```

## Testing

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
pytest
```

## Configuration Notes
- The pipeline configuration lives in `PlanGenerationConfig`. Adjust retries, example counts, or disable A/B generation as required.
- LLM client selection is automatic: GitHub Models (`gpt-4o-mini`) → static mock. Override by supplying a custom `BaseLLMClient`.
- Set `GITHUB_MODELS_BASE_URL` (host) or `GITHUB_MODELS_ENDPOINT` (full URL) to point at a custom GitHub Models endpoint if your organization proxies requests.
- To integrate with GitHub Actions, see `.github/workflows/ci.yml`.
- For custom LLM providers, implement `BaseLLMClient.generate` and pass it into `create_app`.

## How the Plans Are Generated
- We ship a small seed corpus (`subscription_plans/data/seed_corpus.json`) containing representative OTT/telco plans. Each entry provides tier names, pricing, device limits, add-ons, and notes.
- When you call `/generate`, the retriever selects the most relevant examples and injects them into the LLM prompt alongside your user brief. The prompt also includes the YAML schema summary so the model stays on structure.
- The LLM drafts YAML by analogizing from those grounded examples. Validation ensures the output matches the schema and business rules; failures trigger an automatic repair prompt with error feedback.
- Because we ground the model every time, the generated plans stay aligned with the corpus style—sensible tiers, realistic prices, compliant device limits—without needing to fine-tune the model itself.
