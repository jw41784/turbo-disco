#!/usr/bin/env python3
"""
Complete automated pipeline: fetch -> filter -> dedupe -> summarize -> approve -> publish

Usage:
    python scripts/run_pipeline.py                    # Full auto run, schedule Monday
    python scripts/run_pipeline.py --review           # Pause for optional review
    python scripts/run_pipeline.py --dry-run          # Don't publish
    python scripts/run_pipeline.py --schedule monday  # Schedule for specific day
    python scripts/run_pipeline.py --publish-now      # Publish immediately
"""

import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    DATABASE_PATH,
    LOGS_DIR,
    CONFIG_DIR,
    ANTHROPIC_API_KEY,
    BEEHIIV_API_KEY,
    BEEHIIV_PUBLICATION_ID,
    FETCH_DAYS_BACK,
)
from src.grants.fetch import GrantsGovClient
from src.grants.filter import GrantFilter
from src.grants.dedupe import GrantDeduplicator
from src.grants.models import GrantDatabase, GrantStatus
from src.summarize.summarizer import GrantSummarizer
from src.review.reviewer import GrantReviewer
from src.publish.beehiiv import BeehiivClient
from src.publish.composer import NewsletterComposer
from src.publish.scheduler import get_next_monday_9am, calculate_send_time, get_issue_date


