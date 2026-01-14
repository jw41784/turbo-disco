"""
Main review orchestrator.
Handles both auto-approval and optional manual review.
"""

import logging
from datetime import datetime
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.grants.models import GrantDatabase, GrantStatus
from .approval import AutoApprover, ApprovalDecision

logger = logging.getLogger(__name__)


class GrantReviewer:
    """
    Orchestrates the approval workflow.

    Default mode: Fully automatic
    - Auto-approve CFDA and primary keyword matches
    - Auto-approve secondary keyword matches too (--auto-all flag)

    Optional mode: Review flagged items
    - Auto-approve high-confidence
    - Launch CLI for secondary keyword matches
    """

    def __init__(self, db: GrantDatabase):
        self.db = db
        self.approver = AutoApprover()

    def process_grants(
        self, auto_approve_all: bool = True, interactive: bool = False
    ) -> tuple[list[dict], list[dict]]:
        """
        Process all grants pending review.

        Args:
            auto_approve_all: If True, approve secondary keyword matches too
            interactive: If True and auto_approve_all is False, launch CLI

        Returns:
            (approved_grants, skipped_grants)
        """
        # Get grants ready for review (NEW or UPDATED status)
        pending = self.db.get_grants_for_review()

        if not pending:
            logger.info("No grants pending review")
            return [], []

        logger.info(f"Processing {len(pending)} grants for approval")

        # Run auto-approval
        auto_approved, flagged = self.approver.process_batch(pending)

        # Update database for auto-approved grants
        for grant in auto_approved:
            self.db.update_status(
                grant["opportunity_id"],
                GrantStatus.APPROVED,
                approval_confidence="auto",
                auto_approved_at=datetime.utcnow().isoformat(),
            )

        # Handle flagged grants
        if flagged:
            if auto_approve_all:
                # Trust secondary keywords, approve them too
                logger.info(
                    f"Auto-approving {len(flagged)} secondary keyword matches"
                )
                for grant in flagged:
                    self.db.update_status(
                        grant["opportunity_id"],
                        GrantStatus.APPROVED,
                        approval_confidence="auto_secondary",
                        auto_approved_at=datetime.utcnow().isoformat(),
                    )
                auto_approved.extend(flagged)
                flagged = []

            elif interactive:
                # Launch CLI for review (import here to avoid circular deps)
                from .cli import ReviewCLI

                cli = ReviewCLI(self.db)
                manually_approved = cli.run(flagged)

                # Update database
                approved_ids = {g["opportunity_id"] for g in manually_approved}
                for grant in flagged:
                    if grant["opportunity_id"] in approved_ids:
                        self.db.update_status(
                            grant["opportunity_id"],
                            GrantStatus.APPROVED,
                            approval_confidence="manual",
                            reviewed_by="cli",
                        )
                        auto_approved.append(grant)
                    else:
                        self.db.update_status(
                            grant["opportunity_id"], GrantStatus.SKIPPED
                        )
            else:
                # Leave flagged grants as-is for later review
                logger.info(f"{len(flagged)} grants flagged for optional review")

        logger.info(f"Approval complete: {len(auto_approved)} approved")
        return auto_approved, flagged

    def get_approved_for_newsletter(self) -> list[dict]:
        """Get all approved grants ready for newsletter."""
        with self.db._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM grants
                WHERE status = 'approved'
                AND (published_in_issue IS NULL OR published_in_issue = '')
                ORDER BY
                    CASE match_type
                        WHEN 'cfda' THEN 1
                        WHEN 'primary_keyword' THEN 2
                        ELSE 3
                    END,
                    CASE WHEN close_date IS NOT NULL THEN close_date ELSE '9999-12-31' END
            """
            ).fetchall()
            return [dict(row) for row in rows]
