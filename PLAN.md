# Turbo-Disco: Clean Energy Grants Newsletter

## What This Is

A curated newsletter delivering clean energy and climate grant opportunities to subscribers. AI handles the data processing; you provide editorial judgment.

**Platform**: Beehiiv
**Time commitment**: ~45 min per issue
**Niche**: Clean energy and climate grants (DOE, EPA, USDA programs)

---

## Publishing Cadence

**Start**: Weekly (every Monday)
**Upgrade to 2x/week**: After 1,000 subscribers and stable workflow
**Upgrade to daily**: After 2,000 subscribers (if volume justifies it)

---

## Estimated Monthly Costs

| Item | Cost |
|------|------|
| Beehiiv Scale plan | $49 |
| Claude API (~50K tokens/week) | $15-30 |
| Server (if needed for cron) | $5-10 |
| **Total** | **~$70-90/month** |

---

## Core Workflow

```
Grants.gov API → Python scripts → Filter (CFDA + keywords) → Dedupe → Claude API drafts → CLI review → Beehiiv API publishes
```

### Weekly Process

1. **Automated**: Scripts pull new/updated grants from Grants.gov
2. **Automated**: Filter by CFDA codes and keyword matching
3. **Automated**: Deduplicate against previously processed grants
4. **Automated**: Claude generates draft summaries
5. **Manual (~30 min)**: Review drafts in CLI, approve/edit/skip
6. **Automated**: Publish approved content to Beehiiv via API

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

## Newsletter Format

### Issue Structure

Each weekly issue contains:

1. **Header**: Issue number, date, one-line hook
2. **Featured Opportunity** (1): Biggest/most notable grant that week, 150-200 words
3. **New Opportunities** (3-5): New grants with summaries, 75-100 words each
4. **Deadline Alerts** (2-3): Grants closing in next 14 days
5. **Quick Hits** (3-5): One-liner mentions of smaller or niche opportunities
6. **Tip of the Week**: One actionable grant-writing or compliance tip
7. **Footer**: Unsubscribe, feedback link, social links

### Subject Line Format

```
[Clean Energy Grants] {Featured Opportunity Name} + {X} new opportunities
```

Example: `[Clean Energy Grants] $50M DOE Hydrogen Hub + 7 new opportunities`

### Per-Grant Summary Format

```
**{Grant Title}**
Agency: {Agency} | Deadline: {Date} | Amount: {Range}

{2-3 sentence description: what it funds, who's eligible, why it matters}

→ [Apply here]({link})
```

---

## Development Phases

### Phase 1: Data Pipeline (Week 1-3)

**Goal**: Reliably pull, filter, and deduplicate grant data

- [ ] Set up Grants.gov API access
- [ ] Build Python script to fetch new/modified grants
- [ ] Filter logic: CFDA codes + keyword matching
- [ ] SQLite database for tracking:
  - [ ] Store grant IDs already processed
  - [ ] Detect: new grant vs. updated grant vs. no change
  - [ ] Only surface new grants OR significant updates (deadline change, amount change, eligibility change)
- [ ] Hash grant content to detect meaningful changes vs. trivial updates

**Deliverable**: Script that outputs this week's relevant NEW grants as structured data

**Deduplication Rules**:
- New opportunity ID → always include
- Same ID, deadline changed → include with "UPDATED" flag
- Same ID, amount changed → include with "UPDATED" flag
- Same ID, minor text changes only → skip

### Phase 2: AI Summarization (Week 2-3)

**Goal**: Generate useful draft summaries using tested prompts

- [ ] Claude API integration
- [ ] Implement prompt templates (see below)
- [ ] Output format matching newsletter structure
- [ ] Batch processing for efficiency

**Deliverable**: Script that takes grant data → outputs draft newsletter content

#### Prompt Templates

**Grant Summary Prompt**:
```
You are writing for a newsletter about clean energy and climate grants.
Your audience is grant professionals at startups, nonprofits, and universities.

Summarize this grant opportunity in 75-100 words. Include:
1. What activities/projects it funds (be specific)
2. Who is eligible (organization types, any restrictions)
3. Why this matters or what makes it notable

Write in a direct, professional tone. No hype or exclamation points.
Assume readers understand grant basics—don't explain what a NOFO is.

Grant data:
{grant_json}
```

