import json
import logging
import time
from typing import Optional
import httpx

from backend.app.schemas.enrichment import EnrichmentOutput, EnrichmentResult, EnrichmentStatus
from backend.app.services.ai.prompts import PROMPT_VERSION, build_enrichment_prompt
from backend.app.services.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI provider implementation supporting GPT-4o, GPT-4o-mini with JSON schema / json_object.
    """

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    # Cost per 1M tokens (approx. for gpt-4o-mini)
    INPUT_COST_PER_1M = 0.150
    OUTPUT_COST_PER_1M = 0.600

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", timeout_seconds: float = 30.0):
        super().__init__(model_name=model_name)
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def enrich_article(
        self,
        title: str,
        description: str = "",
        content: str = "",
    ) -> EnrichmentResult:
        if not self.api_key:
            return EnrichmentResult(
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                status=EnrichmentStatus.FAILED,
                error_message="OPENAI_API_KEY is not configured.",
            )

        system_prompt, user_prompt = build_enrichment_prompt(title, description, content)

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 1500,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.BASE_URL, headers=headers, json=payload)

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code != 200:
                error_body = response.text
                logger.error(f"OpenAI API error ({response.status_code}): {error_body}")
                return EnrichmentResult(
                    model=self.model_name,
                    prompt_version=PROMPT_VERSION,
                    latency_ms=latency_ms,
                    status=EnrichmentStatus.FAILED,
                    error_message=f"OpenAI error HTTP {response.status_code}: {error_body[:200]}",
                )

            res_json = response.json()
            raw_content = res_json["choices"][0]["message"]["content"]
            usage = res_json.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            # Estimate cost
            estimated_cost = (
                (prompt_tokens / 1_000_000.0) * self.INPUT_COST_PER_1M
                + (completion_tokens / 1_000_000.0) * self.OUTPUT_COST_PER_1M
            )

            # Parse and validate with Pydantic
            parsed_data = json.loads(raw_content)
            enrichment_output = EnrichmentOutput.model_validate(parsed_data)

            return EnrichmentResult(
                enrichment=enrichment_output,
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                latency_ms=latency_ms,
                estimated_cost=estimated_cost,
                status=EnrichmentStatus.COMPLETED,
            )

        except json.JSONDecodeError as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Failed to decode JSON from OpenAI: {exc}")
            return EnrichmentResult(
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                latency_ms=latency_ms,
                status=EnrichmentStatus.FAILED,
                error_message=f"JSON decoding error: {str(exc)}",
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(f"OpenAI enrichment invocation failed: {exc}")
            return EnrichmentResult(
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                latency_ms=latency_ms,
                status=EnrichmentStatus.FAILED,
                error_message=str(exc),
            )
