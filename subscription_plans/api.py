from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .llm import BaseLLMClient, GitHubModelsLLMClient, MockLLMClient
from .models import PlanDocument, PlanGenerationConfig
from .pipeline import PlanGenerationPipeline, PlanGenerationError


class GenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=5)
    max_attempts: Optional[int] = Field(default=None, ge=1, le=6)
    metadata: Optional[dict] = None


class GenerationResponse(BaseModel):
    yaml: str
    warnings: list[str]
    document: PlanDocument


class ABGenerationResponse(BaseModel):
    variants: list[dict]


def create_app(
    *,
    llm_client: Optional[BaseLLMClient] = None,
    config: Optional[PlanGenerationConfig] = None,
) -> FastAPI:
    app = FastAPI(title="Subscription Plan Generator", version="0.1.0")

    @lru_cache
    def get_pipeline() -> PlanGenerationPipeline:
        client = llm_client or _default_llm_client()
        return PlanGenerationPipeline(client, config=config)

    @app.get("/health")
    async def health() -> dict:
        pipeline = get_pipeline()
        return {"status": "ok", "ab_testing": pipeline.config.enable_ab_testing}

    @app.post("/generate", response_model=GenerationResponse)
    async def generate(request: GenerationRequest, pipeline: PlanGenerationPipeline = Depends(get_pipeline)):
        try:
            result = await pipeline.generate_document(
                request.prompt,
                metadata=request.metadata,
                max_attempts=request.max_attempts,
            )
            return GenerationResponse(yaml=result.yaml_output, warnings=result.validation_warnings, document=result.document)
        except PlanGenerationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/generate-ab", response_model=ABGenerationResponse)
    async def generate_ab(
        request: GenerationRequest,
        pipeline: PlanGenerationPipeline = Depends(get_pipeline),
    ):
        try:
            variants = await pipeline.generate_ab_variants(request.prompt)
            payload = [
                {
                    "label": variant.label,
                    "yaml": variant.result.yaml_output,
                    "warnings": variant.result.validation_warnings,
                    "document": variant.result.document,
                    "justification": variant.justification,
                }
                for variant in variants
            ]
            return ABGenerationResponse(variants=payload)
        except PlanGenerationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def _default_llm_client() -> BaseLLMClient:
    try:
        return GitHubModelsLLMClient()
    except Exception:
        # Provide a friendly fallback for local dev.
        fallback_yaml = """
version: "1.0"
plans:
  - id: "dev-basic"
    name: "Developer Basic"
    region: "Local"
    tier: "Basic"
    price:
      monthly: 9.0
      currency: "USD"
    device_limit: 1
    video_quality: "HD"
    add_ons: []
metadata:
  note: "Fallback static plan because real LLM is unavailable."
"""
        return MockLLMClient([fallback_yaml])
