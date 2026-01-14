"""
Newsletter composition from approved grants.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from ..summarize.summarizer import GrantSummarizer
from ..summarize.content_types import (
    NewsletterContent,
    GrantSummary,
    FeaturedOpportunity,
    DeadlineAlert,
)
from .templates import (
    NEWSLETTER_TEMPLATE,
    FEATURED_SECTION,
    OPPORTUNITY_ITEM,
    DEADLINE_SECTION,
    DEADLINE_ITEM,
    QUICK_HITS_SECTION,
    QUICK_HIT_ITEM,
)

logger = logging.getLogger(__name__)


class NewsletterComposer:
    """Composes newsletter from approved grants."""

    def __init__(self, summarizer: GrantSummarizer):
        self.summarizer = summarizer

    def compose(
        self, approved_grants: list[dict]
    ) -> tuple[str, str, NewsletterContent]:
        """
        Compose newsletter from approved grants.

        Args:
            approved_grants: List of approved grant dicts with summaries

        Returns:
            (subject_line, html_content, content_data)
        """
        if not approved_grants:
            raise ValueError("No approved grants to compose newsletter")

        logger.info(f"Composing newsletter from {len(approved_grants)} grants")

        # Sort and categorize grants
        sorted_grants = self._sort_grants(approved_grants)

        # Select grants for each section
        featured_grant = self._select_featured(sorted_grants)
        new_opportunities = self._select_opportunities(sorted_grants, featured_grant)
        deadline_grants = self._get_deadline_alerts(sorted_grants)
        quick_hit_grants = self._select_quick_hits(sorted_grants, new_opportunities)

        # Generate content
        featured = None
        if featured_grant:
            logger.info(f"Generating featured content for: {featured_grant['title']}")
            featured = self.summarizer.generate_featured(featured_grant)

        # Generate summaries for opportunities that don't have them
        summaries = []
        for grant in new_opportunities:
            if grant.get("summary"):
                # Use existing summary
                summaries.append(
                    GrantSummary(
                        opportunity_id=grant["opportunity_id"],
                        title=grant["title"],
                        agency=grant["agency"],
                        summary_text=grant["summary"],
                        deadline=grant.get("close_date"),
                        award_range=self._format_award_range(grant),
                        url=grant.get("url", ""),
                        match_type=grant.get("match_type", ""),
                        match_value=grant.get("match_value", ""),
                    )
                )
            else:
                summary = self.summarizer.summarize_grant(grant)
                summaries.append(summary)

        # Generate deadline alerts
        deadline_alerts = []
        for grant in deadline_grants[:3]:
            alert = self.summarizer.generate_deadline_alert(grant)
            deadline_alerts.append(alert)

        # Generate quick hits
        quick_hits = []
        for grant in quick_hit_grants[:5]:
            hit = self.summarizer.generate_quick_hit(grant)
            quick_hits.append(hit)

        # Generate tip
        grant_titles = [g["title"] for g in approved_grants[:5]]
        tip = self.summarizer.generate_tip_of_week(grant_titles)

        # Build content object
        content = NewsletterContent(
            issue_date=datetime.now().strftime("%B %d, %Y"),
            featured=featured,
            new_opportunities=summaries,
            deadline_alerts=deadline_alerts,
            quick_hits=quick_hits,
            tip_of_the_week=tip,
        )

        # Render HTML
        html = self._render_html(content)

        logger.info(
            f"Newsletter composed: {len(summaries)} opportunities, "
            f"{len(deadline_alerts)} deadline alerts, {len(quick_hits)} quick hits"
        )

        return content.subject_line, html, content

    def _sort_grants(self, grants: list[dict]) -> list[dict]:
        """Sort grants by importance: CFDA first, then by deadline."""

        def sort_key(g):
            # Priority: CFDA > primary_keyword > secondary_keyword
            type_order = {"cfda": 0, "primary_keyword": 1, "secondary_keyword": 2}
            type_score = type_order.get(g.get("match_type", ""), 3)

            # Secondary sort by award amount (higher first)
            amount = g.get("award_ceiling") or 0

            return (type_score, -amount)

        return sorted(grants, key=sort_key)

    def _select_featured(self, grants: list[dict]) -> Optional[dict]:
        """Select the most notable grant for featured section."""
        # Prefer: highest funding, CFDA match, upcoming deadline
        for grant in grants:
            ceiling = grant.get("award_ceiling") or 0
            if ceiling >= 1_000_000:  # $1M+ is notable
                return grant

        # Fall back to first CFDA match
        for grant in grants:
            if grant.get("match_type") == "cfda":
                return grant

        # Fall back to first grant
        return grants[0] if grants else None

    def _select_opportunities(
        self, grants: list[dict], featured: Optional[dict], max_count: int = 5
    ) -> list[dict]:
        """Select grants for new opportunities section."""
        featured_id = featured["opportunity_id"] if featured else None
        return [g for g in grants if g["opportunity_id"] != featured_id][:max_count]

    def _get_deadline_alerts(self, grants: list[dict]) -> list[dict]:
        """Get grants with deadlines in next 14 days."""
        today = datetime.now()
        cutoff = today + timedelta(days=14)

        alerts = []
        for grant in grants:
            close_date = grant.get("close_date")
            if close_date:
                try:
                    deadline = datetime.fromisoformat(close_date.replace("Z", ""))
                    if today <= deadline <= cutoff:
                        grant["days_until"] = (deadline - today).days
                        alerts.append(grant)
                except (ValueError, TypeError):
                    pass

        return sorted(alerts, key=lambda g: g.get("days_until", 999))

    def _select_quick_hits(
        self, grants: list[dict], exclude: list[dict]
    ) -> list[dict]:
        """Select grants for quick hits (one-liners)."""
        exclude_ids = {g["opportunity_id"] for g in exclude}
        return [g for g in grants if g["opportunity_id"] not in exclude_ids][:5]

    def _render_html(self, content: NewsletterContent) -> str:
        """Render content to HTML using templates."""
        # Featured section
        featured_html = ""
        if content.featured:
            featured_html = FEATURED_SECTION.format(
                title=content.featured.title,
                content=content.featured.featured_text,
                url=content.featured.url,
            )

        # Opportunities section
        opps_html = ""
        for summary in content.new_opportunities:
            opps_html += OPPORTUNITY_ITEM.format(
                title=summary.title,
                agency=summary.agency,
                deadline=summary.deadline or "Rolling",
                award_range=summary.award_range,
                summary=summary.summary_text,
                url=summary.url,
            )

        # Deadline section
        deadline_html = ""
        if content.deadline_alerts:
            alerts_html = ""
            for alert in content.deadline_alerts:
                alerts_html += DEADLINE_ITEM.format(
                    title=alert.title,
                    alert_text=alert.alert_text,
                    days_until=alert.days_until,
                )
            deadline_html = DEADLINE_SECTION.format(alerts=alerts_html)

        # Quick hits section
        quick_hits_html = ""
        if content.quick_hits:
            hits_html = ""
            for hit in content.quick_hits:
                hits_html += QUICK_HIT_ITEM.format(text=hit)
            quick_hits_html = QUICK_HITS_SECTION.format(quick_hits=hits_html)

        # Compose full newsletter
        return NEWSLETTER_TEMPLATE.format(
            issue_date=content.issue_date,
            featured_section=featured_html,
            opportunities_section=opps_html,
            deadline_section=deadline_html,
            quick_hits_section=quick_hits_html,
            tip_of_week=content.tip_of_the_week,
        )

    def _format_award_range(self, grant: dict) -> str:
        """Format award range for display."""
        ceiling = grant.get("award_ceiling")
        floor = grant.get("award_floor")
        if ceiling:
            if floor:
                return f"${floor:,} - ${ceiling:,}"
            return f"Up to ${ceiling:,}"
        return "Amount varies"
