# Turbo-Disco: Clean Energy Grants Newsletter

## What This Is

A curated newsletter delivering clean energy and climate grant opportunities to subscribers. AI handles the data processing; you provide editorial judgment.

**Platform**: Beehiiv (~$100/month)
**Time commitment**: ~45 min/day
**Niche**: Clean energy and climate grants (CFDA codes 81.xxx, specific EPA/USDA programs)

---

## Core Workflow

```
Grants.gov API → Python scripts → Filter by CFDA codes → Claude API drafts summaries → You review/edit → Beehiiv API publishes
```

### Daily Process

1. **Automated**: Scripts pull new/updated grants from Grants.gov
2. **Automated**: Filter to clean energy/climate programs
3. **Automated**: Claude generates draft summaries (key dates, eligibility, amounts)
4. **Manual (~30 min)**: Review drafts, add editorial insight, catch errors
5. **Automated**: Publish to Beehiiv via API

---

## Target Audience

Organizations pursuing clean energy and climate funding:
- Clean energy startups
- Environmental nonprofits
- University research labs (climate science, renewable energy)
- Municipal sustainability offices
- Clean tech companies

**Not** targeting: General nonprofits, all researchers, government contractors, etc.

---

## Development Phases

### Phase 1: Data Pipeline (Week 1-3)

**Goal**: Reliably pull and filter grant data

- [ ] Set up Grants.gov API access
- [ ] Identify relevant CFDA codes (DOE 81.xxx, EPA climate programs, USDA rural energy)
- [ ] Build Python script to fetch new/modified grants daily
- [ ] Filter logic for clean energy relevance
- [ ] Store results (simple JSON or SQLite)

**Deliverable**: Script that outputs today's relevant grants as structured data

### Phase 2: AI Summarization (Week 2-3)

**Goal**: Generate useful draft summaries

- [ ] Claude API integration
- [ ] Prompt engineering for grant summaries:
  - Deadline and key dates
  - Funding amount/range
  - Eligibility requirements (who can apply)
  - Brief description of what's funded
  - Direct link to opportunity
- [ ] Output format suitable for newsletter

**Deliverable**: Script that takes grant data → outputs draft newsletter content

### Phase 3: Review Workflow (Week 4-5)

**Goal**: Efficient human review process

- [ ] Simple review interface (Notion database, Google Doc, or basic CLI tool)
- [ ] Ability to edit/approve/reject each item
- [ ] Track what's been published

**Deliverable**: Workflow where you can review 10-20 grants in 30 minutes

### Phase 4: Publishing (Week 6-7)

**Goal**: Automated publishing to Beehiiv

- [ ] Beehiiv account setup and API access
- [ ] Newsletter template design
- [ ] API integration to create/schedule posts
- [ ] End-to-end test of full pipeline

**Deliverable**: One-command publish from approved content to Beehiiv

---

## Project Structure

```
turbo-disco/
├── README.md
├── PLAN.md
├── src/
│   ├── grants/
│   │   ├── fetch.py          # Grants.gov API client
│   │   ├── filter.py         # CFDA code filtering
│   │   └── models.py         # Grant data structures
│   ├── summarize/
│   │   ├── claude_client.py  # Claude API wrapper
│   │   └── prompts.py        # Prompt templates
│   ├── publish/
│   │   └── beehiiv.py        # Beehiiv API client
│   └── review/
│       └── workflow.py       # Review interface
├── data/
│   └── grants.db             # Local SQLite for tracking
├── config/
│   ├── cfda_codes.yaml       # Target grant programs
│   └── settings.py           # API keys, config
├── scripts/
│   ├── daily_fetch.py        # Cron job entry point
│   └── publish.py            # Manual publish trigger
└── requirements.txt
```

---

## Key CFDA Codes to Track

| Code | Agency | Program |
|------|--------|---------|
| 81.086 | DOE | Conservation Research and Development |
| 81.087 | DOE | Renewable Energy Research and Development |
| 81.089 | DOE | Fossil Energy Research and Development |
| 81.117 | DOE | Energy Efficiency and Renewable Energy Information Dissemination |
| 81.119 | DOE | State Energy Program |
| 81.041 | DOE | State Energy Program |
| 66.039 | EPA | National Clean Diesel Emissions Reduction Program |
| 66.045 | EPA | Climate Pollution Reduction Grants |
| 10.868 | USDA | Rural Energy for America Program |

*Expand this list based on research*

---

## Success Metrics

| Milestone | Target |
|-----------|--------|
| Pipeline working | End of Week 3 |
| First newsletter sent | End of Week 7 |
| 500 subscribers | Month 3 |
| 2,000 subscribers | Month 6 |
| First paid tier test | After 2,000 subscribers |

---

## What This Is NOT (Yet)

- Custom web application
- User accounts and authentication
- Payment processing
- Searchable database
- Interactive tools
- Multiple content formats

These come **after** proving demand with 2,000+ subscribers.

---

## Next Steps

1. Set up Python project structure
2. Get Grants.gov API access
3. Research and finalize CFDA code list
4. Build initial fetch script

---

*Last Updated: December 29, 2025*
