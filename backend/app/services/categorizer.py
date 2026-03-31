
from __future__ import annotations

# Simple rule-based categorization (can be extended in Settings)
DEFAULT_RULES = {
    "productive": [
        "docs.google.com", "github.com", "gitlab.com", "stackoverflow.com", "jira", 
        "confluence", "notion.so", "linkedin.com", "canva.com", "trello.com", 
        "asana.com", "bitbucket.org", "chatgpt.com", "openai.com", "claude.ai", 
        "perplexity.ai", "microsoft.com", "office.com", "google.com/search"
    ],
    "communication": [
        "slack.com", "teams.microsoft.com", "mail.google.com", "outlook.office.com", 
        "discord.com", "whatsapp.com", "web.whatsapp.com", "telegram.org", 
        "zoom.us", "meet.google.com"
    ],
    "social": [
        "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com", 
        "reddit.com", "pinterest.com", "snapchat.com", "threads.net", "messenger.com"
    ],
    "streaming": [
        "youtube.com", "netflix.com", "primevideo.com", "spotify.com", 
        "disneyplus.com", "hulu.com", "hbomax.com", "twitch.tv", "music.apple.com"
    ],
    "shopping": [
        "amazon.", "daraz.", "ebay.", "aliexpress.com", "walmart.com", 
        "target.com", "etsy.com", "bestbuy.com", "shopee.", "lazada."
    ],
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
