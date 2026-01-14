#!/usr/bin/env python3
"""
Generate marketing content from approved grants.

Repurposes newsletter data into:
- 3 LinkedIn posts (ready to copy/paste)
- 1 Twitter thread
- 1 SEO blog post

Usage:
    python scripts/generate_marketing.py                    # Use approved grants from DB
    python scripts/generate_marketing.py --model haiku      # Use cheaper model
    python scripts/generate_marketing.py --output ./posts   # Custom output directory
"""

import argparse
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    DATABASE_PATH,
    LOGS_DIR,
    ANTHROPIC_API_KEY,
)
from src.grants.models import GrantDatabase
from src.marketing.repurpose import ContentRepurposer


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure logging."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

    return logger


def get_model_id(model_name: str) -> str:
    """Get full model ID from short name."""
    models = {
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-3-5-haiku-20241022",
        "opus": "claude-opus-4-20250514",
    }
    return models.get(model_name.lower(), models["sonnet"])


def main():
    parser = argparse.ArgumentParser(description="Generate marketing content from grants")
    parser.add_argument(
        "--model",
        type=str,
        default="haiku",
        choices=["sonnet", "haiku", "opus"],
        help="Model to use (default: haiku for cost savings)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=LOGS_DIR / "marketing",
        help="Output directory for generated content",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Look back N days for approved grants",
    )
    parser.add_argument(
        "--no-blog",
        action="store_true",
        help="Skip blog post generation",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    # Setup
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_logging(level=log_level)

    logger.info("=" * 60)
    logger.info("MARKETING CONTENT GENERATOR")
    logger.info(f"Model: {args.model} ({get_model_id(args.model)})")
    logger.info(f"Output: {args.output}")
    logger.info("=" * 60)

    # Validate API key
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set in environment")
        return 1

    try:
        # Get approved grants from database
        db = GrantDatabase(DATABASE_PATH)

        # Get recently approved grants
        with db._get_conn() as conn:
            cutoff = (datetime.now() - timedelta(days=args.days)).isoformat()
            rows = conn.execute(
                """
                SELECT * FROM grants
                WHERE status = 'approved'
                AND last_updated_at >= ?
                ORDER BY
                    CASE match_type
                        WHEN 'cfda' THEN 1
                        WHEN 'primary_keyword' THEN 2
                        ELSE 3
                    END,
                    award_ceiling DESC
                """,
                (cutoff,),
            ).fetchall()
            approved_grants = [dict(row) for row in rows]

        if not approved_grants:
            logger.warning(f"No approved grants found in last {args.days} days")
            logger.info("Tip: Run the main pipeline first to approve grants")
            return 0

        logger.info(f"Found {len(approved_grants)} approved grants")

        # Get grants with upcoming deadlines (next 14 days)
        with db._get_conn() as conn:
            deadline_cutoff = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            rows = conn.execute(
                """
                SELECT * FROM grants
                WHERE status = 'approved'
                AND close_date IS NOT NULL
                AND close_date <= ?
                AND close_date >= date('now')
                ORDER BY close_date
                """,
                (deadline_cutoff,),
            ).fetchall()
            deadline_grants = [dict(row) for row in rows]

        logger.info(f"Found {len(deadline_grants)} grants with upcoming deadlines")

        # Select featured grant (highest funding or first CFDA match)
        featured_grant = None
        for g in approved_grants:
            ceiling = g.get("award_ceiling") or 0
            if ceiling >= 1_000_000:
                featured_grant = g
                break
        if not featured_grant and approved_grants:
            featured_grant = approved_grants[0]

        if featured_grant:
            logger.info(f"Featured: {featured_grant.get('title', '')[:50]}...")

        # Get tip from most recent grant (or use empty for generation)
        tip_of_week = ""
        for g in approved_grants:
            if g.get("summary"):
                tip_of_week = f"Based on recent opportunities from {g.get('agency', 'federal agencies')}."
                break

        # Generate marketing content
        logger.info("\nGenerating marketing content...")

        # Use the specified model
        from src.marketing.linkedin import LinkedInGenerator
        from src.marketing.repurpose import ContentRepurposer

        # Create repurposer with specified model
        model_id = get_model_id(args.model)

        # Patch the model into the generator
        repurposer = ContentRepurposer(api_key=ANTHROPIC_API_KEY)
        repurposer.linkedin.client.model = model_id

        content = repurposer.generate_weekly_content(
            featured_grant=featured_grant,
            approved_grants=approved_grants,
            deadline_grants=deadline_grants,
            tip_of_week=tip_of_week,
            generate_blog=not args.no_blog,
        )

        # Save content
        logger.info("\nSaving content...")
        saved_files = repurposer.save_content(content, args.output)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("CONTENT GENERATED")
        logger.info("=" * 60)

        logger.info("\nLinkedIn Posts:")
        for post in content.linkedin_posts:
            logger.info(f"  - {post.post_type} (post on {post.scheduled_for})")

        if content.twitter_thread:
            logger.info(f"\nTwitter Thread: {len(content.twitter_thread.tweets)} tweets")

        if content.blog_post:
            logger.info(f"\nBlog Post: {content.blog_post.slug}")

        logger.info(f"\nFiles saved to: {args.output}")
        for name, path in saved_files.items():
            logger.info(f"  - {path.name}")

        logger.info("\n" + "=" * 60)
        logger.info("Next steps:")
        logger.info("1. Review the markdown files in the output directory")
        logger.info("2. Copy/paste LinkedIn posts on Tuesday, Thursday, Saturday")
        logger.info("3. Post Twitter thread when convenient")
        logger.info("4. Upload blog post to your website for SEO")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Failed to generate marketing content: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
