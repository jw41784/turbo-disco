"""
LinkedIn post generation from grant data.

Generates 3 post types:
1. Grant Highlight - Featured opportunity of the week
2. Deadline Alert - Grants closing soon
3. Tip/Insight - Actionable advice for grant seekers
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..summarize.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


# LinkedIn post prompts - designed for engagement without being spammy
SYSTEM_PROMPT = """You are a clean energy grants expert writing LinkedIn posts. Your audience is grant professionals, sustainability officers, and clean energy organizations.

Writing style:
- Professional but approachable
- No emojis except sparingly (1-2 max)
- No hashtags in the main text (add 3-5 at the very end)
- Short paragraphs, use line breaks for readability
- Lead with the hook, not "I'm excited to share..."
- Include specific numbers (funding amounts, deadlines)
- End with a soft call-to-action (not pushy)
- Never say "check out my newsletter" - instead offer value first
"""

GRANT_HIGHLIGHT_PROMPT = """Write a LinkedIn post highlighting this grant opportunity.

Format:
- Hook line (the most compelling fact)
- What it funds (2-3 sentences)
- Who should apply
- Key deadline
- Soft CTA: "I cover opportunities like this weekly" or similar
- 3-5 relevant hashtags at the end

Grant data:
Title: {title}
Agency: {agency}
Amount: {award_range}
Deadline: {deadline}
Description: {description}
URL: {url}

Keep it under 200 words. Make it valuable even if they never click.
"""

DEADLINE_ALERT_PROMPT = """Write a LinkedIn post alerting people to grants closing soon.

Format:
- Urgent but not alarmist hook
- List 2-4 grants with: name, amount, deadline
- One sentence on why these matter
- Soft CTA about staying informed
- 3-5 relevant hashtags at the end

Grants closing soon:
{grants_list}

Keep it under 150 words. Focus on being helpful, not promotional.
"""

TIP_INSIGHT_PROMPT = """Write a LinkedIn post sharing an actionable grant-writing tip or insight.

The tip should relate to clean energy grants (DOE, EPA, USDA programs). Make it specific and actionable, not generic advice.

Context from this week's grants:
{context}

Format:
- Lead with the insight (not "Here's a tip...")
- Explain why this matters (1-2 sentences)
- Give a specific action they can take
- Optional: brief example
- 3-5 relevant hashtags at the end

Keep it under 150 words. Demonstrate expertise without being preachy.
"""

TWITTER_THREAD_PROMPT = """Convert this grant opportunity into a Twitter/X thread (5-7 tweets).

Tweet 1: Hook - the most compelling fact (under 280 chars)
Tweet 2: What it funds
Tweet 3: Who's eligible
Tweet 4: Funding amount and deadline
Tweet 5: One tip for applying
Tweet 6: Link and soft CTA
Tweet 7 (optional): Relevant hashtags

Grant data:
Title: {title}
Agency: {agency}
Amount: {award_range}
Deadline: {deadline}
Description: {description}
URL: {url}

Format each tweet on its own line, numbered 1/, 2/, etc.
"""


@dataclass
class LinkedInPost:
    """Generated LinkedIn post."""
    post_type: str  # "grant_highlight", "deadline_alert", "tip_insight"
    content: str
    source_grants: list[str]  # opportunity_ids used
    generated_at: str
    scheduled_for: Optional[str] = None  # Suggested day: "Tuesday", "Thursday", "Saturday"


@dataclass
class TwitterThread:
    """Generated Twitter thread."""
    tweets: list[str]
    source_grant: str
    generated_at: str


class LinkedInGenerator:
    """Generates LinkedIn posts from grant data."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = ClaudeClient(api_key=api_key, model=model)

    def generate_grant_highlight(self, grant: dict) -> LinkedInPost:
        """Generate a post highlighting a single notable grant."""
        prompt = GRANT_HIGHLIGHT_PROMPT.format(
            title=grant.get("title", ""),
            agency=grant.get("agency", ""),
            award_range=self._format_award_range(grant),
            deadline=grant.get("close_date") or "Rolling/Open",
            description=self._truncate(grant.get("description", ""), 1500),
            url=grant.get("url", ""),
        )

        content = self.client.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=400,
            temperature=0.7,
        )

        return LinkedInPost(
            post_type="grant_highlight",
            content=content.strip(),
            source_grants=[grant.get("opportunity_id", "")],
            generated_at=datetime.utcnow().isoformat(),
            scheduled_for="Tuesday",
        )

    def generate_deadline_alert(self, grants: list[dict]) -> LinkedInPost:
        """Generate a post alerting to upcoming deadlines."""
        grants_list = ""
        source_ids = []

        for g in grants[:4]:  # Max 4 grants
            grants_list += f"- {g.get('title', '')}\n"
            grants_list += f"  Agency: {g.get('agency', '')} | "
            grants_list += f"Amount: {self._format_award_range(g)} | "
            grants_list += f"Deadline: {g.get('close_date', 'TBD')}\n\n"
            source_ids.append(g.get("opportunity_id", ""))

        prompt = DEADLINE_ALERT_PROMPT.format(grants_list=grants_list)

        content = self.client.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=300,
            temperature=0.7,
        )

        return LinkedInPost(
            post_type="deadline_alert",
            content=content.strip(),
            source_grants=source_ids,
            generated_at=datetime.utcnow().isoformat(),
            scheduled_for="Thursday",
        )

    def generate_tip_insight(self, grants: list[dict], tip_context: str = "") -> LinkedInPost:
        """Generate a tip/insight post based on current grants."""
        # Build context from grant titles and agencies
        context = tip_context or ""
        if grants:
            context += "\n\nThis week's notable grants:\n"
            for g in grants[:5]:
                context += f"- {g.get('title', '')} ({g.get('agency', '')})\n"

        prompt = TIP_INSIGHT_PROMPT.format(context=context)

        content = self.client.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=300,
            temperature=0.8,
        )

        return LinkedInPost(
            post_type="tip_insight",
            content=content.strip(),
            source_grants=[g.get("opportunity_id", "") for g in grants[:3]],
            generated_at=datetime.utcnow().isoformat(),
            scheduled_for="Saturday",
        )

    def generate_twitter_thread(self, grant: dict) -> TwitterThread:
        """Generate a Twitter thread for a featured grant."""
        prompt = TWITTER_THREAD_PROMPT.format(
            title=grant.get("title", ""),
            agency=grant.get("agency", ""),
            award_range=self._format_award_range(grant),
            deadline=grant.get("close_date") or "Rolling/Open",
            description=self._truncate(grant.get("description", ""), 1000),
            url=grant.get("url", ""),
        )

        content = self.client.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            max_tokens=500,
            temperature=0.7,
        )

        # Parse tweets from numbered format
        tweets = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("Tweet")):
                # Remove numbering prefix
                if "/" in line[:3]:
                    line = line.split("/", 1)[1].strip()
                elif ":" in line[:10]:
                    line = line.split(":", 1)[1].strip()
                if line:
                    tweets.append(line)

        return TwitterThread(
            tweets=tweets,
            source_grant=grant.get("opportunity_id", ""),
            generated_at=datetime.utcnow().isoformat(),
        )

    def _format_award_range(self, grant: dict) -> str:
        """Format award range for display."""
        floor = grant.get("award_floor")
        ceiling = grant.get("award_ceiling")
        if ceiling:
            if floor:
                return f"${floor:,} - ${ceiling:,}"
            return f"Up to ${ceiling:,}"
        return "Amount varies"

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."
