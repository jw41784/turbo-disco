"""
Filter logic for matching grants to our clean energy criteria.

Matches by:
1. CFDA codes (high confidence)
2. Primary keywords (high confidence)
3. Secondary keywords (flag for review)
"""

import logging
import re
from pathlib import Path
from typing import Optional

import yaml

from .models import Grant, MatchType

logger = logging.getLogger(__name__)


class GrantFilter:
    """Filters grants based on CFDA codes and keywords."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize filter with config files.

        Args:
            config_dir: Path to config directory containing cfda_codes.yaml and keywords.yaml
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"

        self.cfda_codes = self._load_cfda_codes(config_dir / "cfda_codes.yaml")
        self.keywords = self._load_keywords(config_dir / "keywords.yaml")

        logger.info(f"Loaded {len(self.cfda_codes)} CFDA codes")
        logger.info(f"Loaded {len(self.keywords['primary'])} primary keywords")
        logger.info(f"Loaded {len(self.keywords['secondary'])} secondary keywords")

    def _load_cfda_codes(self, path: Path) -> set[str]:
        """Load CFDA codes from YAML config."""
        if not path.exists():
            logger.warning(f"CFDA codes file not found: {path}")
            return set()

        with open(path) as f:
            data = yaml.safe_load(f)

        codes = set()
        for agency, programs in data.items():
            for program in programs:
                codes.add(program["code"])

        return codes

    def _load_keywords(self, path: Path) -> dict[str, list[re.Pattern]]:
        """Load keywords from YAML config and compile as regex patterns."""
        if not path.exists():
            logger.warning(f"Keywords file not found: {path}")
            return {"primary": [], "secondary": []}

        with open(path) as f:
            data = yaml.safe_load(f)

        # Compile keywords as case-insensitive regex patterns
        # Use word boundaries for more accurate matching
        keywords = {
            "primary": [],
            "secondary": []
        }

        for kw in data.get("primary", []):
            pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            keywords["primary"].append((kw, pattern))

        for kw in data.get("secondary", []):
            pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            keywords["secondary"].append((kw, pattern))

        return keywords

    def matches_cfda(self, grant: Grant) -> Optional[str]:
        """
        Check if grant matches any tracked CFDA code.

        Returns the matching CFDA code or None.
        """
        for cfda in grant.cfda_numbers:
            # Clean up CFDA number (remove whitespace)
            cfda_clean = cfda.strip()
            if cfda_clean in self.cfda_codes:
                return cfda_clean

        return None

    def matches_keyword(self, grant: Grant) -> tuple[Optional[str], Optional[str]]:
        """
        Check if grant matches any keyword.

        Searches title and description.
        Returns (keyword_type, matched_keyword) or (None, None).
        Primary keywords are checked first.
        """
        # Combine searchable text
        text = f"{grant.title} {grant.description}"

        # Check primary keywords first
        for keyword, pattern in self.keywords["primary"]:
            if pattern.search(text):
                return "primary_keyword", keyword

        # Then secondary keywords
        for keyword, pattern in self.keywords["secondary"]:
            if pattern.search(text):
                return "secondary_keyword", keyword

        return None, None

    def filter_grant(self, grant: Grant) -> tuple[bool, Optional[MatchType], Optional[str]]:
        """
        Check if a grant matches our criteria.

        Returns:
            (matches, match_type, match_value)
            - matches: True if grant should be included
            - match_type: How it matched (CFDA, primary keyword, secondary keyword)
            - match_value: The specific CFDA code or keyword that matched
        """
        # Priority 1: CFDA code match
        cfda_match = self.matches_cfda(grant)
        if cfda_match:
            return True, MatchType.CFDA, cfda_match

        # Priority 2: Keyword match
        kw_type, kw_value = self.matches_keyword(grant)
        if kw_type:
            match_type = MatchType.PRIMARY_KEYWORD if kw_type == "primary_keyword" else MatchType.SECONDARY_KEYWORD
            return True, match_type, kw_value

        return False, None, None

    def filter_grants(self, grants: list[Grant]) -> list[Grant]:
        """
        Filter a list of grants, keeping only those that match.

        Adds match_type and match_value to each matching grant.
        """
        matched = []

        for grant in grants:
            matches, match_type, match_value = self.filter_grant(grant)
            if matches:
                grant.match_type = match_type.value if match_type else None
                grant.match_value = match_value
                matched.append(grant)
                logger.debug(f"Matched: {grant.title[:50]}... ({match_type.value}: {match_value})")

        logger.info(f"Filtered {len(grants)} grants → {len(matched)} matches")

        # Log breakdown by match type
        by_type = {}
        for g in matched:
            by_type[g.match_type] = by_type.get(g.match_type, 0) + 1
        for mt, count in sorted(by_type.items()):
            logger.info(f"  {mt}: {count}")

        return matched
