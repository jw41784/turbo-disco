"""
Beehiiv API client for newsletter publishing.
API Docs: https://developers.beehiiv.com/docs/v2
"""

import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class BeehiivClient:
    """Client for Beehiiv API v2."""

    BASE_URL = "https://api.beehiiv.com/v2"

    def __init__(self, api_key: str, publication_id: str):
        self.api_key = api_key
        self.publication_id = publication_id
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        self.max_retries = 3
        self.base_delay = 2.0

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make API request with retry logic."""
        url = f"{self.BASE_URL}/publications/{self.publication_id}/{endpoint}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)

                if response.status_code == 429:
                    # Rate limited
                    retry_after = int(
                        response.headers.get(
                            "Retry-After", self.base_delay * (2**attempt)
                        )
                    )
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json() if response.text else {}

            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.base_delay * (2**attempt))

        raise RuntimeError("Max retries exceeded")

    def create_post(
        self,
        title: str,
        content: str,
        subtitle: Optional[str] = None,
        status: str = "draft",
        scheduled_at: Optional[str] = None,
        send_to: str = "all",  # "all", "free", "premium"
    ) -> dict:
        """
        Create a new newsletter post.

        Args:
            title: Post title (used as subject line)
            content: HTML content of the newsletter
            subtitle: Preview text
            status: "draft", "confirmed" (scheduled), or "archived"
            scheduled_at: ISO timestamp for scheduled send
            send_to: Audience segment

        Returns:
            Created post data including post_id
        """
        payload = {
            "title": title,
            "content": content,
            "status": status,
            "send_to": send_to,
        }

        if subtitle:
            payload["subtitle"] = subtitle

        if scheduled_at and status == "confirmed":
            payload["scheduled_at"] = scheduled_at

        logger.info(f"Creating post: {title}")
        result = self._request("POST", "posts", json=payload)
        post_id = result.get("data", {}).get("id")
        logger.info(f"Post created with ID: {post_id}")

        return result.get("data", {})

    def update_post(self, post_id: str, **updates) -> dict:
        """Update an existing post."""
        logger.info(f"Updating post: {post_id}")
        return self._request("PATCH", f"posts/{post_id}", json=updates).get("data", {})

    def publish_post(self, post_id: str) -> dict:
        """Immediately publish a post (send newsletter)."""
        logger.info(f"Publishing post: {post_id}")
        return self.update_post(post_id, status="confirmed")

    def schedule_post(self, post_id: str, send_at: str) -> dict:
        """Schedule a post for future sending."""
        logger.info(f"Scheduling post {post_id} for {send_at}")
        return self.update_post(post_id, status="confirmed", scheduled_at=send_at)

    def get_post(self, post_id: str) -> dict:
        """Get post details."""
        return self._request("GET", f"posts/{post_id}").get("data", {})

    def list_posts(self, status: Optional[str] = None, limit: int = 10) -> list:
        """List posts with optional status filter."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._request("GET", "posts", params=params).get("data", [])

    def delete_post(self, post_id: str) -> bool:
        """Delete a draft post."""
        try:
            self._request("DELETE", f"posts/{post_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete post: {e}")
            return False
