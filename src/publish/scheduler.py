"""
Newsletter scheduling utilities.
"""

from datetime import datetime, timedelta


def get_next_monday_9am(timezone_offset: str = "-05:00") -> str:
    """
    Get next Monday at 9:00 AM for scheduling.

    Args:
        timezone_offset: Timezone offset string (default: Eastern Time)

    Returns:
        ISO format timestamp with timezone
    """
    now = datetime.now()
    days_ahead = (7 - now.weekday()) % 7  # Monday is 0
    if days_ahead == 0 and now.hour >= 9:
        days_ahead = 7  # If it's Monday after 9am, schedule for next Monday

    next_monday = now + timedelta(days=days_ahead)
    send_time = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)

    # Return ISO format with timezone
    return send_time.isoformat() + timezone_offset


def calculate_send_time(
    day: str = "monday", hour: int = 9, timezone_offset: str = "-05:00"
) -> str:
    """
    Calculate next occurrence of specified day/time.

    Args:
        day: Day of week (monday, tuesday, etc.)
        hour: Hour in 24h format
        timezone_offset: Timezone offset string

    Returns:
        ISO format timestamp with timezone
    """
    days_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    target_day = days_map.get(day.lower(), 0)
    now = datetime.now()

    days_ahead = (target_day - now.weekday()) % 7
    if days_ahead == 0 and now.hour >= hour:
        days_ahead = 7

    target = now + timedelta(days=days_ahead)
    target = target.replace(hour=hour, minute=0, second=0, microsecond=0)

    return target.isoformat() + timezone_offset


def get_issue_date() -> str:
    """Get the issue date string for the newsletter."""
    return datetime.now().strftime("%Y-%m-%d")


def get_display_date() -> str:
    """Get human-readable date for newsletter header."""
    return datetime.now().strftime("%B %d, %Y")
