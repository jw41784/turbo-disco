"""
Content repurposing orchestrator.

Takes newsletter content and generates:
- 3 LinkedIn posts (grant highlight, deadline alert, tip)
- 1 Twitter thread (for featured grant)
- Blog post draft (for SEO)
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .linkedin import LinkedInGenerator, LinkedInPost, TwitterThread

logger = logging.getLogger(__name__)


@dataclass
class BlogPost:
    """SEO-optimized blog post from newsletter."""
    title: str
    slug: str
    content: str  # Markdown format
    meta_description: str
    keywords: list[str]
    grants_featured: list[str]
    generated_at: str


@dataclass
class WeeklyMarketingContent:
    """All marketing content for the week."""
    week_of: str
    linkedin_posts: list[LinkedInPost]
    twitter_thread: Optional[TwitterThread]
    blog_post: Optional[BlogPost]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "week_of": self.week_of,
            "linkedin_posts": [asdict(p) for p in self.linkedin_posts],
            "twitter_thread": asdict(self.twitter_thread) if self.twitter_thread else None,
            "blog_post": asdict(self.blog_post) if self.blog_post else None,
        }


class ContentRepurposer:
    """
    Repurposes newsletter content into marketing materials.

    Usage:
        repurposer = ContentRepurposer(api_key)
        content = repurposer.generate_weekly_content(
            featured_grant=featured,
            approved_grants=grants,
            deadline_grants=deadlines,
            tip_of_week=tip
        )
        repurposer.save_content(content, output_dir)
    """

    def __init__(self, api_key: str):
        self.linkedin = LinkedInGenerator(api_key=api_key)

    def generate_weekly_content(
        self,
        featured_grant: Optional[dict] = None,
        approved_grants: list[dict] = None,
        deadline_grants: list[dict] = None,
        tip_of_week: str = "",
        generate_blog: bool = True,
    ) -> WeeklyMarketingContent:
        """
        Generate all marketing content for the week.

        Args:
            featured_grant: The featured opportunity from newsletter
            approved_grants: All approved grants for the week
            deadline_grants: Grants with upcoming deadlines
            tip_of_week: The tip from the newsletter
            generate_blog: Whether to generate blog post

        Returns:
            WeeklyMarketingContent with all generated content
        """
        approved_grants = approved_grants or []
        deadline_grants = deadline_grants or []

        linkedin_posts = []
        twitter_thread = None
        blog_post = None

        # 1. Grant Highlight (Tuesday) - from featured grant
        if featured_grant:
            logger.info("Generating LinkedIn grant highlight...")
            highlight = self.linkedin.generate_grant_highlight(featured_grant)
            linkedin_posts.append(highlight)

            # Also generate Twitter thread for featured
            logger.info("Generating Twitter thread...")
            twitter_thread = self.linkedin.generate_twitter_thread(featured_grant)
        elif approved_grants:
            # Fall back to first approved grant
            logger.info("No featured grant, using first approved...")
            highlight = self.linkedin.generate_grant_highlight(approved_grants[0])
            linkedin_posts.append(highlight)

        # 2. Deadline Alert (Thursday) - from deadline grants
        if deadline_grants:
            logger.info("Generating LinkedIn deadline alert...")
            deadline_post = self.linkedin.generate_deadline_alert(deadline_grants)
            linkedin_posts.append(deadline_post)

        # 3. Tip/Insight (Saturday) - from tip or grant context
        logger.info("Generating LinkedIn tip/insight...")
        tip_post = self.linkedin.generate_tip_insight(
            grants=approved_grants,
            tip_context=tip_of_week,
        )
        linkedin_posts.append(tip_post)

        # 4. Blog post for SEO (optional)
        if generate_blog and approved_grants:
            logger.info("Generating blog post...")
            blog_post = self._generate_blog_post(
                featured=featured_grant,
                grants=approved_grants,
                tip=tip_of_week,
            )

        return WeeklyMarketingContent(
            week_of=datetime.now().strftime("%Y-%m-%d"),
            linkedin_posts=linkedin_posts,
            twitter_thread=twitter_thread,
            blog_post=blog_post,
        )

    def _generate_blog_post(
        self,
        featured: Optional[dict],
        grants: list[dict],
        tip: str,
    ) -> BlogPost:
        """Generate SEO-optimized blog post from newsletter content."""
        now = datetime.now()
        week_str = now.strftime("%B %d, %Y")
        slug = now.strftime("clean-energy-grants-week-of-%Y-%m-%d")

        # Build markdown content
        content = f"# Clean Energy Grants: Week of {week_str}\n\n"
        content += "This week's curated federal funding opportunities for clean energy organizations.\n\n"

        # Featured
        if featured:
            content += "## Featured Opportunity\n\n"
            content += f"### {featured.get('title', '')}\n\n"
            content += f"**Agency:** {featured.get('agency', '')}  \n"
            content += f"**Amount:** {self._format_award(featured)}  \n"
            content += f"**Deadline:** {featured.get('close_date') or 'Rolling'}  \n\n"
            if featured.get("summary"):
                content += f"{featured['summary']}\n\n"
            content += f"[View Full Details]({featured.get('url', '')})\n\n"

        # Other grants
        if grants:
            content += "## New Opportunities\n\n"
            for g in grants[:5]:
                if g.get("opportunity_id") == featured.get("opportunity_id"):
                    continue
                content += f"### {g.get('title', '')}\n\n"
                content += f"**Agency:** {g.get('agency', '')} | "
                content += f"**Deadline:** {g.get('close_date') or 'Rolling'} | "
                content += f"**Amount:** {self._format_award(g)}\n\n"
                if g.get("summary"):
                    content += f"{g['summary']}\n\n"
                content += f"[Learn More]({g.get('url', '')})\n\n"

        # Tip
        if tip:
            content += "## Tip of the Week\n\n"
            content += f"{tip}\n\n"

        # CTA
        content += "---\n\n"
        content += "*Get these opportunities delivered to your inbox every week. "
        content += "[Subscribe to the newsletter](#).*\n"

        # Keywords for SEO
        keywords = [
            "clean energy grants",
            "federal grants",
            "DOE grants",
            "EPA grants",
            now.strftime("%Y"),
        ]

        return BlogPost(
            title=f"Clean Energy Grants: Week of {week_str}",
            slug=slug,
            content=content,
            meta_description=f"This week's federal clean energy grant opportunities including DOE, EPA, and USDA programs. Updated {week_str}.",
            keywords=keywords,
            grants_featured=[g.get("opportunity_id", "") for g in grants[:5]],
            generated_at=datetime.utcnow().isoformat(),
        )

    def save_content(
        self,
        content: WeeklyMarketingContent,
        output_dir: Path,
    ) -> dict[str, Path]:
        """
        Save generated content to files.

        Returns dict of content type to file path.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        week = content.week_of
        saved = {}

        # LinkedIn posts - individual markdown files
        for i, post in enumerate(content.linkedin_posts, 1):
            filename = f"linkedin_{week}_{post.post_type}.md"
            filepath = output_dir / filename

            md_content = f"# LinkedIn Post: {post.post_type.replace('_', ' ').title()}\n\n"
            md_content += f"**Scheduled for:** {post.scheduled_for}\n\n"
            md_content += "---\n\n"
            md_content += post.content
            md_content += "\n\n---\n\n"
            md_content += f"*Generated: {post.generated_at}*\n"

            filepath.write_text(md_content)
            saved[f"linkedin_{i}"] = filepath
            logger.info(f"Saved: {filepath}")

        # Twitter thread
        if content.twitter_thread:
            filename = f"twitter_{week}_thread.md"
            filepath = output_dir / filename

            md_content = "# Twitter Thread\n\n"
            for i, tweet in enumerate(content.twitter_thread.tweets, 1):
                md_content += f"**{i}/** {tweet}\n\n"
            md_content += f"---\n\n*Generated: {content.twitter_thread.generated_at}*\n"

            filepath.write_text(md_content)
            saved["twitter"] = filepath
            logger.info(f"Saved: {filepath}")

        # Blog post
        if content.blog_post:
            filename = f"blog_{content.blog_post.slug}.md"
            filepath = output_dir / filename

            # Add frontmatter for static site generators
            frontmatter = "---\n"
            frontmatter += f"title: \"{content.blog_post.title}\"\n"
            frontmatter += f"date: {week}\n"
            frontmatter += f"description: \"{content.blog_post.meta_description}\"\n"
            frontmatter += f"keywords: {json.dumps(content.blog_post.keywords)}\n"
            frontmatter += "---\n\n"

            filepath.write_text(frontmatter + content.blog_post.content)
            saved["blog"] = filepath
            logger.info(f"Saved: {filepath}")

        # Full JSON export
        json_path = output_dir / f"marketing_{week}.json"
        json_path.write_text(json.dumps(content.to_dict(), indent=2))
        saved["json"] = json_path
        logger.info(f"Saved: {json_path}")

        return saved

    def _format_award(self, grant: dict) -> str:
        """Format award amount."""
        ceiling = grant.get("award_ceiling")
        floor = grant.get("award_floor")
        if ceiling:
            if floor:
                return f"${floor:,} - ${ceiling:,}"
            return f"Up to ${ceiling:,}"
        return "Varies"
