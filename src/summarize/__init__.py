# Summarize module - Claude API integration (Phase 2)

from .claude_client import ClaudeClient
from .summarizer import GrantSummarizer
from .content_types import (
    GrantSummary,
    FeaturedOpportunity,
    DeadlineAlert,
    NewsletterContent,
)

__all__ = [
    "ClaudeClient",
    "GrantSummarizer",
    "GrantSummary",
    "FeaturedOpportunity",
    "DeadlineAlert",
    "NewsletterContent",
]
