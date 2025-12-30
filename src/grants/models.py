"""
Data models and database schema for grant tracking.
"""

import sqlite3
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum


class GrantStatus(Enum):
    """Status of a grant in our pipeline."""
    NEW = "new"              # Just fetched, not yet processed
    UPDATED = "updated"      # Existing grant with significant changes
    PROCESSED = "processed"  # Summarized, ready for review
    APPROVED = "approved"    # Approved for newsletter
    PUBLISHED = "published"  # Published in newsletter
    SKIPPED = "skipped"      # Manually skipped


class MatchType(Enum):
    """How the grant was matched to our filters."""
    CFDA = "cfda"            # Matched by CFDA code
    PRIMARY_KEYWORD = "primary_keyword"    # Matched primary keyword
    SECONDARY_KEYWORD = "secondary_keyword"  # Matched secondary keyword (needs review)


@dataclass
class Grant:
    """Represents a federal grant opportunity."""
    opportunity_id: str       # Grants.gov opportunity ID
    opportunity_number: str   # Funding opportunity number
    title: str
    agency: str
    cfda_numbers: list[str]   # Can have multiple
    description: str
    posted_date: str          # ISO format
    close_date: Optional[str] # ISO format, None if rolling
    award_floor: Optional[int]
    award_ceiling: Optional[int]
    expected_awards: Optional[int]
    eligibility_codes: list[str]
    url: str

    # Pipeline tracking
    match_type: Optional[str] = None
    match_value: Optional[str] = None  # Which CFDA or keyword matched
    content_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """
        Compute hash of significant fields to detect meaningful changes.
        Ignores minor text changes, focuses on: deadline, amount, eligibility.
        """
        significant_fields = {
            "close_date": self.close_date,
            "award_floor": self.award_floor,
            "award_ceiling": self.award_ceiling,
            "eligibility_codes": sorted(self.eligibility_codes) if self.eligibility_codes else [],
        }
        content = json.dumps(significant_fields, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_api_response(cls, data: dict) -> "Grant":
        """Create Grant from Grants.gov API response."""
        return cls(
            opportunity_id=str(data.get("opportunityId", "")),
            opportunity_number=data.get("opportunityNumber", ""),
            title=data.get("opportunityTitle", ""),
            agency=data.get("agencyName", ""),
            cfda_numbers=data.get("cfdaNumbers", "").split(",") if data.get("cfdaNumbers") else [],
            description=data.get("description", ""),
            posted_date=data.get("postedDate", ""),
            close_date=data.get("closeDate"),
            award_floor=data.get("awardFloor"),
            award_ceiling=data.get("awardCeiling"),
            expected_awards=data.get("expectedNumberOfAwards"),
            eligibility_codes=data.get("eligibilityCodes", "").split(",") if data.get("eligibilityCodes") else [],
            url=f"https://www.grants.gov/search-results-detail/{data.get('opportunityId', '')}",
        )


class GrantDatabase:
    """SQLite database for tracking processed grants."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS grants (
        opportunity_id TEXT PRIMARY KEY,
        opportunity_number TEXT,
        title TEXT NOT NULL,
        agency TEXT,
        cfda_numbers TEXT,  -- JSON array
        description TEXT,
        posted_date TEXT,
        close_date TEXT,
        award_floor INTEGER,
        award_ceiling INTEGER,
        expected_awards INTEGER,
        eligibility_codes TEXT,  -- JSON array
        url TEXT,
        match_type TEXT,
        match_value TEXT,
        content_hash TEXT,
        status TEXT DEFAULT 'new',
        first_seen_at TEXT,
        last_updated_at TEXT,
        published_in_issue TEXT,
        summary TEXT,
        notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_status ON grants(status);
    CREATE INDEX IF NOT EXISTS idx_close_date ON grants(close_date);
    CREATE INDEX IF NOT EXISTS idx_posted_date ON grants(posted_date);

    CREATE TABLE IF NOT EXISTS fetch_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fetched_at TEXT,
        grants_fetched INTEGER,
        grants_matched INTEGER,
        grants_new INTEGER,
        grants_updated INTEGER,
        error TEXT
    );
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.SCHEMA)

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_grant(self, opportunity_id: str) -> Optional[dict]:
        """Get existing grant by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM grants WHERE opportunity_id = ?",
                (opportunity_id,)
            ).fetchone()
            return dict(row) if row else None

    def upsert_grant(self, grant: Grant, status: GrantStatus = GrantStatus.NEW) -> tuple[bool, bool]:
        """
        Insert or update grant. Returns (is_new, is_updated).

        is_new: True if this is a brand new grant
        is_updated: True if existing grant had significant changes
        """
        now = datetime.utcnow().isoformat()
        content_hash = grant.compute_hash()

        existing = self.get_grant(grant.opportunity_id)

        if existing is None:
            # New grant
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO grants (
                        opportunity_id, opportunity_number, title, agency,
                        cfda_numbers, description, posted_date, close_date,
                        award_floor, award_ceiling, expected_awards,
                        eligibility_codes, url, match_type, match_value,
                        content_hash, status, first_seen_at, last_updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    grant.opportunity_id, grant.opportunity_number, grant.title,
                    grant.agency, json.dumps(grant.cfda_numbers), grant.description,
                    grant.posted_date, grant.close_date, grant.award_floor,
                    grant.award_ceiling, grant.expected_awards,
                    json.dumps(grant.eligibility_codes), grant.url,
                    grant.match_type, grant.match_value, content_hash,
                    status.value, now, now
                ))
            return True, False

        # Existing grant - check for significant changes
        is_updated = existing["content_hash"] != content_hash

        if is_updated:
            new_status = GrantStatus.UPDATED.value
        else:
            new_status = existing["status"]  # Keep current status

        with self._get_conn() as conn:
            conn.execute("""
                UPDATE grants SET
                    title = ?, agency = ?, cfda_numbers = ?, description = ?,
                    posted_date = ?, close_date = ?, award_floor = ?,
                    award_ceiling = ?, expected_awards = ?, eligibility_codes = ?,
                    url = ?, content_hash = ?, status = ?, last_updated_at = ?
                WHERE opportunity_id = ?
            """, (
                grant.title, grant.agency, json.dumps(grant.cfda_numbers),
                grant.description, grant.posted_date, grant.close_date,
                grant.award_floor, grant.award_ceiling, grant.expected_awards,
                json.dumps(grant.eligibility_codes), grant.url, content_hash,
                new_status, now, grant.opportunity_id
            ))

        return False, is_updated

    def get_grants_for_review(self) -> list[dict]:
        """Get grants ready for review (new or updated)."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM grants
                WHERE status IN ('new', 'updated')
                ORDER BY
                    CASE WHEN close_date IS NOT NULL THEN close_date ELSE '9999-12-31' END,
                    posted_date DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def update_status(self, opportunity_id: str, status: GrantStatus, **kwargs):
        """Update grant status and optional fields."""
        updates = ["status = ?", "last_updated_at = ?"]
        values = [status.value, datetime.utcnow().isoformat()]

        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)

        values.append(opportunity_id)

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE grants SET {', '.join(updates)} WHERE opportunity_id = ?",
                values
            )

    def log_fetch(self, grants_fetched: int, grants_matched: int,
                  grants_new: int, grants_updated: int, error: Optional[str] = None):
        """Log a fetch run for monitoring."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO fetch_log (fetched_at, grants_fetched, grants_matched,
                                       grants_new, grants_updated, error)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                grants_fetched, grants_matched, grants_new, grants_updated, error
            ))

    def get_stats(self) -> dict:
        """Get current database statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM grants").fetchone()[0]
            by_status = {}
            for row in conn.execute("SELECT status, COUNT(*) FROM grants GROUP BY status"):
                by_status[row[0]] = row[1]

            upcoming = conn.execute("""
                SELECT COUNT(*) FROM grants
                WHERE close_date >= date('now') AND status NOT IN ('published', 'skipped')
            """).fetchone()[0]

            return {
                "total": total,
                "by_status": by_status,
                "upcoming_deadlines": upcoming
            }
