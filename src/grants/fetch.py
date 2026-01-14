"""
Grants.gov API client for fetching grant opportunities.

Public Search API: https://api.grants.gov/v1/api/search2
No authentication required.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

from .models import Grant

logger = logging.getLogger(__name__)


class GrantsGovClient:
    """Client for Grants.gov public REST API."""

    BASE_URL = "https://api.grants.gov/v1/api/search2"

    def __init__(self):
        """Initialize client. No API key required for public search endpoint."""
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    def search(
        self,
        posted_from: Optional[datetime] = None,
        posted_to: Optional[datetime] = None,
        cfda_numbers: Optional[list[str]] = None,
        keyword: Optional[str] = None,
        rows: int = 25,
        page: int = 1,
    ) -> tuple[list[Grant], int]:
        """
        Search for grant opportunities.

        Args:
            posted_from: Start date for posted date filter
            posted_to: End date for posted date filter
            cfda_numbers: List of CFDA numbers to filter by
            keyword: Keyword search term
            rows: Number of results per request (max 25 for this API)
            page: Page number (1-indexed)

        Returns:
            Tuple of (list of Grant objects, total count)
        """
        # Build request body for POST
        body = {
            "paging": {
                "pageNumber": page,
                "pageSize": min(rows, 25),
                "sortOrder": "DESC",
                "orderBy": "postedDate"
            },
            "status": "posted"  # Only active opportunities
        }

        # Date filters
        if posted_from:
            body["postedFrom"] = posted_from.strftime("%Y-%m-%d")
        if posted_to:
            body["postedTo"] = posted_to.strftime("%Y-%m-%d")

        # CFDA filter
        if cfda_numbers:
            body["assistanceListingNumber"] = cfda_numbers

        # Keyword search
        if keyword:
            body["keyword"] = keyword

        try:
            response = self.session.post(self.BASE_URL, json=body, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

        # Parse response - data is nested under 'data' key
        inner_data = data.get("data", {})
        opportunities = inner_data.get("oppHits", [])
        total_count = inner_data.get("hitCount", 0)
        grants = []

        for opp in opportunities:
            try:
                grant = Grant.from_api_response(opp)
                grants.append(grant)
            except Exception as e:
                logger.warning(f"Failed to parse opportunity {opp.get('opportunityId', opp.get('id'))}: {e}")

        logger.info(f"Fetched {len(grants)} grants (page {page}, total: {total_count})")
        return grants, total_count

    def fetch_recent(self, days_back: int = 7) -> list[Grant]:
        """
        Fetch all grants posted in the last N days.

        Handles pagination to get all results.
        """
        posted_from = datetime.now() - timedelta(days=days_back)
        posted_to = datetime.now()

        all_grants = []
        page = 1
        rows_per_page = 25

        while True:
            grants, total_count = self.search(
                posted_from=posted_from,
                posted_to=posted_to,
                rows=rows_per_page,
                page=page,
            )

            if not grants:
                break

            all_grants.extend(grants)

            # Check if we've fetched all
            if len(all_grants) >= total_count:
                break

            page += 1

            # Rate limiting - be nice to the API
            time.sleep(0.3)

            # Safety limit - can increase for production
            if page > 100:  # 100 pages * 25 = 2,500 records
                logger.warning("Hit pagination safety limit at 2,500 records")
                break

        logger.info(f"Total grants fetched for last {days_back} days: {len(all_grants)}")
        return all_grants

    def fetch_by_cfda(self, cfda_codes: list[str], days_back: int = 30) -> list[Grant]:
        """
        Fetch grants for specific CFDA codes.

        Note: The API may limit how many CFDA codes can be searched at once,
        so we batch them.
        """
        all_grants = []
        posted_from = datetime.now() - timedelta(days=days_back)
        batch_size = 10  # Search 10 CFDA codes at a time

        for i in range(0, len(cfda_codes), batch_size):
            batch = cfda_codes[i:i + batch_size]
            logger.info(f"Fetching grants for CFDA codes: {batch}")

            page = 1
            while True:
                grants, total_count = self.search(
                    posted_from=posted_from,
                    cfda_numbers=batch,
                    rows=25,
                    page=page,
                )

                if not grants:
                    break

                all_grants.extend(grants)

                if len(grants) < 25 or page * 25 >= total_count:
                    break

                page += 1
                time.sleep(0.3)

                if page > 200:
                    break

            time.sleep(0.5)  # Pause between batches

        # Deduplicate by opportunity_id (same grant might match multiple CFDA codes)
        seen = set()
        unique_grants = []
        for grant in all_grants:
            if grant.opportunity_id not in seen:
                seen.add(grant.opportunity_id)
                unique_grants.append(grant)

        logger.info(f"Total unique grants for CFDA codes: {len(unique_grants)}")
        return unique_grants

    def get_opportunity_details(self, opportunity_id: str) -> Optional[dict]:
        """
        Get full details for a specific opportunity.

        This provides more detail than the search results.
        """
        url = f"https://www.grants.gov/grantsws/rest/opportunity/details"
        params = {"oppId": opportunity_id}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get details for {opportunity_id}: {e}")
            return None
