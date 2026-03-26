
from __future__ import annotations

# Simple rule-based categorization (can be extended in Settings)
DEFAULT_RULES = {
    "productive": ["docs.google.com", "github.com", "gitlab.com", "stackoverflow.com", "jira", "confluence", "notion.so"],
    "communication": ["slack.com", "teams.microsoft.com", "mail.google.com", "outlook.office.com"],
    "social": ["facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com", "reddit.com"],
    "streaming": ["youtube.com", "netflix.com", "primevideo.com", "spotify.com"],
    "shopping": ["amazon.", "daraz", "ebay.", "aliexpress"],
    "adult": [],
    "other": [],
}

def categorize_domain(domain: str, rules: dict | None = None) -> str:
    rules = rules or DEFAULT_RULES
    d = (domain or "").lower()
    for cat, needles in rules.items():
        for n in needles:
            if n.lower() in d:
                return cat
    return "other"
