# Industry Weekly Digest

An automated weekly email digest that tracks AI disruption, funding activity, earnings,
and org changes across target companies in enterprise cybersecurity, SaaS, and AI platforms.

Runs every Monday morning via GitHub Actions. Powered by the Anthropic API with live web search.

---

## What it does

- Searches the web for the past 7 days of news on 35+ target companies
- Organises findings into four sections: **AI Moves**, **Funding & M&A**, **Earnings**, **Layoffs & Org**
- Adds a strategic "So what?" summary at the end
- Sends a clean HTML email to your inbox every Monday at 08:00 Paris time

---

## Setup (one-time, ~10 minutes)

### 1. Fork or clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/industry-digest.git
cd industry-digest
```

### 2. Get an Anthropic API key

1. Go to [platform.anthropic.com](https://platform.anthropic.com)
2. Create an account and navigate to **API Keys**
3. Create a new key and copy it

### 3. Create a Gmail App Password

Gmail requires an App Password for SMTP access (not your regular Gmail password).

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** if not already on
3. Search for **App Passwords** in the security settings
4. Create a new app password — name it "Industry Digest"
5. Copy the 16-character password shown

### 4. Add GitHub Secrets

In your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**.

Add these four secrets:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | The 16-character App Password from step 3 |
| `RECIPIENT_EMAIL` | Where to send the digest (can be the same Gmail) |

### 5. Test it manually

Go to **Actions → Weekly Industry Digest → Run workflow** to trigger it immediately
and confirm the email arrives before the first scheduled Monday run.

---

## Customising the company list

Edit the `COMPANIES` dictionary in `src/digest.py`. Companies are grouped by tier
but all are included in a single weekly search. Add or remove as your target list evolves.

```python
COMPANIES = {
    "Tier 1 — Cybersecurity": [
        "Palo Alto Networks", "CrowdStrike", ...
    ],
    ...
}
```

---

## Cost

Each weekly run makes one Anthropic API call with web search enabled.
Typical cost: **$0.10–0.30 per run** depending on how much news there is.

GitHub Actions is free for public repos and includes 2,000 minutes/month for private repos
(this workflow uses roughly 2 minutes per run).

---

## Project structure

```
industry-digest/
├── .github/
│   └── workflows/
│       └── weekly_digest.yml   # GitHub Actions schedule + job definition
├── src/
│   └── digest.py               # Main script: fetch → format → send
├── requirements.txt
└── README.md
```

---

## Tech stack

- **Python 3.11** — standard library only, plus the Anthropic SDK
- **Anthropic API** — claude-sonnet with web_search tool for live news
- **GitHub Actions** — free CI/CD for the weekly cron schedule
- **Gmail SMTP** — sends the HTML email via SSL

---

*Built to stay informed on AI disruption trends across enterprise software and cybersecurity.*
