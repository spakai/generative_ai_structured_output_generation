from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable, List, Optional

import yaml

from .llm import BaseLLMClient
from .models import (
    PlanDocument,
    PlanGenerationConfig,
    PlanGenerationResult,
    PlanVariant,
)
from .retrieval import ExampleRetriever
from .validator import PlanValidator

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "base_prompt.txt"


class PlanGenerationError(RuntimeError):
    """Raised when the plan generation pipeline fails."""


class PlanGenerationPipeline:
    """Coordinates retrieval, generation, validation, and repair."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        retriever: Optional[ExampleRetriever] = None,
        config: Optional[PlanGenerationConfig] = None,
        prompt_template_path: Optional[Path] = None,
    ):
        self.llm = llm_client
        self.retriever = retriever or ExampleRetriever()
        self.config = config or PlanGenerationConfig()
        self.validator = PlanValidator()
        template_path = prompt_template_path or PROMPT_PATH
        self.system_prompt = template_path.read_text(encoding="utf-8")

    async def generate_document(
        self,
        user_prompt: str,
        metadata: Optional[dict] = None,
        *,
        max_attempts: Optional[int] = None,
    ) -> PlanGenerationResult:
        attempts = max_attempts or self.config.max_retries
        retrieval_context = self.retriever.to_prompt(
            user_prompt, top_k=self.config.examples_to_include
        )
        prior_yaml: Optional[str] = None
        validation_errors: List[str] = []
        warnings: List[str] = []

        for attempt in range(1, attempts + 1):
            prompt = self._compose_prompt(
                user_prompt=user_prompt,
                retrieval_context=retrieval_context,
                attempt=attempt,
                prior_yaml=prior_yaml,
                validation_errors=validation_errors,
            )
            try:
                yaml_output = await self.llm.generate(prompt)
            except Exception as exc:  # pragma: no cover - network errors covered via raise
                raise PlanGenerationError(f"LLM request failed: {exc}") from exc
            prior_yaml = yaml_output
            payload, parse_error = self._parse_yaml(yaml_output)
            if parse_error:
                validation_errors = [parse_error]
                continue

            if metadata:
                payload.setdefault("metadata", {}).update(metadata)

            validation_errors, warnings = self.validator.validate(payload)
            if not validation_errors:
                document = PlanDocument.model_validate(payload)
                return PlanGenerationResult(
                    prompt=user_prompt,
                    yaml_output=yaml_output,
                    document=document,
                    validation_warnings=warnings,
                )

        raise PlanGenerationError(
            f"Unable to generate a valid plan after {attempts} attempts: {validation_errors}"
        )

    async def generate_ab_variants(
        self,
        user_prompt: str,
        labels: Optional[Iterable[str]] = None,
    ) -> List[PlanVariant]:
        if not self.config.enable_ab_testing:
            raise PlanGenerationError("A/B testing disabled in configuration.")
        labels = list(labels or ("A", "B"))
        instructions = {
            "A": "Optimize for entry-level affordability and retention.",
            "B": "Optimize for premium upsell and average revenue per user.",
        }
        tasks = []
        for label in labels:
            focus = instructions.get(label, f"Variant {label} should explore a distinct positioning.")
            variant_prompt = f"{user_prompt}\n\nFocus for variant {label}: {focus}"
            metadata = {"variant_label": label, "variant_focus": focus}
            tasks.append(self.generate_document(variant_prompt, metadata=metadata))

        results = await asyncio.gather(*tasks)
        variants: List[PlanVariant] = []
        for label, result in zip(labels, results):
            justification = await self._generate_justification(label, result)
            variants.append(PlanVariant(label=label, result=result, justification=justification))
        return variants

    async def _generate_justification(self, label: str, result: PlanGenerationResult) -> str:
        prompt = (
            "You are reviewing a streaming subscription plan proposal.\n"
            f"Variant {label} YAML:\n```yaml\n{result.yaml_output}\n```\n"
            "Write 2 bullet sentences explaining the core positioning for stakeholders."
        )
        try:
            response = await self.llm.generate(prompt, temperature=0.2)
            return response.strip()
        except Exception:
            return self._fallback_justification(result)

    @staticmethod
    def _fallback_justification(result: PlanGenerationResult) -> str:
        plans = result.document.plans
        monthly_prices = [plan.price.monthly for plan in plans]
        min_price = min(monthly_prices)
        max_price = max(monthly_prices)
        return (
            "• Mix of tiers from affordable to premium to cover audience breadth.\n"
            f"• Pricing spectrum spans {min_price:.2f} to {max_price:.2f} {plans[0].price.currency}."
        )

    def _compose_prompt(
        self,
        *,
        user_prompt: str,
        retrieval_context: str,
        attempt: int,
        prior_yaml: Optional[str],
        validation_errors: List[str],
    ) -> str:
        sections = [
            self.system_prompt.strip(),
            "\n---\nUser brief:\n" + user_prompt.strip(),
            "\n---\n" + retrieval_context.strip(),
            "\n---\nYAML Schema (simplified view):\n"
            "plans:\n"
            "  - id: string\n"
            "    name: string\n"
            "    region: string\n"
            "    tier: string\n"
            "    price:\n"
            "      monthly: number\n"
            "      currency: ISO-4217 code\n"
            "    device_limit: integer <= 8\n"
            "    video_quality: string\n"
            "    add_ons:\n"
            "      - name: string\n"
            "        price_delta: number\n",
        ]

        if attempt > 1 and prior_yaml:
            error_block = "\n".join(f"- {err}" for err in validation_errors) or "- Invalid output."
            sections.append(
                "\n---\nPrevious YAML (attempt failed validation):\n"
                f"{prior_yaml.strip()}\n"
                "\nValidation feedback:\n"
                f"{error_block}\n"
                "Revise the YAML to resolve the issues."
            )
        else:
            sections.append("\nDraft fresh YAML plan proposals adhering to the schema.")

        return "\n".join(sections)

    @staticmethod
    def _parse_yaml(raw_yaml: str) -> tuple[dict, Optional[str]]:
        normalized = PlanGenerationPipeline._strip_code_fence(raw_yaml)
        try:
            data = yaml.safe_load(normalized)
        except yaml.YAMLError as exc:
            return {}, f"YAML parse error: {exc}"
        if not isinstance(data, dict):
            return {}, "Model output must be a YAML mapping/object."
        return data, None

    @staticmethod
    def _strip_code_fence(raw_yaml: str) -> str:
        stripped = raw_yaml.strip()
        if not stripped.startswith("```"):
            return raw_yaml
        lines = stripped.splitlines()
        fence = lines[0]
        if not fence.startswith("```"):
            return raw_yaml

        closing_index = None
        for idx in range(len(lines) - 1, 0, -1):
            if lines[idx].startswith("```"):
                closing_index = idx
                break

        if closing_index is None:
            body = lines[1:]
        else:
            body = lines[1:closing_index]
        return "\n".join(body).strip()
