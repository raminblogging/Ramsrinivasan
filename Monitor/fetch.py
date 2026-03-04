import feedparser
import json
import socket
from datetime import datetime, timezone

# Timeout so slow/dead feeds don't hang the whole run
socket.setdefaulttimeout(10)

print("=" * 50)
print(f"World Monitor — Feed Fetch Started")
print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 50)

# Read feeds
feeds = open("feeds.txt", encoding="utf-8").read().splitlines()
articles = []
success = 0
failed = 0
total_feeds = sum(1 for f in feeds if f.strip() and not f.strip().startswith("#"))

print(f"\nFetching {total_feeds} feeds...\n")

for url in feeds:
    url = url.strip()

    # Skip empty lines and comments
    if not url or url.startswith("#"):
        continue

    try:
        feed = feedparser.parse(url)

        # Skip if feed returned nothing useful
        if not feed.entries:
            raise ValueError("No entries found")

        source_name = feed.feed.get("title", url)
        count = 0

        for entry in feed.entries[:30]:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "").strip()

            # Skip entries with no title or link
            if not title or not link:
                continue

            articles.append({
                "title":     title,
                "link":      link,
                "source":    source_name,
                "published": entry.get("published", "")
            })
            count += 1

        success += 1
        print(f"  ✓  [{success:>3}] {source_name[:55]:<55} {count} articles")

    except Exception as e:
        failed += 1
        print(f"  ✗  FAIL  {url[:60]} — {e}")

# Sort newest first
articles = sorted(articles, key=lambda x: x["published"], reverse=True)

# Remove duplicates by link
seen = set()
unique = []
for a in articles:
    if a["link"] not in seen:
        seen.add(a["link"])
        unique.append(a)

# Save top 5000
final = unique[:5000]
with open("news.json", "w", encoding="utf-8") as f:
    json.dump(final, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 50)
print(f"✓ Saved {len(final)} unique articles to news.json")
print(f"  Sources : {success} succeeded / {failed} failed")
print(f"  Finished: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 50)
