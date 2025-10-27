import pytest
import pytest_asyncio

from subscription_plans.llm import MockLLMClient
from subscription_plans.pipeline import PlanGenerationPipeline, PlanGenerationConfig


@pytest_asyncio.fixture
async def pipeline():
    # First response missing device_limit, second response fixes it.
    scripted = [
        """
version: "1.0"
plans:
  - id: "basic"
    name: "Basic Plan"
    region: "US"
    tier: "Basic"
    price:
      monthly: 9.0
      currency: "USD"
    video_quality: "HD"
    add_ons: []
""",
        """
version: "1.0"
plans:
  - id: "basic"
    name: "Basic Plan"
    region: "US"
    tier: "Basic"
    price:
      monthly: 9.0
      currency: "USD"
    device_limit: 1
    video_quality: "HD"
    add_ons: []
""",
    ]
    client = MockLLMClient(scripted)
    return PlanGenerationPipeline(client, config=PlanGenerationConfig(max_retries=2))


@pytest.mark.asyncio
async def test_pipeline_auto_repairs_invalid_yaml(pipeline):
    result = await pipeline.generate_document("Design a basic plan for US market.")

    assert result.document.plans[0].device_limit == 1
    assert result.validation_warnings == []


@pytest.mark.asyncio
async def test_ab_generation_produces_variants():
    scripted = [
        """
version: "1.0"
plans:
  - id: "variant-a"
    name: "Variant A"
    region: "US"
    tier: "Basic"
    price:
      monthly: 8.0
      currency: "USD"
    device_limit: 1
    video_quality: "HD"
    add_ons: []
""",
        """
version: "1.0"
plans:
  - id: "variant-b"
    name: "Variant B"
    region: "US"
    tier: "Premium"
    price:
      monthly: 16.0
      currency: "USD"
    device_limit: 4
    video_quality: "UHD"
    add_ons: []
""",
        "Variant A focuses on affordability.\nVariant A upsell path via add-ons.",
        "Variant B focuses on upsell.\nVariant B leverages UHD quality.",
    ]
    pipeline = PlanGenerationPipeline(
        MockLLMClient(scripted),
        config=PlanGenerationConfig(max_retries=1),
    )

    variants = await pipeline.generate_ab_variants("Create US plans for testing.")

    assert len(variants) == 2
    assert {variant.label for variant in variants} == {"A", "B"}
    assert variants[0].result.document.plans
    assert "Variant" in variants[0].justification
