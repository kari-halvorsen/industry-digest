"""
Industry Weekly Digest
----------------------
Pulls the latest news on target companies using the Anthropic API
with web search, organises it by news type, and sends a formatted
HTML email via Gmail every Monday morning.

Run manually:  python src/digest.py
Automated:     GitHub Actions (.github/workflows/weekly_digest.yml)

Required environment variables (set as GitHub Secrets):
  ANTHROPIC_API_KEY   — from platform.anthropic.com
  GMAIL_ADDRESS       — your Gmail address
  GMAIL_APP_PASSWORD  — Gmail App Password (not your login password)
  RECIPIENT_EMAIL     — where to send the digest (can be same as GMAIL_ADDRESS)
"""

import os
import json
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic

# ---------------------------------------------------------------------------
# Company list — edit freely, organised by tier
# ---------------------------------------------------------------------------

COMPANIES = {
    "Tier 1 — Cybersecurity": [
        "Palo Alto Networks", "Fortinet", "CrowdStrike", "Zscaler",
        "SentinelOne", "Tenable", "Rapid7", "Okta", "SailPoint",
        "Netskope", "Check Point Software", "Akamai Technologies",
        "Cloudflare", "Darktrace", "Rubrik",
    ],
    "Tier 2 — Enterprise SaaS": [
        "Datadog", "Dataiku", "Workiva", "MongoDB", "ServiceNow",
        "HubSpot", "Snowflake", "Zendesk", "Salesforce",
    ],
    "Tier 3 — Outliers": [
        "Mirakl", "Contentsquare", "Veeva Systems", "Sprinklr",
        "Coupa Software", "Docusign", "Workday", "Amadeus IT Group",
    ],
    "Tier 5 — AI Platforms": [
        "Anthropic", "OpenAI", "Mistral AI",
    ],
}

# Flatten for the API prompt
ALL_COMPANIES = [c for companies in COMPANIES.values() for c in companies]

# ---------------------------------------------------------------------------
# News categories we care about
# ---------------------------------------------------------------------------

NEWS_CATEGORIES = [
    "AI moves",       # product launches, AI integrations, agentic features
    "Funding & M&A",  # funding rounds, acquisitions, IPOs, PE activity
    "Earnings",       # revenue results, guidance, stock moves
    "Layoffs & org",  # headcount changes, leadership moves, restructuring
]


def build_prompt(companies: list[str], categories: list[str]) -> str:
    company_list = ", ".join(companies)
    category_list = ", ".join(categories)
    week_ending = datetime.date.today().strftime("%d %B %Y")

    return f"""You are an industry analyst producing a weekly news digest for a senior commercial strategy professional
targeting roles at enterprise SaaS and cybersecurity companies.

Today's date is {week_ending}. Search the web for the most recent news (last 7 days) on the following companies:

{company_list}

Organise your findings into exactly these four sections, in this order:
1. AI Moves — product launches, agentic AI features, model integrations, partnerships with AI vendors
2. Funding & M&A — funding rounds, acquisitions, IPOs, PE buyouts, mergers
3. Earnings — quarterly results, revenue guidance, stock reactions, analyst upgrades/downgrades
4. Layoffs & Org — headcount reductions, leadership changes, restructuring announcements

Rules:
- Only include items where something actually happened in the last 7 days. Do not speculate.
- For each item, format as: **Company Name** — one or two sentences summarising what happened and why it matters.
- If a category has no news this week, write: "No significant news this week."
- At the end, add a short "So what?" paragraph (3–5 sentences) summarising the biggest strategic signal of the week
  for someone evaluating these companies as potential employers. Flag any company that looks particularly strong
  or particularly at risk right now.
- Be direct and analytical. No filler phrases.

Return the digest as plain structured text. Use the exact section headings listed above."""


