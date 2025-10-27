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

## Example Prompts and Responses

### 1. US Holiday Season Plans

**Request**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Launch plans for the US holiday season"}'
```

**Response**
```json
{
  "yaml": "```yaml\nmetadata:\n  proposal_rationale: \"Introducing new streaming subscription plans tailored for the US holiday season to attract a wider audience and accommodate varying viewing preferences.\"\n\nplans:\n  - id: \"us-holiday-standard\"\n    name: \"US Holiday Standard Plan\"\n    region: \"United States\"\n    tier: \"Standard\"\n    price:\n      monthly: 14.99\n      currency: \"USD\"\n    device_limit: 2\n    video_quality: \"HD\"\n    add_ons:\n      - name: \"Extra Profile Pack\"\n        price_delta: 2.00\n      - name: \"Premium Sports\"\n        price_delta: 5.00\n\n  - id: \"us-holiday-basic\"\n    name: \"US Holiday Basic Plan\"\n    region: \"United States\"\n    tier: \"Basic\"\n    price:\n      monthly: 9.99\n      currency: \"USD\"\n    device_limit: 1\n    video_quality: \"SD\"\n    add_ons:\n      - name: \"Offline Downloads\"\n        price_delta: 1.00\n\n  - id: \"us-holiday-mobile\"\n    name: \"US Holiday Mobile Plan\"\n    region: \"United States\"\n    tier: \"Mobile\"\n    price:\n      monthly: 5.99\n      currency: \"USD\"\n    device_limit: 1\n    video_quality: \"SD\"\n    add_ons:\n      - name: \"Extra Mobile Data\"\n        price_delta: 2.00\n```",
  "warnings": [],
  "document": {
    "version": "1.0",
    "plans": [
      {
        "id": "us-holiday-standard",
        "name": "US Holiday Standard Plan",
        "region": "United States",
        "tier": "Standard",
        "price": {"monthly": 14.99, "currency": "USD"},
        "device_limit": 2,
        "video_quality": "HD",
        "add_ons": [
          {"name": "Extra Profile Pack", "price_delta": 2.0, "description": null},
          {"name": "Premium Sports", "price_delta": 5.0, "description": null}
        ],
        "description": null
      },
      {
        "id": "us-holiday-basic",
        "name": "US Holiday Basic Plan",
        "region": "United States",
        "tier": "Basic",
        "price": {"monthly": 9.99, "currency": "USD"},
        "device_limit": 1,
        "video_quality": "SD",
        "add_ons": [
          {"name": "Offline Downloads", "price_delta": 1.0, "description": null}
        ],
        "description": null
      },
      {
        "id": "us-holiday-mobile",
        "name": "US Holiday Mobile Plan",
        "region": "United States",
        "tier": "Mobile",
        "price": {"monthly": 5.99, "currency": "USD"},
        "device_limit": 1,
        "video_quality": "SD",
        "add_ons": [
          {"name": "Extra Mobile Data", "price_delta": 2.0, "description": null}
        ],
        "description": null
      }
    ],
    "metadata": {
      "proposal_rationale": "Introducing new streaming subscription plans tailored for the US holiday season to attract a wider audience and accommodate varying viewing preferences."
    }
  }
}
```

### 2. APAC Summer Travel Bundles

**Request**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Design bundled streaming plans for the APAC summer travel season with cross-device perks"}'
```

**Response**
```json
{
  "yaml": "```yaml\nmetadata:\n  proposal_rationale: \"Designed for the APAC summer travel season, these bundled streaming plans offer cross-device perks to enhance user experience while traveling.\"\n\nplans:\n  - id: \"apac_summer_mobile\"\n    name: \"APAC Summer Mobile Plan\"\n    region: \"Asia Pacific\"\n    tier: \"Mobile\"\n    price:\n      monthly: 5.99\n      currency: \"USD\"\n    device_limit: 1\n    video_quality: \"SD\"\n    add_ons:\n      - name: \"Extra Mobile Data\"\n        price_delta: 2.00\n\n  - id: \"apac_summer_family\"\n    name: \"APAC Summer Family Plan\"\n    region: \"Asia Pacific\"\n    tier: \"Family\"\n    price:\n      monthly: 12.99\n      currency: \"USD\"\n    device_limit: 4\n    video_quality: \"HD\"\n    add_ons:\n      - name: \"Kids Pack\"\n        price_delta: 3.00\n      - name: \"Premier Sports\"\n        price_delta: 5.00\n\n  - id: \"apac_summer_standard\"\n    name: \"APAC Summer Standard Plan\"\n    region: \"Asia Pacific\"\n    tier: \"Standard\"\n    price:\n      monthly: 14.99\n      currency: \"USD\"\n    device_limit: 2\n    video_quality: \"HD\"\n    add_ons:\n      - name: \"Extra Profile Pack\"\n        price_delta: 2.50\n      - name: \"Premium Sports\"\n        price_delta: 4.00\n```",
  "warnings": [],
  "document": {
    "version": "1.0",
    "plans": [
      {
        "id": "apac_summer_mobile",
        "name": "APAC Summer Mobile Plan",
        "region": "Asia Pacific",
        "tier": "Mobile",
        "price": {"monthly": 5.99, "currency": "USD"},
        "device_limit": 1,
        "video_quality": "SD",
        "add_ons": [
          {"name": "Extra Mobile Data", "price_delta": 2.0, "description": null}
        ],
        "description": null
      },
      {
        "id": "apac_summer_family",
        "name": "APAC Summer Family Plan",
        "region": "Asia Pacific",
        "tier": "Family",
        "price": {"monthly": 12.99, "currency": "USD"},
        "device_limit": 4,
        "video_quality": "HD",
        "add_ons": [
          {"name": "Kids Pack", "price_delta": 3.0, "description": null},
          {"name": "Premier Sports", "price_delta": 5.0, "description": null}
        ],
        "description": null
      },
      {
        "id": "apac_summer_standard",
        "name": "APAC Summer Standard Plan",
        "region": "Asia Pacific",
        "tier": "Standard",
        "price": {"monthly": 14.99, "currency": "USD"},
        "device_limit": 2,
        "video_quality": "HD",
        "add_ons": [
          {"name": "Extra Profile Pack", "price_delta": 2.5, "description": null},
          {"name": "Premium Sports", "price_delta": 4.0, "description": null}
        ],
        "description": null
      }
    ],
    "metadata": {
      "proposal_rationale": "Designed for the APAC summer travel season, these bundled streaming plans offer cross-device perks to enhance user experience while traveling."
    }
  }
}
```
