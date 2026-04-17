"""
Domain Categorization Service
-----------------------------
This module provides logic for classifying web domains into categories
(e.g., Productivity, Social Media, Streaming) based on predefined rules.
"""

from __future__ import annotations

# Simple rule-based categorization.
# These rules map partial domain matches (needles) to a category name.
# This can be extended via the system settings in a production environment.
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
    """
    Classify a domain string into a category based on keyword matching.
    
    The function checks if any of the keywords defined in 'rules' are present
    within the 'domain' string. If no match is found, it defaults to 'other'.
    
    :param domain: The domain name to categorize (e.g., 'github.com').
    :param rules: An optional dictionary of rules. Defaults to DEFAULT_RULES.
    :return: The category name as a string.
    """
    rules = rules or DEFAULT_RULES
    d = (domain or "").lower()
    for cat, needles in rules.items():
        for n in needles:
            # Check for substring match to handle subdomains and variations.
            if n.lower() in d:
                return cat
    return "other"
