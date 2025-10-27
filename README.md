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

1. Install dependencies (Python 3.10+):

   ```bash
   pip install -e .[dev]
   ```

2. Export a GitHub token with model access:

   ```bash
   export GITHUB_TOKEN=ghp_...
   ```

   The API first tries GitHub Models (`GITHUB_TOKEN` or `GH_TOKEN`); if unavailable it falls back to a static mock response (useful for offline/local development).

3. Run the API service:

   ```bash
   uvicorn subscription_plans.api:create_app --factory
   ```

4. Call the API:

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
- To integrate with GitHub Actions, see `.github/workflows/ci.yml`.
- For custom LLM providers, implement `BaseLLMClient.generate` and pass it into `create_app`.
