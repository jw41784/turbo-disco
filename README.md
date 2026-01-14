# Turbo Disco

Automated newsletter pipeline for curating federal clean energy grant opportunities.

**Value proposition:** Find relevant funding in 5 minutes, not 5 hours.

## Features

- Fetches grants from Grants.gov API (no authentication required)
- Filters by 44 CFDA codes (DOE, EPA, USDA, DOT, DOI, DOC)
- Matches 27 clean energy keywords
- Generates AI summaries via Claude API
- Auto-approves high-confidence matches
- Publishes to Beehiiv newsletter platform

## Quick Start

```bash
# 1. Clone and enter directory
cd turbo-disco

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env with your keys

# 5. Run pipeline (dry run)
python scripts/run_pipeline.py --dry-run --days 7
```

## Usage

```bash
# Dry run - generates draft without publishing
python scripts/run_pipeline.py --dry-run

# Schedule newsletter for Monday 9am
python scripts/run_pipeline.py --schedule monday

# Publish immediately
python scripts/run_pipeline.py --publish-now

# Include manual review step
python scripts/run_pipeline.py --review
```

## Configuration

### Required API Keys (.env)

| Variable | Source |
|----------|--------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `BEEHIIV_API_KEY` | Beehiiv → Settings → Integrations → API |
| `BEEHIIV_PUBLICATION_ID` | Beehiiv → Settings → Publication URL |

### Grant Filters

Edit `config/cfda_codes.yaml` and `config/keywords.yaml` to customize which grants are matched.

## Project Structure

```
├── scripts/run_pipeline.py   # Main entry point
├── src/grants/               # Fetch, filter, dedupe
├── src/summarize/            # Claude API integration
├── src/review/               # Auto-approval logic
├── src/publish/              # Beehiiv publishing
├── config/                   # CFDA codes, keywords, settings
└── logs/                     # Pipeline logs and drafts
```

## Documentation

- **CLAUDE.md** - Technical context for Claude Code
- **PLAN.md** - Newsletter format and business strategy
- **MARKETING.md** - Subscriber growth plan

## Costs

| Service | Monthly Cost |
|---------|-------------|
| Beehiiv Scale | $49 |
| Claude API | $15-30 |
| **Total** | ~$70-90 |

## License

MIT
