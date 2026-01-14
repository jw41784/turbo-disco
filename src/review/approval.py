"""
Automatic approval logic based on match confidence.

Approval Rules:
- CFDA match: AUTO-APPROVE (highest confidence)
- Primary keyword match: AUTO-APPROVE (high confidence)
- Secondary keyword match: FLAG FOR REVIEW (optional human check)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ApprovalConfidence(Enum):
    """Confidence level for auto-approval."""

    HIGH = "high"  # CFDA or primary keyword - auto-approve
    MEDIUM = "medium"  # Secondary keyword - flag for optional review
    LOW = "low"  # Would need manual intervention


class ApprovalDecision(Enum):
    """Approval decision."""

    AUTO_APPROVED = "auto_approved"
    FLAGGED = "flagged"  # For optional review
    MANUALLY_APPROVED = "manually_approved"
    SKIPPED = "skipped"


@dataclass
class ApprovalResult:
    """Result of approval decision for a grant."""

    opportunity_id: str
    decision: ApprovalDecision
    confidence: ApprovalConfidence
    reason: str
    decided_at: str


class AutoApprover:
    """
    Automatic approval engine based on match type.

    Philosophy: High-confidence matches (CFDA, primary keywords) are
    almost always relevant. Auto-approve them. Secondary keywords
    occasionally match irrelevant grants, so flag for optional review.
    """

    # Match types that get auto-approved
    AUTO_APPROVE_MATCH_TYPES = {"cfda", "primary_keyword"}

    # Match types that get flagged for optional review
    REVIEW_MATCH_TYPES = {"secondary_keyword"}

    def evaluate(self, grant: dict) -> ApprovalResult:
        """
        Evaluate a grant for auto-approval.

        Args:
            grant: Grant dict with match_type field

        Returns:
            ApprovalResult with decision and reasoning
        """
        match_type = grant.get("match_type", "").lower()
        match_value = grant.get("match_value", "")
        now = datetime.utcnow().isoformat()

        if match_type in self.AUTO_APPROVE_MATCH_TYPES:
            return ApprovalResult(
                opportunity_id=grant["opportunity_id"],
                decision=ApprovalDecision.AUTO_APPROVED,
                confidence=ApprovalConfidence.HIGH,
                reason=f"Auto-approved: {match_type} match ({match_value})",
                decided_at=now,
            )

        elif match_type in self.REVIEW_MATCH_TYPES:
            return ApprovalResult(
                opportunity_id=grant["opportunity_id"],
                decision=ApprovalDecision.FLAGGED,
                confidence=ApprovalConfidence.MEDIUM,
                reason=f"Flagged for review: {match_type} match ({match_value})",
                decided_at=now,
            )

        else:
            # Unknown match type - should not happen
            logger.warning(
                f"Unknown match type: {match_type} for {grant['opportunity_id']}"
            )
            return ApprovalResult(
                opportunity_id=grant["opportunity_id"],
                decision=ApprovalDecision.FLAGGED,
                confidence=ApprovalConfidence.LOW,
                reason=f"Unknown match type: {match_type}",
                decided_at=now,
            )

    def process_batch(self, grants: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Process grants through auto-approval.

        Returns:
            (auto_approved_grants, flagged_grants)
        """
        auto_approved = []
        flagged = []

        for grant in grants:
            result = self.evaluate(grant)
            grant["approval_result"] = result

            if result.decision == ApprovalDecision.AUTO_APPROVED:
                auto_approved.append(grant)
            else:
                flagged.append(grant)

        logger.info(
            f"Auto-approval: {len(auto_approved)} approved, "
            f"{len(flagged)} flagged for review"
        )

        return auto_approved, flagged
