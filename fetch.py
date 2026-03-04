import feedparser
import json
from datetime import datetime

feeds = open("feeds.txt").read().splitlines()
articles = []

for url in feeds:
    if not url.strip() or url.strip().startswith("#"):
        continue
    try:
        feed = feedparser.parse(url.strip())
        for entry in feed.entries[:10]:
            articles.append({
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "source": feed.feed.get("title", "Unknown"),
                "published": entry.get("published", "")
            })
    except Exception as e:
        print(f"Error fetching {url}: {e}")

# Sort newest first
articles = sorted(articles, key=lambda x: x["published"], reverse=True)

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(articles[:300], f, indent=2, ensure_ascii=False)

print(f"✓ Done — {len(articles[:300])} articles saved to news.json")
