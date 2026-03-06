import feedparser
import json
import socket
from datetime import datetime, timezone

socket.setdefaulttimeout(10)

print("=" * 50)
print(f"World Monitor — Feed Fetch Started")
print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 50)

# Read feeds and assign category from section comment headers
# e.g. "# ── SUPPLY CHAIN ──" sets category = "Supply Chain" for all feeds below it
feeds_raw = open("feeds.txt", encoding="utf-8").read().splitlines()

# Map comment headers to clean category names
HEADER_MAP = {
    "INDIA":        "India",
    "SUPPLY CHAIN": "Supply Chain",
    "CRICKET":      "Cricket",
    "ECONOMY":      "Economy",
    "TECH":         "Tech",
    "BUSINESS":     "Business",
    "AI":           "AI",
    "TRENDING":     "Trending",
}

def header_to_category(line):
    """Extract category name from a comment line like # ── SUPPLY CHAIN ──"""
    clean = line.strip("#─ \t").strip().upper()
    for key, label in HEADER_MAP.items():
        if key in clean:
            return label
    return None

# Build list of (url, category) pairs
feed_list = []
current_category = "Other"

for line in feeds_raw:
    line = line.strip()
    if not line:
        continue
    if line.startswith("#"):
        cat = header_to_category(line)
        if cat:
            current_category = cat
        continue
    feed_list.append((line, current_category))

total_feeds = len(feed_list)
print(f"\nFetching {total_feeds} feeds...\n")

articles = []
success = 0
failed = 0

for url, category in feed_list:
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            raise ValueError("No entries found")

        source_name = feed.feed.get("title", url)
        count = 0

        for entry in feed.entries[:30]:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "").strip()
            if not title or not link:
                continue
            articles.append({
                "title":     title,
                "link":      link,
                "source":    source_name,
                "category":  category,
                "published": entry.get("published", "")
            })
            count += 1

        success += 1
        print(f"  ✓  [{success:>3}] [{category:<12}] {source_name[:45]:<45} {count} articles")

    except Exception as e:
        failed += 1
        print(f"  ✗  FAIL  [{category:<12}] {url[:55]} — {e}")

# Sort newest first
articles = sorted(articles, key=lambda x: x["published"], reverse=True)

# Remove duplicates by link
seen = set()
unique = []
for a in articles:
    if a["link"] not in seen:
        seen.add(a["link"])
        unique.append(a)

final = unique[:5000]
with open("news.json", "w", encoding="utf-8") as f:
    json.dump(final, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 50)
print(f"✓ Saved {len(final)} unique articles to news.json")
print(f"  Sources : {success} succeeded / {failed} failed")
print(f"  Finished: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 50)
