"""
Configuration settings for Turbo-Disco.

API keys should be set via environment variables or .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Database
DATABASE_PATH = DATA_DIR / "grants.db"

# Grants.gov API
# Docs: https://www.grants.gov/web/grants/s2s/applicant/schemas/grants-funding-synopsis.html
GRANTS_GOV_API_KEY = os.getenv("GRANTS_GOV_API_KEY", "")
GRANTS_GOV_BASE_URL = "https://www.grants.gov/grantsws/rest/opportunities/search"

# Anthropic Claude API (Phase 2)
# Docs: https://docs.anthropic.com/
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Beehiiv API (Phase 4)
# Docs: https://developers.beehiiv.com/docs/v2
BEEHIIV_API_KEY = os.getenv("BEEHIIV_API_KEY", "")
BEEHIIV_PUBLICATION_ID = os.getenv("BEEHIIV_PUBLICATION_ID", "")

# Fetch settings
FETCH_DAYS_BACK = 7  # How many days back to look for grants
MAX_RESULTS_PER_REQUEST = 100

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "turbo_disco.log"
