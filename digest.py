import os
import json
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic

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

ALL_COMPANIES = [c for companies in COMPANIES.values() for c in companies]

NEWS_CATEGORIES = [
    "AI moves",
    "Funding & M&A",
    "Earnings",
    "Layoffs & org",
]


def build_prompt(companies, categories):
    company_list = ", ".join(companies)
    week_ending = datetime.date.today().strftime("%d %B %Y")
    return f"""You are an industry analyst producing a weekly news digest for a senior commercial strategy professional targeting roles at enterprise SaaS and cybersecurity companies.

Today's date is {week_ending}. Search the web for the most recent news (last 7 days) on the following companies:

{company_list}

Organise your findings into exactly these four sections:
1. AI Moves
2. Funding & M&A
3. Earnings
4. Layoffs & Org

For each item: **Company Name** — one or two sentences on what happened and why it matters.
If a category has no news this week, write: No significant news this week.
End with a short So what? paragraph summarising the biggest strategic signal of the week.

Return as plain structured text using the exact section headings above."""


def fetch_digest(client, prompt):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    text_parts = [block.text for block in response.content if block.type == "text"]
    return "\n\n".join(text_parts).strip()


def text_to_html(digest_text, week_label):
    lines = digest_text.split("\n")
    body_html = ""
    section_colours = {
        "AI Moves": "#185FA5",
        "Funding & M&A": "#0F6E56",
        "Earnings": "#854F0B",
        "Layoffs & Org": "#993556",
        "So what?": "#3C3489",
    }
    for line in lines:
        line = line.strip()
        if not line:
            continue
        matched = False
        for heading, colour in section_colours.items():
            if line.lower().startswith(heading.lower()):
                body_html += f'<tr><td style="padding:24px 0 8px;"><p style="margin:0;font-size:13px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:{colour};">{line}</p><hr style="border:none;border-top:2px solid {colour};margin:6px 0 0;opacity:0.25;"></td></tr>'
                matched = True
                break
        if matched:
            continue
        if line.startswith("**"):
            parts = line.split("**")
            if len(parts) >= 3:
                company = parts[1]
                rest = "**".join(parts[2:]).lstrip(" —–-")
                body_html += f'<tr><td style="padding:6px 0;"><p style="margin:0;font-size:14px;line-height:1.6;color:#1a1a1a;"><span style="font-weight:600;">{company}</span>{f" — {rest}" if rest else ""}</p></td></tr>'
                continue
        if len(line) > 2 and line[0].isdigit() and line[1] == ".":
            body_html += f'<tr><td style="padding:20px 0 4px;"><p style="margin:0;font-size:15px;font-weight:600;color:#111;">{line[3:]}</p></td></tr>'
            continue
        body_html += f'<tr><td style="padding:4px 0;"><p style="margin:0;font-size:14px;line-height:1.7;color:#333;">{line}</p></td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Industry Digest — {week_label}</title></head>
<body style="margin:0;padding:0;background:#f5f5f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f0;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;border:1px solid #e0ddd4;">
<tr><td style="background:#111;padding:28px 32px;">
<p style="margin:0;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#888;">Weekly Industry Digest</p>
<p style="margin:8px 0 0;font-size:22px;font-weight:600;color:#ffffff;">{week_label}</p>
<p style="margin:6px 0 0;font-size:13px;color:#aaa;">Cybersecurity · Enterprise SaaS · AI Platforms</p>
</td></tr>
<tr><td style="padding:24px 32px 32px;">
<table width="100%" cellpadding="0" cellspacing="0">{body_html}</table>
</td></tr>
<tr><td style="background:#f9f8f5;border-top:1px solid #e0ddd4;padding:16px 32px;">
<p style="margin:0;font-size:11px;color:#999;">Generated automatically using the Anthropic API with live web search.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def send_email(html_content, subject):
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
