"""
Prompt templates for grant summarization.
All prompts designed to produce consistent, newsletter-ready content.
"""

SYSTEM_PROMPT = """You are a professional grant writer creating content for a clean energy grants newsletter. Your audience is grant professionals at startups, nonprofits, municipalities, and university research labs.

Writing guidelines:
- Be direct and professional, no hype or exclamation points
- Assume readers understand grant basics (NOFO, RFP, etc.)
- Focus on actionable information: what it funds, who's eligible, key deadlines
- Use specific numbers when available (funding amounts, deadline dates)
- Keep language concise and scannable
"""

GRANT_SUMMARY_PROMPT = """Summarize this grant opportunity in 75-100 words. Include:
1. What activities/projects it funds (be specific)
2. Who is eligible (organization types, any restrictions)
3. Why this matters or what makes it notable

Grant data:
Title: {title}
Agency: {agency}
CFDA: {cfda_numbers}
Description: {description}
Award Range: {award_range}
Expected Awards: {expected_awards}
Deadline: {close_date}
Eligibility: {eligibility_codes}
"""

FEATURED_OPPORTUNITY_PROMPT = """Write the featured story for this week's most important grant opportunity in 150-200 words.

Cover:
1. What this grant funds and why it's significant
2. Funding amount and timeline
3. Who should apply (be specific about ideal applicants)
4. One concrete tip for a strong application
5. Key deadline

Grant data:
Title: {title}
Agency: {agency}
Description: {description}
Award Range: {award_range}
Expected Awards: {expected_awards}
Deadline: {close_date}
URL: {url}
"""

DEADLINE_ALERT_PROMPT = """Write a 2-sentence deadline alert for this grant.
First sentence: what it funds and amount.
Second sentence: deadline and one key eligibility point.

Grant data:
Title: {title}
Agency: {agency}
Award Ceiling: {award_ceiling}
Deadline: {close_date}
Eligibility: {eligibility_codes}
"""

TIP_OF_THE_WEEK_PROMPT = """Generate one actionable grant-writing tip relevant to clean energy/climate grants.
Keep it to 2-3 sentences. Be specific and practical, not generic advice.

Topics to consider: budget justification, letters of support, compliance requirements, common mistakes, agency-specific preferences, DOE vs EPA application differences, required certifications, timeline planning.

This week's featured grants for context:
{grant_titles}
"""

QUICK_HIT_PROMPT = """Write a one-line summary (max 25 words) of this grant opportunity.
Include: funding amount, what it funds, and deadline.

Grant: {title}
Amount: {award_ceiling}
Deadline: {close_date}
"""
