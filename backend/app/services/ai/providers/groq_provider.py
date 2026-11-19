import json
import logging
import time
from typing import Optional
import httpx

from backend.app.schemas.enrichment import EnrichmentOutput, EnrichmentResult, EnrichmentStatus
from backend.app.services.ai.prompts import PROMPT_VERSION, build_enrichment_prompt
from backend.app.services.ai.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """
    Groq LLM provider implementation using fast LPU inference and JSON mode.
    """

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model_name: str = "openai/gpt-oss-120b", timeout_seconds: float = 30.0):
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
                error_message="GROQ_API_KEY is not configured.",
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
            max_attempts = 3
            for attempt in range(max_attempts):
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(self.BASE_URL, headers=headers, json=payload)

                if response.status_code == 429 and attempt < max_attempts - 1:
                    logger.warning(f"Groq Rate limit (429) hit. Waiting 6.0s for token bucket refill (attempt {attempt + 1}/{max_attempts})...")
                    import asyncio
                    await asyncio.sleep(6.0)
                    continue
                break

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code != 200:
                error_body = response.text
                logger.error(f"Groq API error ({response.status_code}): {error_body}")
                return EnrichmentResult(
                    model=self.model_name,
                    prompt_version=PROMPT_VERSION,
                    latency_ms=latency_ms,
                    status=EnrichmentStatus.FAILED,
                    error_message=f"Groq API error HTTP {response.status_code}: {error_body[:200]}",
                )

            res_json = response.json()
            raw_content = res_json["choices"][0]["message"]["content"]
            usage = res_json.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

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
                estimated_cost=0.0,  # Groq free tier
                status=EnrichmentStatus.COMPLETED,
            )

        except json.JSONDecodeError as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Failed to decode JSON from Groq: {exc}")
            return EnrichmentResult(
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                latency_ms=latency_ms,
                status=EnrichmentStatus.FAILED,
                error_message=f"JSON decoding error: {str(exc)}",
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(f"Groq enrichment invocation failed: {exc}")
            return EnrichmentResult(
                model=self.model_name,
                prompt_version=PROMPT_VERSION,
                latency_ms=latency_ms,
                status=EnrichmentStatus.FAILED,
                error_message=str(exc),
            )

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured.")

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        max_attempts = 3
        for attempt in range(max_attempts):
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.BASE_URL, headers=headers, json=payload)

            if response.status_code == 429 and attempt < max_attempts - 1:
                logger.warning(f"Groq Rate limit (429) hit during completion. Waiting 6.0s (attempt {attempt + 1}/{max_attempts})...")
                import asyncio
                await asyncio.sleep(6.0)
                continue
            break

        if response.status_code != 200:
            raise RuntimeError(f"Groq API error HTTP {response.status_code}: {response.text}")

        res_json = response.json()
        return res_json["choices"][0]["message"]["content"]


# Alias for backwards compatibility
GroqAIProvider = GroqProvider
