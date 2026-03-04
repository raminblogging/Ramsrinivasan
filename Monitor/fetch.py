import feedparser
import json
import socket

# Set global timeout so slow feeds don't hang
socket.setdefaulttimeout(10)

feeds = open("feeds.txt").read().splitlines()
articles = []
success = 0
failed = 0

for url in feeds:
    url = url.strip()
    if not url or url.startswith("#"):
        continue
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            raise ValueError("Bad feed")
        source_name = feed.feed.get("title", url)
        for entry in feed.entries[:30]:  # 30 per source keeps file size manageable
            articles.append({
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "source": source_name,
                "published": entry.get("published", "")
            })
        success += 1
        print(f"✓ {source_name} — {len(feed.entries[:30])} articles")
    except Exception as e:
        failed += 1
        print(f"✗ Failed: {url} — {e}")

# Sort newest first
articles = sorted(articles, key=lambda x: x["published"], reverse=True)

# Save up to 3000 total
with open("news.json", "w", encoding="utf-8") as f:
    json.dump(articles[:3000], f, indent=2, ensure_ascii=False)

print(f"\n✓ Done — {len(articles[:3000])} articles saved")
print(f"  Sources: {success} succeeded, {failed} failed")
