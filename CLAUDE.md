# Turbo Disco - Claude Code Context

## Project Overview

Automated newsletter pipeline for curating federal clean energy grant opportunities. Fetches from Grants.gov, filters by CFDA codes and keywords, generates AI summaries, and publishes to Beehiiv.

**Goal:** Single-command weekly execution with minimal human intervention.

## Codebase Structure

```
turbo-disco/
├── config/
│   ├── cfda_codes.yaml     # 44 CFDA codes (DOE, EPA, USDA, DOT, DOI, DOC)
│   ├── keywords.yaml       # 14 primary + 13 secondary keywords
│   └── settings.py         # API keys from .env, paths, constants
├── scripts/
│   ├── weekly_fetch.py     # Phase 1 standalone script
│   └── run_pipeline.py     # Full pipeline orchestration
├── src/
│   ├── grants/             # Phase 1: Data pipeline (COMPLETE)
│   │   ├── fetch.py        # Grants.gov API client
│   │   ├── filter.py       # CFDA + keyword matching
│   │   ├── dedupe.py       # Hash-based deduplication
│   │   └── models.py       # Grant dataclass, SQLite database
│   ├── summarize/          # Phase 2: AI summaries (COMPLETE)
│   │   ├── claude_client.py # Anthropic API with retry
│   │   ├── prompts.py      # 5 prompt templates
│   │   ├── summarizer.py   # Batch summarization
│   │   └── content_types.py # Newsletter data classes
│   ├── review/             # Phase 3: Auto-approval (COMPLETE)
│   │   ├── approval.py     # Auto-approve by match type
│   │   ├── reviewer.py     # Approval workflow
│   │   └── cli.py          # Optional manual review
│   └── publish/            # Phase 4: Beehiiv publishing (COMPLETE)
│       ├── beehiiv.py      # Beehiiv API v2 client
│       ├── composer.py     # Newsletter composition
│       ├── templates.py    # HTML email templates
│       └── scheduler.py    # Send time utilities
├── data/                   # SQLite database (gitignored)
├── logs/                   # Pipeline logs, draft HTML
├── .env                    # API keys (gitignored)
└── venv/                   # Python virtual environment
```

## Key Commands

```bash
# Activate virtual environment
cd "/Users/jasonwilliamson/Desktop/Turbo Disco"
source venv/bin/activate

# Run full pipeline (dry run - no publish)
python scripts/run_pipeline.py --dry-run --days 7

# Run and schedule for Monday 9am
python scripts/run_pipeline.py --schedule monday

# Run and publish immediately
python scripts/run_pipeline.py --publish-now

# Run with manual review of flagged grants
python scripts/run_pipeline.py --review
```

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-...     # Required for summarization
BEEHIIV_API_KEY=bh_...           # Required for publishing
BEEHIIV_PUBLICATION_ID=pub_...   # Required for publishing
```

## Pipeline Flow

```
Grants.gov API
    ↓
[fetch.py] → Pull grants from last N days
    ↓
[filter.py] → Match CFDA codes + keywords
    ↓
[dedupe.py] → Skip already-processed grants
    ↓
[summarizer.py] → Generate AI summaries (Claude)
    ↓
[reviewer.py] → Auto-approve high-confidence matches
    ↓
[composer.py] → Build newsletter HTML
    ↓
[beehiiv.py] → Create draft → Schedule/Publish
```

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Data Pipeline | ✅ Complete | Fetch, filter, dedupe, database |
| Phase 2: Summarization | ✅ Complete | Claude API integration |
| Phase 3: Auto-Approval | ✅ Complete | CFDA/keyword-based approval |
| Phase 4: Publishing | ✅ Complete | Beehiiv API integration |
| Weekly Automation | ⏳ Pending | Cron job setup |

## Next Steps

1. **Add Beehiiv credentials** to `.env` when site is available
2. **Test full pipeline** with `--dry-run` to verify end-to-end
3. **Run first live test** with `--publish-now` or `--schedule monday`
4. **Set up cron job** for weekly automation:
   ```bash
   # Every Sunday 8pm - prepare Monday newsletter
   0 20 * * 0 cd /path/to/turbo-disco && source venv/bin/activate && python scripts/run_pipeline.py
   ```
5. **Start marketing** - see MARKETING.md for subscriber growth plan

## Related Documentation

- **PLAN.md** - Newsletter format, audience, pricing strategy
- **MARKETING.md** - Subscriber acquisition plan, growth phases