def setup_logging(level: str = "INFO", log_file: Path = None) -> logging.Logger:
    """Configure logging for the pipeline."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


def main():
    parser = argparse.ArgumentParser(description="Run complete newsletter pipeline")
    parser.add_argument("--days", type=int, default=FETCH_DAYS_BACK, help="Days back to fetch")
    parser.add_argument("--review", action="store_true", help="Enable optional review step")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually publish")
    parser.add_argument("--schedule", type=str, help="Schedule for day (e.g., 'monday')")
    parser.add_argument("--publish-now", action="store_true", help="Publish immediately")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    log_file = LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger = setup_logging(level=log_level, log_file=log_file)

    logger.info("=" * 70)
    logger.info("TURBO DISCO PIPELINE - Automated Newsletter Generation")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    try:
        # Validate API keys
        if not args.dry_run:
            if not ANTHROPIC_API_KEY:
                logger.error("ANTHROPIC_API_KEY not set in environment")
                return 1
            if not BEEHIIV_API_KEY or not BEEHIIV_PUBLICATION_ID:
                logger.error("BEEHIIV_API_KEY or BEEHIIV_PUBLICATION_ID not set")
                return 1

        # Initialize components
        db = GrantDatabase(DATABASE_PATH)
        client = GrantsGovClient()
        filter_ = GrantFilter(config_dir=CONFIG_DIR)
        deduper = GrantDeduplicator(db)

        # PHASE 1: Fetch & Filter & Dedupe
        logger.info("\n[PHASE 1] Fetching and filtering grants...")
        all_grants = client.fetch_recent(days_back=args.days)
        logger.info(f"  Fetched: {len(all_grants)} grants from Grants.gov")

        matched = filter_.filter_grants(all_grants)
        logger.info(f"  Matched: {len(matched)} grants (clean energy relevant)")

        if not matched:
            logger.info("No matching grants found. Exiting.")
            return 0

        results, stats = deduper.process_grants(matched)
        actionable = deduper.get_actionable(results)
        logger.info(f"  New/Updated: {len(actionable)} grants for processing")

        if not actionable:
            logger.info("No new grants to process. Exiting.")
            return 0

        # Log fetch
        db.log_fetch(len(all_grants), len(matched), stats["new"], stats["updated"])

        # PHASE 2: Summarization
        logger.info("\n[PHASE 2] Generating AI summaries...")

        if not ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set - skipping summarization in dry-run")
            grants_to_process = [r.grant.to_dict() for r in actionable]
            for grant in grants_to_process:
                grant["summary"] = f"[Dry run - summary would be generated for: {grant['title'][:50]}...]"
                db.update_status(
                    grant["opportunity_id"],
                    GrantStatus.PROCESSED,
                    summary=grant["summary"],
                )
        else:
            summarizer = GrantSummarizer(api_key=ANTHROPIC_API_KEY)
            grants_to_process = [r.grant.to_dict() for r in actionable]

            for grant in grants_to_process:
                summary = summarizer.summarize_grant(grant)
                grant["summary"] = summary.summary_text
                db.update_status(
                    grant["opportunity_id"],
                    GrantStatus.PROCESSED,
                    summary=summary.summary_text,
                )
            logger.info(f"  Summarized: {len(grants_to_process)} grants")

        # PHASE 3: Approval
        logger.info("\n[PHASE 3] Running auto-approval...")
        reviewer = GrantReviewer(db)
        approved, flagged = reviewer.process_grants(
            auto_approve_all=not args.review, interactive=args.review
        )
        logger.info(f"  Approved: {len(approved)} grants")
        logger.info(f"  Flagged: {len(flagged)} grants")

        if not approved:
            logger.warning("No grants approved for newsletter")
            return 0

        # PHASE 4: Compose & Publish
        logger.info("\n[PHASE 4] Composing newsletter...")
        approved_grants = reviewer.get_approved_for_newsletter()

        if not approved_grants:
            logger.warning("No approved grants found for newsletter")
            return 0

        if not ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY not set - using placeholder content")
            subject = f"[Clean Energy Grants] {len(approved_grants)} new opportunities"
            html = f"<html><body><h1>Dry Run Newsletter</h1><p>{len(approved_grants)} grants would be included.</p></body></html>"
        else:
            summarizer = GrantSummarizer(api_key=ANTHROPIC_API_KEY)
            composer = NewsletterComposer(summarizer)
            subject, html, content = composer.compose(approved_grants)

        logger.info(f"  Subject: {subject}")

        if args.dry_run:
            logger.info("\n[DRY RUN] Would publish:")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Content length: {len(html)} chars")
            logger.info(f"  Grants included: {len(approved_grants)}")

            # Save draft locally
            draft_path = LOGS_DIR / f"draft_{datetime.now().strftime('%Y%m%d')}.html"
            with open(draft_path, "w") as f:
                f.write(html)
            logger.info(f"  Draft saved: {draft_path}")

        else:
            # Publish to Beehiiv
            beehiiv = BeehiivClient(
                api_key=BEEHIIV_API_KEY, publication_id=BEEHIIV_PUBLICATION_ID
            )

            post = beehiiv.create_post(
                title=subject,
                content=html,
                subtitle=f"This week: {len(approved_grants)} new clean energy grant opportunities",
                status="draft",
            )

            post_id = post.get("id")
            logger.info(f"  Created draft post: {post_id}")

            if args.publish_now:
                beehiiv.publish_post(post_id)
                logger.info("  Published immediately!")

            elif args.schedule:
                send_time = calculate_send_time(day=args.schedule)
                beehiiv.schedule_post(post_id, send_time)
                logger.info(f"  Scheduled for: {send_time}")

            else:
                # Default: schedule for next Monday 9am
                send_time = get_next_monday_9am()
                beehiiv.schedule_post(post_id, send_time)
                logger.info(f"  Scheduled for: {send_time}")

            # Update database
            issue_date = get_issue_date()
            for grant in approved_grants:
                db.update_status(
                    grant["opportunity_id"],
                    GrantStatus.PUBLISHED,
                    published_in_issue=issue_date,
                )

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETE")
        logger.info(f"  Grants fetched: {len(all_grants)}")
        logger.info(f"  Grants matched: {len(matched)}")
        logger.info(f"  Grants processed: {len(actionable)}")
        logger.info(f"  Grants approved: {len(approved)}")
        logger.info(f"  Newsletter: {'DRAFT' if args.dry_run else 'SCHEDULED'}")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
