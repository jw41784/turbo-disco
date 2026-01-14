"""
Anthropic Claude API client with retry logic and rate limiting.
"""

import time
import logging
from typing import Optional

from anthropic import Anthropic, APIError, RateLimitError

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Claude API with production-ready error handling."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = 3
        self.base_delay = 1.0  # seconds

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> str:
        """
        Generate text with automatic retry on rate limits.

        Args:
            prompt: User message content
            max_tokens: Maximum response length
            temperature: Creativity (0.0-1.0)
            system: Optional system prompt

        Returns:
            Generated text content
        """
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system or "",
                    messages=messages,
                )
                return response.content[0].text

            except RateLimitError:
                delay = self.base_delay * (2**attempt)
                logger.warning(f"Rate limited, waiting {delay}s (attempt {attempt + 1})")
                time.sleep(delay)

            except APIError as e:
                logger.error(f"API error: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.base_delay)

        raise RuntimeError("Max retries exceeded")

    def batch_generate(
        self, prompts: list[str], delay_between: float = 0.5, **kwargs
    ) -> list[str]:
        """Generate responses for multiple prompts with rate limiting."""
        results = []
        for i, prompt in enumerate(prompts):
            logger.debug(f"Processing prompt {i + 1}/{len(prompts)}")
            result = self.generate(prompt, **kwargs)
            results.append(result)
            if i < len(prompts) - 1:
                time.sleep(delay_between)
        return results
