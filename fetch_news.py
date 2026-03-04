import feedparser
import json
from datetime import datetime

feeds = open("feeds.txt").read().splitlines()
articles = []

for url in feeds:
    feed = feedparser.parse(url)
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "source": feed.feed.get("title", "Unknown"),
            "published": entry.get("published", "")
        })

# Sort newest first
articles = sorted(articles, key=lambda x: x["published"], reverse=True)

with open("news.json", "w") as f:
    json.dump(articles[:300], f, indent=2)
