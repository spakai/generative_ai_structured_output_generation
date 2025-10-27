from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "seed_corpus.json"


@dataclass
class PlanExample:
    id: str
    title: str
    region: str
    tier: str
    devices: int
    price: dict
    video_quality: str
    add_ons: Sequence[dict]
    notes: str

    def as_prompt_snippet(self) -> str:
        add_on_summary = ", ".join(add_on["name"] for add_on in self.add_ons) or "None"
        return (
            f"- {self.title} ({self.region})\n"
            f"  tier: {self.tier}, devices: {self.devices}, quality: {self.video_quality}\n"
            f"  price: {self.price['monthly']} {self.price['currency']}, add-ons: {add_on_summary}\n"
            f"  notes: {self.notes}"
        )


class ExampleRetriever:
    """Lightweight keyword-based retriever for plan examples."""

    def __init__(self, data_path: str | os.PathLike | None = None):
        path = Path(data_path) if data_path else DEFAULT_DATA_PATH
        with path.open("r", encoding="utf-8") as fh:
            raw_examples = json.load(fh)
        self.examples: List[PlanExample] = [PlanExample(**row) for row in raw_examples]
        self.inverted_index = self._build_index(self.examples)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token.lower() for token in re.findall(r"[a-zA-Z]+", text)]

    def _build_index(self, examples: Sequence[PlanExample]) -> dict[str, set[int]]:
        index: dict[str, set[int]] = {}
        for idx, example in enumerate(examples):
            tokens = set(self._tokenize(" ".join([example.title, example.region, example.tier, example.notes])))
            for token in tokens:
                index.setdefault(token, set()).add(idx)
        return index

    def retrieve(self, query: str, top_k: int = 3) -> List[PlanExample]:
        if not query.strip():
            return self.examples[:top_k]
        tokens = self._tokenize(query)
        candidate_indices: set[int] = set()
        for token in tokens:
            candidate_indices.update(self.inverted_index.get(token, set()))
        if not candidate_indices:
            return self.examples[:top_k]

        scored = []
        for idx in candidate_indices:
            example = self.examples[idx]
            score = self._score_example(example, tokens)
            scored.append((score, example))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [example for _, example in scored[:top_k]]

    def _score_example(self, example: PlanExample, tokens: Iterable[str]) -> float:
        text = " ".join([example.title, example.region, example.tier, example.notes]).lower()
        score = 0.0
        for token in tokens:
            occurrences = text.count(token)
            if occurrences:
                score += 1.0 + math.log1p(occurrences)
        score += 0.1 * (example.devices or 0)
        return score

    def to_prompt(self, query: str, top_k: int = 3) -> str:
        examples = self.retrieve(query, top_k=top_k)
        if not examples:
            return "No reference examples available."
        snippets = [example.as_prompt_snippet() for example in examples]
        return "Reference OTT plan examples:\n" + "\n".join(snippets)

