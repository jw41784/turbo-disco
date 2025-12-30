"""
Grants.gov API client for fetching grant opportunities.

API Documentation: https://www.grants.gov/web/grants/s2s/applicant/schemas/grants-funding-synopsis.html
Search API: https://www.grants.gov/grantsws/rest/opportunities/search
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

from .models import Grant

logger = logging.getLogger(__name__)


class GrantsGovClient:
    """Client for Grants.gov REST API."""

    BASE_URL = "https://www.grants.gov/grantsws/rest/opportunities/search"

    # Opportunity statuses we care about
    ACTIVE_STATUSES = ["posted", "forecasted"]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize client.

        Note: Grants.gov search API may not require an API key for basic searches.
        The API key is used for higher rate limits and S2S operations.
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["X-API-KEY"] = api_key

    def search(
        self,
        posted_from: Optional[datetime] = None,
        posted_to: Optional[datetime] = None,
        cfda_numbers: Optional[list[str]] = None,
        keyword: Optional[str] = None,
        rows: int = 100,
        start_record: int = 0,
    ) -> list[Grant]:
        """
        Search for grant opportunities.

        Args:
            posted_from: Start date for posted date filter
            posted_to: End date for posted date filter
            cfda_numbers: List of CFDA numbers to filter by
            keyword: Keyword search term
            rows: Number of results per request (max 100)
            start_record: Starting record for pagination

        Returns:
            List of Grant objects
        """
        params = {
            "rows": min(rows, 100),
            "startRecord": start_record,
            "sortBy": "postedDate|desc",
            "oppStatus": "posted",  # Only active opportunities
        }

        if posted_from:
            params["postedFrom"] = posted_from.strftime("%m/%d/%Y")
        if posted_to:
            params["postedTo"] = posted_to.strftime("%m/%d/%Y")
        if cfda_numbers:
            params["cfda"] = ",".join(cfda_numbers)
        if keyword:
            params["keyword"] = keyword

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

        opportunities = data.get("oppHits", [])
        grants = []

        for opp in opportunities:
            try:
                grant = Grant.from_api_response(opp)
                grants.append(grant)
            except Exception as e:
                logger.warning(f"Failed to parse opportunity {opp.get('opportunityId')}: {e}")

        logger.info(f"Fetched {len(grants)} grants (total hits: {data.get('totalCount', 0)})")
        return grants

    def fetch_recent(self, days_back: int = 7) -> list[Grant]:
        """
        Fetch all grants posted in the last N days.

        Handles pagination to get all results.
        """
        posted_from = datetime.now() - timedelta(days=days_back)
        posted_to = datetime.now()

        all_grants = []
        start_record = 0
        rows_per_page = 100

        while True:
            grants = self.search(
                posted_from=posted_from,
                posted_to=posted_to,
                rows=rows_per_page,
                start_record=start_record,
            )

            if not grants:
                break

            all_grants.extend(grants)
            start_record += rows_per_page

            # Rate limiting - be nice to the API
            time.sleep(0.5)

            # Safety limit
            if start_record > 10000:
                logger.warning("Hit pagination safety limit at 10,000 records")
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

            start_record = 0
            while True:
                grants = self.search(
                    posted_from=posted_from,
                    cfda_numbers=batch,
                    rows=100,
                    start_record=start_record,
                )

                if not grants:
                    break

                all_grants.extend(grants)
                start_record += 100
                time.sleep(0.5)

                if start_record > 5000:
                    break

            time.sleep(1)  # Pause between batches

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
