"""Data classes for generated newsletter content."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class GrantSummary:
    """Generated summary for a single grant."""

    opportunity_id: str
    title: str
    agency: str
    summary_text: str  # 75-100 words
    deadline: Optional[str]
    award_range: str  # "$X - $Y"
    url: str
    match_type: str  # cfda, primary_keyword, secondary_keyword
    match_value: str
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class FeaturedOpportunity:
    """Extended summary for featured grant."""

    opportunity_id: str
    title: str
    featured_text: str  # 150-200 words
    url: str


@dataclass
class DeadlineAlert:
    """Short alert for closing deadlines."""

    opportunity_id: str
    title: str
    alert_text: str  # 2 sentences
    deadline: str
    days_until: int


@dataclass
class NewsletterContent:
    """Complete newsletter content ready for publishing."""

    issue_date: str
    featured: Optional[FeaturedOpportunity]
    new_opportunities: list[GrantSummary]  # 3-5 grants
    deadline_alerts: list[DeadlineAlert]  # 2-3 grants
    quick_hits: list[str]  # 3-5 one-liners
    tip_of_the_week: str

    @property
    def subject_line(self) -> str:
        """Generate email subject line."""
        if self.featured:
            return f"[Clean Energy Grants] {self.featured.title} + {len(self.new_opportunities)} more"
        return f"[Clean Energy Grants] {len(self.new_opportunities)} new opportunities this week"

    @property
    def total_grants(self) -> int:
        """Total number of grants in this issue."""
        count = len(self.new_opportunities) + len(self.quick_hits)
        if self.featured:
            count += 1
        return count