**Featured Opportunity Prompt** (for the lead story):
```
You are writing the featured story for a clean energy grants newsletter.
This is the most important opportunity of the week.

Write 150-200 words covering:
1. What this grant funds and why it's significant
2. Funding amount and timeline
3. Who should apply (be specific about ideal applicants)
4. One concrete tip for a strong application
5. Key deadline

Grant data:
{grant_json}
```

**Deadline Alert Prompt**:
```
Write a 2-sentence deadline alert for this grant.
First sentence: what it funds and amount.
Second sentence: deadline and one key eligibility point.

Grant data:
{grant_json}
```

**Tip of the Week Prompt**:
```
Generate one actionable grant-writing tip relevant to clean energy/climate grants.
Keep it to 2-3 sentences. Be specific and practical, not generic advice.
Example topics: budget justification, letters of support, compliance requirements,
common mistakes, agency-specific preferences.

This week's featured grants for context:
{grant_titles}
```

### Phase 3: Review Workflow (Week 4-5)

**Goal**: Efficient CLI-based human review

**Interface**: Command-line tool (fastest for daily use)

- [ ] Display each grant summary with full context
- [ ] Keyboard commands:
  - `a` = approve as-is
  - `e` = edit (opens in $EDITOR)
  - `s` = skip (don't include this week)
  - `f` = flag for featured slot
  - `q` = quit and save progress
- [ ] Show running count: "Approved: 5 | Skipped: 2 | Remaining: 8"
- [ ] Save review state (can quit and resume)
- [ ] Track which grants have been published (prevent duplicates across issues)

**Deliverable**: Review 15-20 grants in 30 minutes or less

### Phase 4: Publishing & Operations (Week 6-7)

**Goal**: Automated publishing with error handling

**Beehiiv API docs**: https://developers.beehiiv.com/docs/v2

- [ ] Beehiiv account setup and API access
- [ ] Newsletter template matching format spec above
- [ ] API integration to create/schedule posts
- [ ] End-to-end test of full pipeline

**Error Handling**:
- [ ] Retry logic for API failures (3 attempts with exponential backoff)
- [ ] Logging to file for debugging
- [ ] Alert on failure: email or Slack webhook if daily run fails
- [ ] Graceful degradation: if Claude API fails, save raw grants for manual processing

**Monitoring**:
- [ ] Log each run: grants fetched, filtered, summarized, published
- [ ] Weekly summary: total grants processed, approval rate, any errors

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
│   │   ├── filter.py         # CFDA + keyword filtering
│   │   ├── dedupe.py         # Deduplication logic
│   │   └── models.py         # Grant data structures
│   ├── summarize/
│   │   ├── claude_client.py  # Claude API wrapper
│   │   └── prompts.py        # Prompt templates (from above)
│   ├── publish/
│   │   └── beehiiv.py        # Beehiiv API client
│   ├── review/
│   │   └── cli.py            # CLI review interface
│   └── utils/
│       ├── logging.py        # Logging setup
│       └── alerts.py         # Failure notifications
├── data/
│   └── grants.db             # SQLite: processed grants, review state
├── config/
│   ├── cfda_codes.yaml       # Target CFDA codes
│   ├── keywords.yaml         # Keyword filters
│   └── settings.py           # API keys, config
├── scripts/
│   ├── weekly_fetch.py       # Cron job entry point
│   ├── review.py             # Launch CLI review
│   └── publish.py            # Publish approved content
├── logs/
│   └── .gitkeep
└── requirements.txt
```

---

## CFDA Codes to Track

### Department of Energy (DOE 81.xxx)

| Code | Program | Notes |
|------|---------|-------|
| 81.041 | State Energy Program | Core program |
| 81.042 | Weatherization Assistance for Low-Income Persons | Major ongoing program |
| 81.086 | Conservation Research and Development | |
| 81.087 | Renewable Energy Research and Development | |
| 81.089 | Fossil Energy Research and Development | Carbon capture focus |
| 81.117 | Energy Efficiency and Renewable Energy Information Dissemination | |
| 81.119 | State Energy Program Special Projects | |
| 81.122 | Electricity Research, Development and Analysis | Grid modernization |
| 81.124 | Tribal Energy Development Capacity | Tribal clean energy |
| 81.126 | Federal Energy Regulatory Improvements | Grid modernization |
| 81.127 | Energy Efficient Appliance Rebate Program | State rebate programs |
| 81.128 | Energy Efficiency and Conservation Block Grant (EECBG) | Revived under BIL/IRA |
| 81.129 | Energy Efficiency and Renewable Energy Technology Application | Deployment programs |
| 81.135 | ARPA-E | Often biggest DOE opportunities |
| 81.138 | State Assistance for High Energy Cost Areas | Rural/remote energy |
| 81.140 | Clean Hydrogen Manufacturing, Recycling, and Electrolysis | IRA program |
| 81.141 | Industrial Decarbonization | IRA program |
| 81.250 | Energy Policy and Systems Analysis | Grid planning |

### Environmental Protection Agency (EPA 66.xxx)

**IRA-Funded Programs (Major - $40B+ total)**

| Code | Program | Funding |
|------|---------|---------|
| 66.046 | Climate Pollution Reduction Grants | $5B IRA |
| 66.047 | Greenhouse Gas Reduction Fund | $27B IRA (green bank) |
| 66.048 | Environmental and Climate Justice Block Grants | $3B IRA, community-focused |
| 66.049 | Grants to Reduce Air Pollution at Ports | $3B IRA, port electrification |
| 66.050 | Clean Heavy-Duty Vehicles | $1B IRA, fleet electrification |
| 66.051 | Methane Emissions Reduction Program | $1.55B IRA |

**Other EPA Programs**

| Code | Program |
|------|---------|
| 66.039 | National Clean Diesel Funding Assistance |
| 66.045 | Climate Pollution Reduction Grants |
| 66.956 | Targeted Air Shed Grants |

### Department of Agriculture (USDA 10.xxx)

| Code | Program | Notes |
|------|---------|-------|
| 10.865 | Biorefinery Assistance | |
| 10.866 | Repowering Assistance | Bioenergy for biorefineries |
| 10.867 | Bioenergy Program for Advanced Biofuels | Biofuel production |
| 10.868 | Rural Energy for America Program (REAP) | Major program |
| 10.870 | Rural Business Investment Program | Clean energy businesses |
| 10.881 | Powering Affordable Clean Energy (PACE) | IRA program, rural utilities |
| 10.884 | Empowering Rural America (New ERA) | $9.7B IRA, rural electric co-ops |
| 10.885 | Higher Blends Infrastructure Incentive | Biofuel infrastructure |

### Department of Transportation (DOT 20.xxx)

| Code | Program | Notes |
|------|---------|-------|
| 20.525 | State of Good Repair | Transit electrification |
| 20.526 | Bus and Bus Facilities / Low or No Emissions | Electric buses |
| 20.941 | SMART Grants | Technology pilots |
| 20.942 | NEVI Formula Program | EV charging infrastructure |

### Department of the Interior (DOI 15.xxx)

| Code | Program | Notes |
|------|---------|-------|
| 15.148 | Tribal Energy Development | Energy projects on tribal lands |
| 15.875 | Economic Development of Territories | Clean energy in PR, USVI, Guam |

### Department of Commerce (DOC 11.xxx)

| Code | Program | Notes |
|------|---------|-------|
| 11.300 | EDA Public Works | Clean energy infrastructure |
| 11.307 | EDA Economic Adjustment Assistance | Energy transition communities |
| 11.549 | NOAA Climate Program Office | Climate resilience |

---

## Keyword Filters (Supplement to CFDA)

Match grants containing these terms (case-insensitive):

### Primary Keywords (high confidence)
- clean energy
- renewable energy
- solar
- wind energy
- energy storage
- battery storage
- clean hydrogen
- EV charging
- electric vehicle infrastructure
- decarbonization
- carbon capture
- energy efficiency
- grid modernization
- climate resilience

### Secondary Keywords (review manually)
- sustainability
- greenhouse gas
- emissions reduction
- weatherization
- building electrification
- heat pump
- offshore wind
- geothermal
- hydropower
- nuclear energy
- smart grid
- distributed energy
- microgrid

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

1. Set up Python project structure with dependencies
2. Get Grants.gov API access (register at grants.gov)
3. Create SQLite schema for grant tracking
4. Build initial fetch + filter script
5. Test with one week of data

---

*Last Updated: December 29, 2025*