def fetch_digest(client: anthropic.Anthropic, prompt: str) -> str:
    """Call the Anthropic API with web search enabled."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract all text blocks from the response
    text_parts = [block.text for block in response.content if block.type == "text"]
    return "\n\n".join(text_parts).strip()


def text_to_html(digest_text: str, week_label: str) -> str:
    """Convert the plain-text digest into a clean HTML email."""

    section_colours = {
        "AI Moves": "#185FA5",
        "Funding & M&A": "#0F6E56",
        "Earnings": "#854F0B",
        "Layoffs & Org": "#993556",
        "So what?": "#3C3489",
    }

    lines = digest_text.split("\n")
    body_html = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Section headings
        matched_heading = False
        for heading, colour in section_colours.items():
            if line.lower().startswith(heading.lower()):
                body_html += f"""
                <tr><td style="padding: 24px 0 8px;">
                  <p style="margin:0; font-size:13px; font-weight:600;
                             letter-spacing:0.06em; text-transform:uppercase;
                             color:{colour};">{line}</p>
                  <hr style="border:none; border-top:2px solid {colour};
                              margin:6px 0 0; opacity:0.25;">
                </td></tr>"""
                matched_heading = True
                break

        if matched_heading:
            continue

        # Bold company items (lines starting with **)
        if line.startswith("**"):
            parts = line.split("**")
            if len(parts) >= 3:
                company = parts[1]
                rest = "**".join(parts[2:]).lstrip(" —–-")
                body_html += f"""
                <tr><td style="padding: 6px 0;">
                  <p style="margin:0; font-size:14px; line-height:1.6; color:#1a1a1a;">
                    <span style="font-weight:600;">{company}</span>
                    {f" — {rest}" if rest else ""}
                  </p>
                </td></tr>"""
                continue

        # Numbered headings like "1. AI Moves"
        if len(line) > 2 and line[0].isdigit() and line[1] == ".":
            body_html += f"""
            <tr><td style="padding: 20px 0 4px;">
              <p style="margin:0; font-size:15px; font-weight:600; color:#111;">{line[3:]}</p>
            </td></tr>"""
            continue

        # Regular paragraph text
        body_html += f"""
        <tr><td style="padding: 4px 0;">
          <p style="margin:0; font-size:14px; line-height:1.7; color:#333;">{line}</p>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Industry Digest — {week_label}</title>
</head>
<body style="margin:0; padding:0; background:#f5f5f0; font-family: -apple-system, BlinkMacSystemFont,
             'Segoe UI', Helvetica, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f0; padding: 32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff; border-radius:8px; overflow:hidden;
                    border: 1px solid #e0ddd4;">

        <!-- Header -->
        <tr>
          <td style="background:#111; padding: 28px 32px;">
            <p style="margin:0; font-size:11px; font-weight:600; letter-spacing:0.1em;
                       text-transform:uppercase; color:#888;">Weekly Industry Digest</p>
            <p style="margin:8px 0 0; font-size:22px; font-weight:600; color:#ffffff;">
              {week_label}
            </p>
            <p style="margin:6px 0 0; font-size:13px; color:#aaa;">
              Cybersecurity · Enterprise SaaS · AI Platforms
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding: 24px 32px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              {body_html}
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9f8f5; border-top:1px solid #e0ddd4;
                     padding: 16px 32px;">
            <p style="margin:0; font-size:11px; color:#999; line-height:1.6;">
              Generated automatically using the Anthropic API with live web search.
              &nbsp;·&nbsp; <a href="https://github.com" style="color:#999;">View on GitHub</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(html_content: str, subject: str) -> None:
    """Send the digest via Gmail SMTP."""
    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Industry Digest <{gmail_address}>"
    msg["To"] = recipient

    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, recipient, msg.as_string())

    print(f"Digest sent to {recipient}")


def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    week_label = datetime.date.today().strftime("Week of %-d %B %Y")
    subject = f"Industry Digest — {datetime.date.today().strftime('%-d %b %Y')}"

    print(f"Fetching digest for {week_label}...")
    prompt = build_prompt(ALL_COMPANIES, NEWS_CATEGORIES)
    digest_text = fetch_digest(client, prompt)

    print("Building email...")
    html = text_to_html(digest_text, week_label)

    print("Sending...")
    send_email(html, subject)
    print("Done.")


if __name__ == "__main__":
    main()
