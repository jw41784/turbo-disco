"""
Newsletter HTML templates.
Designed for email compatibility (tables, inline styles).
"""

NEWSLETTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

    <!-- Header -->
    <div style="border-bottom: 2px solid #2563eb; padding-bottom: 15px; margin-bottom: 25px;">
        <h1 style="margin: 0; color: #1e3a5f; font-size: 24px;">Clean Energy Grants Weekly</h1>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">{issue_date}</p>
    </div>

    <!-- Featured Opportunity -->
    {featured_section}

    <!-- New Opportunities -->
    <div style="margin-bottom: 30px;">
        <h2 style="color: #2563eb; font-size: 20px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px;">
            New Opportunities
        </h2>
        {opportunities_section}
    </div>

    <!-- Deadline Alerts -->
    {deadline_section}

    <!-- Quick Hits -->
    {quick_hits_section}

    <!-- Tip of the Week -->
    <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px; margin-bottom: 30px;">
        <h3 style="margin: 0 0 10px 0; color: #166534; font-size: 16px;">Tip of the Week</h3>
        <p style="margin: 0;">{tip_of_week}</p>
    </div>

    <!-- Footer -->
    <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; color: #666; font-size: 13px;">
        <p>You're receiving this because you subscribed to Clean Energy Grants Weekly.</p>
        <p>Find relevant funding in 5 minutes, not 5 hours.</p>
    </div>

</body>
</html>
"""

FEATURED_SECTION = """
<div style="background: #eff6ff; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
    <span style="background: #2563eb; color: white; font-size: 11px; padding: 3px 8px; border-radius: 4px; text-transform: uppercase;">Featured</span>
    <h2 style="margin: 15px 0 10px 0; color: #1e3a5f;">{title}</h2>
    <p style="margin: 0 0 15px 0;">{content}</p>
    <a href="{url}" style="display: inline-block; background: #2563eb; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: 500;">View Details</a>
</div>
"""

OPPORTUNITY_ITEM = """
<div style="margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #f3f4f6;">
    <h3 style="margin: 0 0 5px 0; color: #1e3a5f; font-size: 17px;">{title}</h3>
    <p style="margin: 0 0 10px 0; color: #666; font-size: 13px;">
        {agency} | Deadline: {deadline} | {award_range}
    </p>
    <p style="margin: 0 0 10px 0;">{summary}</p>
    <a href="{url}" style="color: #2563eb; text-decoration: none; font-weight: 500;">View Details</a>
</div>
"""

DEADLINE_SECTION = """
<div style="background: #fef2f2; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
    <h2 style="color: #dc2626; font-size: 18px; margin: 0 0 15px 0;">Deadline Alerts</h2>
    {alerts}
</div>
"""

DEADLINE_ITEM = """
<div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #fecaca;">
    <strong>{title}</strong> - {alert_text}
    <span style="color: #dc2626; font-weight: bold;"> ({days_until} days left)</span>
</div>
"""

QUICK_HITS_SECTION = """
<div style="margin-bottom: 30px;">
    <h2 style="color: #2563eb; font-size: 20px; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px;">
        Quick Hits
    </h2>
    <ul style="padding-left: 20px;">
        {quick_hits}
    </ul>
</div>
"""

QUICK_HIT_ITEM = '<li style="margin-bottom: 8px;">{text}</li>'
