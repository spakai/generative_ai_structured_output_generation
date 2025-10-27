from __future__ import annotations

from typing import List, Tuple

import jsonschema
from jsonschema.exceptions import ValidationError

from .models import PlanDocument
from .schema import PLAN_DOCUMENT_SCHEMA


class PlanValidator:
    """Validates generated plan documents against schema and business rules."""

    def __init__(self):
        self._validator = jsonschema.Draft202012Validator(PLAN_DOCUMENT_SCHEMA)

    def validate(self, payload: dict) -> Tuple[List[str], List[str]]:
        errors = [self._format_error(error) for error in self._validator.iter_errors(payload)]
        warnings: List[str] = []
        if errors:
            return errors, warnings

        document = PlanDocument.model_validate(payload)
        rule_errors, warnings = self._cross_field_rules(document)
        return rule_errors, warnings

    def _cross_field_rules(self, document: PlanDocument) -> Tuple[List[str], List[str]]:
        errors: List[str] = []
        warnings: List[str] = []
        seen_ids = set()
        region_tier_pairs = set()

        for plan in document.plans:
            if plan.id in seen_ids:
                errors.append(f"Duplicate plan id '{plan.id}'.")
            seen_ids.add(plan.id)
            pair = (plan.region.lower(), plan.tier.lower())
            if pair in region_tier_pairs:
                warnings.append(f"Duplicate region/tier combination for {plan.region} {plan.tier}.")
            region_tier_pairs.add(pair)

            tier = plan.tier.lower()
            if tier == "basic" and plan.device_limit > 1:
                errors.append(f"Basic tier plan '{plan.name}' exceeds 1 device limit.")
            if tier == "mobile" and plan.device_limit > 1:
                errors.append(f"Mobile tier plan '{plan.name}' exceeds mobile device policy.")
            if tier in {"premium", "uhd"} and plan.video_quality.upper() not in {"UHD", "4K"}:
                warnings.append(f"Premium tier plan '{plan.name}' should advertise UHD or 4K video quality.")
            if plan.price.monthly == 0 and not plan.add_ons:
                warnings.append(f"Plan '{plan.name}' is free with no add-ons; confirm that is intentional.")
        return errors, warnings

    @staticmethod
    def _format_error(error: ValidationError) -> str:
        path = " > ".join(str(item) for item in error.path)
        prefix = f"{path}: " if path else ""
        return f"{prefix}{error.message}"

