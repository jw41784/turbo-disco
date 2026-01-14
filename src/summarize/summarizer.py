"""
Main summarization orchestrator.
Processes grants in batches with intelligent content generation.
"""

import logging
from datetime import datetime
from typing import Optional

from .claude_client import ClaudeClient
from .prompts import (
    SYSTEM_PROMPT,
    GRANT_SUMMARY_PROMPT,
    FEATURED_OPPORTUNITY_PROMPT,
    DEADLINE_ALERT_PROMPT,
    TIP_OF_THE_WEEK_PROMPT,
    QUICK_HIT_PROMPT,
)
from .content_types import GrantSummary, FeaturedOpportunity, DeadlineAlert

logger = logging.getLogger(__name__)


class GrantSummarizer:
    """Orchestrates AI summarization for grants."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = ClaudeClient(api_key=api_key, model=model)

    def summarize_grant(self, grant: dict) -> GrantSummary:
        """Generate 75-100 word summary for a single grant."""
        prompt = GRANT_SUMMARY_PROMPT.format(
            title=grant.get("title", ""),
            agency=grant.get("agency", ""),
            cfda_numbers=grant.get("cfda_numbers", ""),
            description=self._truncate(grant.get("description", ""), 2000),
            award_range=self._format_award_range(grant),
            expected_awards=grant.get("expected_awards") or "Not specified",
            close_date=grant.get("close_date") or "Rolling",
            eligibility_codes=grant.get("eligibility_codes", ""),
        )

        summary_text = self.client.generate(
            prompt=prompt, system=SYSTEM_PROMPT, max_tokens=200, temperature=0.6
        )

        return GrantSummary(
            opportunity_id=grant["opportunity_id"],
            title=grant["title"],
            agency=grant["agency"],
            summary_text=summary_text.strip(),
            deadline=grant.get("close_date"),
            award_range=self._format_award_range(grant),
            url=grant.get("url", ""),
            match_type=grant.get("match_type", ""),
            match_value=grant.get("match_value", ""),
        )

    def generate_featured(self, grant: dict) -> FeaturedOpportunity:
        """Generate 150-200 word featured opportunity writeup."""
        prompt = FEATURED_OPPORTUNITY_PROMPT.format(
            title=grant.get("title", ""),
            agency=grant.get("agency", ""),
            description=self._truncate(grant.get("description", ""), 3000),
            award_range=self._format_award_range(grant),
            expected_awards=grant.get("expected_awards") or "Not specified",
            close_date=grant.get("close_date") or "Rolling",
            url=grant.get("url", ""),
        )

        text = self.client.generate(
            prompt=prompt, system=SYSTEM_PROMPT, max_tokens=400, temperature=0.7
        )

        return FeaturedOpportunity(
            opportunity_id=grant["opportunity_id"],
            title=grant["title"],
            featured_text=text.strip(),
            url=grant.get("url", ""),
        )

    def generate_deadline_alert(self, grant: dict) -> DeadlineAlert:
        """Generate 2-sentence deadline alert."""
        prompt = DEADLINE_ALERT_PROMPT.format(
            title=grant.get("title", ""),
            agency=grant.get("agency", ""),
            award_ceiling=self._format_amount(grant.get("award_ceiling")),
            close_date=grant.get("close_date", ""),
            eligibility_codes=grant.get("eligibility_codes", ""),
        )

        text = self.client.generate(
            prompt=prompt, system=SYSTEM_PROMPT, max_tokens=100, temperature=0.5
        )

        days_until = self._calculate_days_until(grant.get("close_date"))

        return DeadlineAlert(
            opportunity_id=grant["opportunity_id"],
            title=grant["title"],
            alert_text=text.strip(),
            deadline=grant.get("close_date", ""),
            days_until=days_until,
        )

    def generate_tip_of_week(self, grant_titles: list[str]) -> str:
        """Generate actionable tip based on this week's grants."""
        prompt = TIP_OF_THE_WEEK_PROMPT.format(
            grant_titles="\n".join(f"- {t}" for t in grant_titles[:5])
        )

        return self.client.generate(
            prompt=prompt, system=SYSTEM_PROMPT, max_tokens=150, temperature=0.8
        ).strip()

    def generate_quick_hit(self, grant: dict) -> str:
        """Generate one-liner summary."""
        prompt = QUICK_HIT_PROMPT.format(
            title=grant.get("title", ""),
            award_ceiling=self._format_amount(grant.get("award_ceiling")),
            close_date=grant.get("close_date") or "Open",
        )

        return self.client.generate(
            prompt=prompt, system=SYSTEM_PROMPT, max_tokens=60, temperature=0.5
        ).strip()

    def process_batch(self, grants: list[dict]) -> list[GrantSummary]:
        """Process multiple grants with progress logging."""
        summaries = []
        for i, grant in enumerate(grants):
            logger.info(
                f"Summarizing grant {i + 1}/{len(grants)}: {grant['title'][:50]}..."
            )
            try:
                summary = self.summarize_grant(grant)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to summarize {grant['opportunity_id']}: {e}")
        return summaries

    def _format_award_range(self, grant: dict) -> str:
        """Format award range for display."""
        floor = grant.get("award_floor")
        ceiling = grant.get("award_ceiling")
        if ceiling:
            if floor:
                return f"${floor:,} - ${ceiling:,}"
            return f"Up to ${ceiling:,}"
        return "Amount varies"

    def _format_amount(self, amount: Optional[int]) -> str:
        """Format single amount for display."""
        if amount:
            return f"${amount:,}"
        return "Amount varies"

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _calculate_days_until(self, close_date: Optional[str]) -> int:
        """Calculate days until deadline."""
        if not close_date:
            return 999
        try:
            deadline = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
            delta = deadline - datetime.now(deadline.tzinfo)
            return max(0, delta.days)
        except (ValueError, TypeError):
            return 999
