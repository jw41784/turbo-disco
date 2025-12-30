#!/usr/bin/env python3
"""
Weekly grant fetch script.

Fetches grants from Grants.gov, filters for clean energy relevance,
deduplicates against the database, and outputs new/updated grants.

Usage:
    python scripts/weekly_fetch.py [--days 7] [--dry-run]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.grants.fetch import GrantsGovClient
from src.grants.filter import GrantFilter
from src.grants.dedupe import GrantDeduplicator
from src.grants.models import GrantDatabase
from src.utils.logging import setup_logging
from config.settings import (
    DATABASE_PATH,
    LOGS_DIR,
    CONFIG_DIR,
    FETCH_DAYS_BACK,
)


def main():
    parser = argparse.ArgumentParser(description="Fetch clean energy grants")
    parser.add_argument(
        "--days",
        type=int,
        default=FETCH_DAYS_BACK,
        help=f"Days back to fetch (default: {FETCH_DAYS_BACK})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save to database, just show what would be fetched"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    log_file = LOGS_DIR / f"fetch_{datetime.now().strftime('%Y%m%d')}.log"
    logger = setup_logging(level=log_level, log_file=log_file)

    logger.info("=" * 60)
    logger.info(f"Starting grant fetch - {datetime.now().isoformat()}")
    logger.info(f"Looking back {args.days} days")
    logger.info("=" * 60)

    try:
        # Initialize components
        client = GrantsGovClient()  # No API key needed for public endpoint
        filter_ = GrantFilter(config_dir=CONFIG_DIR)
        db = GrantDatabase(DATABASE_PATH)
        deduper = GrantDeduplicator(db)

        # Step 1: Fetch recent grants
        logger.info("Step 1: Fetching from Grants.gov API...")
        all_grants = client.fetch_recent(days_back=args.days)
        logger.info(f"Fetched {len(all_grants)} total grants")

        if not all_grants:
            logger.warning("No grants fetched - check API connection")
            return 1

        # Step 2: Filter for clean energy
        logger.info("Step 2: Filtering for clean energy relevance...")
        matched_grants = filter_.filter_grants(all_grants)
        logger.info(f"Matched {len(matched_grants)} grants")

        if not matched_grants:
            logger.info("No matching grants found this period")
            return 0

        # Step 3: Deduplicate
        logger.info("Step 3: Deduplicating against database...")
        if args.dry_run:
            logger.info("DRY RUN - not saving to database")
            # Still check dedupe but don't save
            for grant in matched_grants:
                existing = db.get_grant(grant.opportunity_id)
                status = "NEW" if existing is None else "existing"
                logger.info(f"  [{status}] {grant.title[:60]}...")
        else:
            results, stats = deduper.process_grants(matched_grants)
            actionable = deduper.get_actionable(results)

            # Log results
            logger.info(f"Deduplication complete:")
            logger.info(f"  New grants: {stats['new']}")
            logger.info(f"  Updated grants: {stats['updated']}")
            logger.info(f"  Unchanged (skipped): {stats['unchanged']}")

            # Log fetch to database
            db.log_fetch(
                grants_fetched=len(all_grants),
                grants_matched=len(matched_grants),
                grants_new=stats['new'],
                grants_updated=stats['updated']
            )

            # Print actionable grants
            if actionable:
                logger.info("")
                logger.info("=" * 60)
                logger.info("GRANTS TO REVIEW:")
                logger.info("=" * 60)
                for result in actionable:
                    g = result.grant
                    logger.info("")
                    logger.info(f"[{result.status_label}] {g.title}")
                    logger.info(f"  Agency: {g.agency}")
                    logger.info(f"  Deadline: {g.close_date or 'Rolling/Open'}")
                    if g.award_ceiling:
                        logger.info(f"  Max Award: ${g.award_ceiling:,}")
                    logger.info(f"  Match: {g.match_type} = {g.match_value}")
                    logger.info(f"  URL: {g.url}")

        # Print summary
        logger.info("")
        logger.info("=" * 60)
        db_stats = db.get_stats()
        logger.info(f"Database stats: {db_stats['total']} total grants")
        logger.info(f"  Upcoming deadlines: {db_stats['upcoming_deadlines']}")
        for status, count in db_stats['by_status'].items():
            logger.info(f"  {status}: {count}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Fetch failed: {e}", exc_info=True)
        if not args.dry_run:
            db.log_fetch(
                grants_fetched=0,
                grants_matched=0,
                grants_new=0,
                grants_updated=0,
                error=str(e)
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
