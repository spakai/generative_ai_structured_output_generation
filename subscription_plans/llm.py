from __future__ import annotations

import abc
import os
from typing import Any, Dict, Optional
import httpx


class BaseLLMClient(abc.ABC):
    """Abstraction for an LLM client used by the pipeline."""

    @abc.abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """Deterministic client for testing."""

    def __init__(self, scripted_completions: list[str]):
        self._responses = scripted_completions
        self._cursor = 0

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if self._cursor >= len(self._responses):
            raise RuntimeError("MockLLMClient exhausted responses.")
        response = self._responses[self._cursor]
        self._cursor += 1
        return response


class GitHubModelsLLMClient(BaseLLMClient):
    """
    Minimal GitHub Models client using the chat completions endpoint.

    Requires a GitHub personal access token or fine-grained token with the
    `read:org` scope (for enterprise) or default public model access.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.model = model
        self.temperature = temperature
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not self.token:
            raise ValueError("GitHub token required for GitHubModelsLLMClient.")
        env_base = os.getenv("GITHUB_MODELS_BASE_URL")
        resolved = base_url or env_base or "https://api.githubcopilot.com"
        self.base_url = resolved.rstrip("/")
        env_endpoint = os.getenv("GITHUB_MODELS_ENDPOINT")
        self.endpoint = (endpoint or env_endpoint or "").strip() or None
        self.timeout = timeout

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2023-12-01",
            "User-Agent": "subscription-plans/0.1.0",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a pricing strategist producing YAML."},
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", self.temperature),
        }
        target_url = self.endpoint or f"{self.base_url}/v1/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(target_url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {401, 403, 404}:
                raise RuntimeError(
                    "GitHub Models API returned "
                    f"{status}. Check that your token has GitHub Models access "
                    "and that the base URL is correct (set GITHUB_MODELS_BASE_URL if needed)."
                ) from exc
            raise
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Failed to call GitHub Models API: {exc}") from exc
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected response format from GitHub Models: {data}") from exc
