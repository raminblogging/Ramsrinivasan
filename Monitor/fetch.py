import feedparser
import json
import socket
from datetime import datetime, timezone

socket.setdefaulttimeout(10)

print("=" * 50)
print(f"World Monitor — Feed Fetch Started")
print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 50)

# ── CATEGORY MAP ──────────────────────────────────────────
# Maps each feed URL keyword to a category label
CATEGORY_MAP = {
    # India News
    "timesofindia":        "India",
    "thehindu":            "India",
    "indianexpress":       "India",
    "hindustantimes":      "India",
    "ndtv":                "India",
    "indiatoday":          "India",
    "news18":              "India",
    "deccanherald":        "India",
    "tribuneindia":        "India",

    # Supply Chain
    "supplychaindive":     "Supply Chain",
    "logisticsmgmt":       "Supply Chain",
    "supplychainbrain":    "Supply Chain",
    "freightwaves":        "Supply Chain",
    "joc.com":             "Supply Chain",
    "dcvelocity":          "Supply Chain",
    "sdcexec":             "Supply Chain",
    "inboundlogistics":    "Supply Chain",
    "globaltrademag":      "Supply Chain",
    "materialhandling247": "Supply Chain",
    "supplychainquarterly":"Supply Chain",
    "scmr.com":            "Supply Chain",
    "transporttopics":     "Supply Chain",
    "lloydsloadinglist":   "Supply Chain",
    "porttechnology":      "Supply Chain",
    "maritime-executive":  "Supply Chain",
    "aircargonews":        "Supply Chain",
    "ajot.com":            "Supply Chain",
    "logisticsmanager":    "Supply Chain",
    "foodlogistics":       "Supply Chain",
    "mmh.com":             "Supply Chain",
    "tradewindsnews":      "Supply Chain",
    "railwayage":          "Supply Chain",
    "bulk-online":         "Supply Chain",
    "automotivelogistics": "Supply Chain",
    "container-news":      "Supply Chain",
    "cips.org":            "Supply Chain",
    "sourcingjournal":     "Supply Chain",
    "projectcargojournal": "Supply Chain",

    # Cricket
    "espncricinfo":        "Cricket",
    "cricbuzz":            "Cricket",
    "icc-cricket":         "Cricket",
    "sportskeeda":         "Cricket",
    "skysports":           "Cricket",
    "54829575":            "Cricket",  # TOI cricket feed ID
    "cricket":             "Cricket",

    # Economy
    "reutersagency":       "Economy",
    "ft.com":              "Economy",
    "worldbank":           "Economy",
    "imf.org":             "Economy",
    "oecd.org":            "Economy",
    "economist.com":       "Economy",
    "marketwatch":         "Economy",
    "moneycontrol":        "Economy",
    "bloomberg":           "Economy",
    "business-standard":   "Economy",
    "livemint":            "Economy",
    "forbes.com/economy":  "Economy",

    # Tech
    "techcrunch":          "Tech",
    "theverge":            "Tech",
    "wired.com":           "Tech",
    "arstechnica":         "Tech",
    "thenextweb":          "Tech",
    "zdnet":               "Tech",
    "engadget":            "Tech",
    "techradar":           "Tech",
    "gizmodo":             "Tech",
    "macrumors":           "Tech",
    "androidauthority":    "Tech",
    "windowscentral":      "Tech",
    "digitaltrends":       "Tech",
    "slashgear":           "Tech",
    "tomshardware":        "Tech",

    # Business
    "cnbc.com":            "Business",
    "forbes.com/business": "Business",
    "businessinsider":     "Business",
    "fortune.com":         "Business",
    "inc.com":             "Business",
    "entrepreneur":        "Business",
    "wsj.com":             "Business",
    "nytimes.com":         "Business",
    "bbc.co.uk/news/business": "Business",
    "moneycontrol.com/rss/markets": "Business",
    "13352306":            "Business",  # ET markets feed ID
    "hindustantimes.com/feeds/rss/business": "Business",
    "indianexpress.com/section/business": "Business",

    # AI
    "venturebeat.com/category/ai": "AI",
    "technologyreview":    "AI",
    "ai.googleblog":       "AI",
    "openai.com":          "AI",
    "blogs.microsoft.com/ai": "AI",
    "aws.amazon.com/blogs/machine-learning": "AI",
    "deepmind":            "AI",
    "towardsdatascience":  "AI",
    "unite.ai":            "AI",
    "analyticsindiamag":   "AI",
    "marktechpost":        "AI",
    "artificialintelligence-news": "AI",
    "kdnuggets":           "AI",
    "machinelearningmastery": "AI",
    "sciencedaily.com/rss/computers_math/artificial_intelligence": "AI",

    # Trending
    "news.google.com":     "Trending",
    "reddit.com":          "Trending",
    "aljazeera":           "Trending",
    "bbci.co.uk/news/rss": "Trending",
    "theguardian.com/world": "Trending",
}

def get_category(url):
    url_lower = url.lower()
    # Try longest/most specific match first
    for key in sorted(CATEGORY_MAP.keys(), key=len, reverse=True):
        if key in url_lower:
            return CATEGORY_MAP[key]
    return "Other"

# Read feeds
feeds = open("feeds.txt", encoding="utf-8").read().splitlines()
articles = []
success = 0
failed = 0
total_feeds = sum(1 for f in feeds if f.strip() and not f.strip().startswith("#"))

print(f"\nFetching {total_feeds} feeds...\n")

for url in feeds:
    url = url.strip()
    if not url or url.startswith("#"):
        continue

    category = get_category(url)

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
