"""
Deduplication logic for grant processing.

Handles:
- New grants (never seen before)
- Updated grants (significant changes: deadline, amount, eligibility)
- Unchanged grants (skip)
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .models import Grant, GrantDatabase, GrantStatus

logger = logging.getLogger(__name__)


@dataclass
class DedupeResult:
    """Result of deduplication for a single grant."""
    grant: Grant
    is_new: bool
    is_updated: bool
    change_reason: Optional[str] = None  # What changed (for updated grants)

    @property
    def should_process(self) -> bool:
        """Whether this grant should be included in the newsletter."""
        return self.is_new or self.is_updated

    @property
    def status_label(self) -> str:
        """Human-readable status."""
        if self.is_new:
            return "NEW"
        elif self.is_updated:
            return f"UPDATED ({self.change_reason})"
        else:
            return "unchanged"


class GrantDeduplicator:
    """
    Deduplicates grants against the database.

    Deduplication rules:
    - New opportunity ID → always include
    - Same ID, deadline changed → include with "UPDATED" flag
    - Same ID, amount changed → include with "UPDATED" flag
    - Same ID, eligibility changed → include with "UPDATED" flag
    - Same ID, minor text changes only → skip
    """

    def __init__(self, db: GrantDatabase):
        self.db = db

    def check_grant(self, grant: Grant) -> DedupeResult:
        """
        Check a single grant against the database.

        Returns DedupeResult indicating whether this is new, updated, or unchanged.
        """
        existing = self.db.get_grant(grant.opportunity_id)

        if existing is None:
            # Brand new grant
            return DedupeResult(grant=grant, is_new=True, is_updated=False)

        # Compare content hash for significant changes
        new_hash = grant.compute_hash()
        old_hash = existing.get("content_hash", "")

        if new_hash != old_hash:
            # Something significant changed - figure out what
            change_reason = self._detect_change_reason(grant, existing)
            return DedupeResult(
                grant=grant,
                is_new=False,
                is_updated=True,
                change_reason=change_reason
            )

        # No significant changes
        return DedupeResult(grant=grant, is_new=False, is_updated=False)

    def _detect_change_reason(self, new_grant: Grant, existing: dict) -> str:
        """Determine what changed between old and new versions."""
        reasons = []

        if new_grant.close_date != existing.get("close_date"):
            reasons.append("deadline")

        if new_grant.award_floor != existing.get("award_floor"):
            reasons.append("min amount")

        if new_grant.award_ceiling != existing.get("award_ceiling"):
            reasons.append("max amount")

        # For eligibility, we'd need to parse the JSON
        # Simplified check for now
        import json
        old_elig = json.loads(existing.get("eligibility_codes", "[]"))
        if sorted(new_grant.eligibility_codes) != sorted(old_elig):
            reasons.append("eligibility")

        if reasons:
            return ", ".join(reasons)
        return "other"

    def process_grants(self, grants: list[Grant]) -> tuple[list[DedupeResult], dict]:
        """
        Process a batch of grants through deduplication.

        Returns:
            - List of DedupeResult for all grants
            - Stats dict with counts
        """
        results = []
        stats = {
            "total": len(grants),
            "new": 0,
            "updated": 0,
            "unchanged": 0,
        }

        for grant in grants:
            result = self.check_grant(grant)
            results.append(result)

            if result.is_new:
                stats["new"] += 1
            elif result.is_updated:
                stats["updated"] += 1
            else:
                stats["unchanged"] += 1

            # Store in database
            if result.should_process:
                status = GrantStatus.NEW if result.is_new else GrantStatus.UPDATED
                self.db.upsert_grant(grant, status)

        logger.info(
            f"Deduplication: {stats['new']} new, {stats['updated']} updated, "
            f"{stats['unchanged']} unchanged (of {stats['total']} total)"
        )

        return results, stats

    def get_actionable(self, results: list[DedupeResult]) -> list[DedupeResult]:
        """Get only the grants that need action (new or updated)."""
        return [r for r in results if r.should_process]
