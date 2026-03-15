#!/usr/bin/env python3
"""
fetch.py — World Monitor feed generator
Run this script to refresh feed.json.

Usage:
  python3 fetch.py

Schedule via cron (every 30 min):
  */30 * * * * cd /path/to/Monitor && python3 fetch.py

Requires:
  pip install feedparser requests
"""

import feedparser
import requests
import json
import time
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "feed.json")
MAX_WORKERS  = 20     # parallel fetches
PER_FEED     = 15     # max articles per feed
TIMEOUT      = 10     # seconds per request

SOURCES = [
    # ── INDIA ──────────────────────────────────────────────────────
    {"url": "https://feeds.feedburner.com/ndtvnews-top-stories",                    "category": "India",       "source": "NDTV"},
    {"url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",           "category": "India",       "source": "Times of India"},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss",            "category": "India",       "source": "The Hindu"},
    {"url": "https://indianexpress.com/feed/",                                       "category": "India",       "source": "Indian Express"},
    {"url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",      "category": "India",       "source": "Hindustan Times"},
    {"url": "https://www.livemint.com/rss/news",                                    "category": "India",       "source": "Mint"},
    {"url": "https://scroll.in/feed",                                               "category": "India",       "source": "Scroll.in"},
    {"url": "https://thewire.in/feed",                                              "category": "India",       "source": "The Wire"},
    {"url": "https://www.deccanherald.com/rss-feeds/national.rss",                  "category": "India",       "source": "Deccan Herald"},
    {"url": "https://www.firstpost.com/rss/india.xml",                              "category": "India",       "source": "Firstpost"},
    {"url": "https://www.moneycontrol.com/rss/economy.xml",                         "category": "India",       "source": "Moneycontrol"},
    {"url": "https://www.theweek.in/news/india.rss",                                "category": "India",       "source": "The Week"},
    {"url": "https://www.business-standard.com/rss/home_page_top_stories.rss",      "category": "India",       "source": "Business Standard"},
    {"url": "https://www.outlookindia.com/rss/main/magazine",                       "category": "India",       "source": "Outlook India"},
    {"url": "https://www.news18.com/rss/india.xml",                                 "category": "India",       "source": "News18"},
    {"url": "https://zeenews.india.com/rss/india-national-news.xml",                "category": "India",       "source": "Zee News"},
    {"url": "https://www.thehindubusinessline.com/economy/?service=rss",            "category": "India",       "source": "Hindu BusinessLine"},
    {"url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",          "category": "India",       "source": "Economic Times"},
    {"url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "category": "India",       "source": "ET Markets"},
    {"url": "https://www.ndtv.com/rss/feeds",                                       "category": "India",       "source": "NDTV All"},
    {"url": "https://www.tribuneindia.com/rss/feed.xml",                            "category": "India",       "source": "Tribune India"},
    # ── TECH ───────────────────────────────────────────────────────
    {"url": "https://feeds.feedburner.com/TechCrunch",                              "category": "Tech",        "source": "TechCrunch"},
    {"url": "https://www.wired.com/feed/rss",                                       "category": "Tech",        "source": "Wired"},
    {"url": "https://www.theverge.com/rss/index.xml",                               "category": "Tech",        "source": "The Verge"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index",                      "category": "Tech",        "source": "Ars Technica"},
    {"url": "https://www.zdnet.com/news/rss.xml",                                   "category": "Tech",        "source": "ZDNet"},
    {"url": "https://www.engadget.com/rss.xml",                                     "category": "Tech",        "source": "Engadget"},
    {"url": "https://www.cnet.com/rss/news/",                                       "category": "Tech",        "source": "CNET"},
    {"url": "https://techrepublic.com/rssfeeds/articles/",                          "category": "Tech",        "source": "TechRepublic"},
    {"url": "https://9to5mac.com/feed/",                                            "category": "Tech",        "source": "9to5Mac"},
    {"url": "https://9to5google.com/feed/",                                         "category": "Tech",        "source": "9to5Google"},
    {"url": "https://www.macrumors.com/macrumors.xml",                              "category": "Tech",        "source": "MacRumors"},
    {"url": "https://thenextweb.com/feed/",                                         "category": "Tech",        "source": "TNW"},
    {"url": "https://www.theregister.com/headlines.atom",                           "category": "Tech",        "source": "The Register"},
    {"url": "https://spectrum.ieee.org/feeds/feed.rss",                             "category": "Tech",        "source": "IEEE Spectrum"},
    {"url": "https://hackaday.com/blog/feed/",                                      "category": "Tech",        "source": "Hackaday"},
    {"url": "https://www.techradar.com/rss",                                        "category": "Tech",        "source": "TechRadar"},
    {"url": "https://www.digitaltrends.com/feed/",                                  "category": "Tech",        "source": "Digital Trends"},
    {"url": "https://www.androidauthority.com/feed/",                               "category": "Tech",        "source": "Android Authority"},
    {"url": "https://www.gsmarena.com/rss-news-articles.php3",                      "category": "Tech",        "source": "GSMArena"},
    {"url": "https://gizmodo.com/rss",                                              "category": "Tech",        "source": "Gizmodo"},
    {"url": "https://www.bleepingcomputer.com/feed/",                               "category": "Tech",        "source": "BleepingComputer"},
    {"url": "https://krebsonsecurity.com/feed/",                                    "category": "Tech",        "source": "Krebs Security"},
    {"url": "https://www.darkreading.com/rss.xml",                                  "category": "Tech",        "source": "Dark Reading"},
    # ── AI ─────────────────────────────────────────────────────────
    {"url": "https://venturebeat.com/category/ai/feed/",                            "category": "AI",          "source": "VentureBeat AI"},
    {"url": "https://www.artificialintelligence-news.com/feed/",                    "category": "AI",          "source": "AI News"},
    {"url": "https://openai.com/blog/rss.xml",                                      "category": "AI",          "source": "OpenAI"},
    {"url": "https://www.marktechpost.com/feed/",                                   "category": "AI",          "source": "MarkTechPost"},
    {"url": "https://www.unite.ai/feed/",                                           "category": "AI",          "source": "Unite.AI"},
    {"url": "https://www.technologyreview.com/feed/",                               "category": "AI",          "source": "MIT Tech Review"},
    {"url": "https://huggingface.co/blog/feed.xml",                                 "category": "AI",          "source": "HuggingFace"},
    {"url": "https://www.deeplearning.ai/the-batch/feed/",                          "category": "AI",          "source": "The Batch"},
    {"url": "https://towardsdatascience.com/feed",                                  "category": "AI",          "source": "Towards Data Science"},
    {"url": "https://blogs.nvidia.com/feed/",                                       "category": "AI",          "source": "NVIDIA Blog"},
    {"url": "https://ai.googleblog.com/feeds/posts/default",                        "category": "AI",          "source": "Google AI"},
    {"url": "https://www.deepmind.com/blog/rss.xml",                                "category": "AI",          "source": "DeepMind"},
    {"url": "https://paperswithcode.com/latest.rss",                                "category": "AI",          "source": "Papers With Code"},
    # ── ECONOMY ────────────────────────────────────────────────────
    {"url": "https://feeds.bloomberg.com/markets/news.rss",                         "category": "Economy",     "source": "Bloomberg"},
    {"url": "https://feeds.reuters.com/reuters/businessNews",                        "category": "Economy",     "source": "Reuters Business"},
    {"url": "https://www.wsj.com/xml/rss/3_7014.xml",                              "category": "Economy",     "source": "WSJ Economy"},
    {"url": "https://www.economist.com/finance-and-economics/rss.xml",              "category": "Economy",     "source": "The Economist"},
    {"url": "https://www.project-syndicate.org/rss",                                "category": "Economy",     "source": "Project Syndicate"},
    {"url": "https://voxeu.org/feed.xml",                                           "category": "Economy",     "source": "VoxEU"},
    {"url": "https://www.imf.org/en/News/rss",                                      "category": "Economy",     "source": "IMF"},
    {"url": "https://www.worldbank.org/en/news/rss",                                "category": "Economy",     "source": "World Bank"},
    {"url": "https://www.livemint.com/rss/economy",                                 "category": "Economy",     "source": "Mint Economy"},
    # ── BUSINESS ───────────────────────────────────────────────────
    {"url": "https://www.businessinsider.com/rss",                                  "category": "Business",    "source": "Business Insider"},
    {"url": "https://fortune.com/feed/",                                            "category": "Business",    "source": "Fortune"},
    {"url": "https://hbr.org/feed/",                                                "category": "Business",    "source": "Harvard Business Review"},
    {"url": "https://feeds.inc.com/home/updates",                                   "category": "Business",    "source": "Inc."},
    {"url": "https://www.fastcompany.com/latest/rss",                               "category": "Business",    "source": "Fast Company"},
    {"url": "https://www.forbes.com/innovation/feed2",                              "category": "Business",    "source": "Forbes"},
    {"url": "https://www.entrepreneur.com/latest/rss",                              "category": "Business",    "source": "Entrepreneur"},
    {"url": "https://www.businesswire.com/rss/home/?rss=G1",                        "category": "Business",    "source": "Business Wire"},
    # ── SUPPLY CHAIN ───────────────────────────────────────────────
    {"url": "https://www.supplychaindive.com/feeds/news/",                          "category": "SC",          "source": "SC Dive"},
    {"url": "https://www.logisticsmgmt.com/rss/news",                               "category": "SC",          "source": "Logistics Mgmt"},
    {"url": "https://www.supplychainbrain.com/rss/articles.xml",                    "category": "SC",          "source": "SCBrain"},
    {"url": "https://theloadstar.com/feed/",                                        "category": "SC",          "source": "The Loadstar"},
    {"url": "https://www.freightwaves.com/news/feed",                               "category": "SC",          "source": "FreightWaves"},
    {"url": "https://www.inboundlogistics.com/rss/",                                "category": "SC",          "source": "Inbound Logistics"},
    {"url": "https://mhlnews.com/rss/all",                                          "category": "SC",          "source": "MHLNews"},
    {"url": "https://www.dcvelocity.com/rss",                                       "category": "SC",          "source": "DC Velocity"},
    {"url": "https://www.globaltrademag.com/feed/",                                 "category": "SC",          "source": "Global Trade"},
    {"url": "https://gcaptain.com/feed/",                                           "category": "SC",          "source": "gCaptain"},
    {"url": "https://splash247.com/feed/",                                          "category": "SC",          "source": "Splash 247"},
    {"url": "https://www.hellenicshippingnews.com/feed/",                           "category": "SC",          "source": "Hellenic Shipping"},
    # ── CRICKET ────────────────────────────────────────────────────
    {"url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",           "category": "Cricket",     "source": "Cricinfo"},
    {"url": "https://sports.ndtv.com/feeds/cricket-news",                           "category": "Cricket",     "source": "NDTV Cricket"},
    {"url": "https://www.cricbuzz.com/rss/google-news.xml",                         "category": "Cricket",     "source": "Cricbuzz"},
    {"url": "https://www.icc-cricket.com/media-releases/rss",                       "category": "Cricket",     "source": "ICC"},
    {"url": "https://www.wisden.com/feed",                                          "category": "Cricket",     "source": "Wisden"},
    {"url": "https://www.cricketaddictor.com/feed/",                                "category": "Cricket",     "source": "Cricket Addictor"},
    # ── SPORTS ─────────────────────────────────────────────────────
    {"url": "https://www.espn.com/espn/rss/news",                                   "category": "Sports",      "source": "ESPN"},
    {"url": "https://sports.yahoo.com/rss/",                                        "category": "Sports",      "source": "Yahoo Sports"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",              "category": "Sports",      "source": "NYT Sports"},
    {"url": "https://www.bbc.co.uk/sport/rss/sport",                                "category": "Sports",      "source": "BBC Sport"},
    {"url": "https://feeds.skysports.com/news/football/rss.xml",                    "category": "Sports",      "source": "Sky Sports"},
    {"url": "https://www.sportskeeda.com/feed",                                     "category": "Sports",      "source": "Sportskeeda"},
    # ── WORLD ──────────────────────────────────────────────────────
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",                          "category": "World",       "source": "BBC World"},
    {"url": "https://feeds.reuters.com/Reuters/worldNews",                           "category": "World",       "source": "Reuters World"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",               "category": "World",       "source": "NYT World"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml",                            "category": "World",       "source": "Al Jazeera"},
    {"url": "https://www.dw.com/rss/rss.xml",                                       "category": "World",       "source": "DW"},
    {"url": "https://feeds.washingtonpost.com/rss/world",                           "category": "World",       "source": "Washington Post"},
    {"url": "https://www.theguardian.com/world/rss",                                "category": "World",       "source": "The Guardian"},
    {"url": "https://www.apnews.com/apf-topnews?format=feed&type=rss",              "category": "World",       "source": "AP News"},
    {"url": "https://www.france24.com/en/rss",                                      "category": "World",       "source": "France 24"},
    {"url": "https://www.scmp.com/rss/91/feed",                                     "category": "World",       "source": "SCMP"},
    {"url": "https://www.euronews.com/rss?level=theme&name=news",                   "category": "World",       "source": "Euronews"},
    {"url": "https://feeds.npr.org/1001/rss.xml",                                   "category": "World",       "source": "NPR News"},
    {"url": "https://foreignpolicy.com/feed/",                                      "category": "World",       "source": "Foreign Policy"},
    # ── GEOPOLITICS ────────────────────────────────────────────────
    {"url": "https://www.cfr.org/rss.xml",                                          "category": "Geopolitics", "source": "CFR"},
    {"url": "https://www.chathamhouse.org/rss.xml",                                 "category": "Geopolitics", "source": "Chatham House"},
    {"url": "https://warontherocks.com/feed/",                                      "category": "Geopolitics", "source": "War on the Rocks"},
    {"url": "https://thediplomat.com/feed/",                                        "category": "Geopolitics", "source": "The Diplomat"},
    {"url": "https://www.bellingcat.com/feed/",                                     "category": "Geopolitics", "source": "Bellingcat"},
    {"url": "https://www.crisisgroup.org/feed",                                     "category": "Geopolitics", "source": "Crisis Group"},
    {"url": "https://www.defensenews.com/rss/",                                     "category": "Geopolitics", "source": "Defense News"},
    {"url": "https://nationalinterest.org/rss.xml",                                 "category": "Geopolitics", "source": "National Interest"},
    {"url": "https://www.rand.org/pubs/rss.xml",                                    "category": "Geopolitics", "source": "RAND"},
    # ── SCIENCE ────────────────────────────────────────────────────
    {"url": "https://www.nature.com/news.rss",                                      "category": "Science",     "source": "Nature"},
    {"url": "https://phys.org/rss-feed/",                                           "category": "Science",     "source": "Phys.org"},
    {"url": "https://www.sciencedaily.com/rss/all.xml",                             "category": "Science",     "source": "ScienceDaily"},
    {"url": "https://www.newscientist.com/feed/home/",                              "category": "Science",     "source": "New Scientist"},
    {"url": "https://www.scientificamerican.com/feed/",                             "category": "Science",     "source": "Scientific American"},
    {"url": "https://earthsky.org/feed/",                                           "category": "Science",     "source": "EarthSky"},
    {"url": "https://www.nasa.gov/news-release/feed/",                              "category": "Science",     "source": "NASA"},
    {"url": "https://www.quantamagazine.org/feed/",                                 "category": "Science",     "source": "Quanta Magazine"},
    {"url": "https://www.livescience.com/feeds/all",                                "category": "Science",     "source": "LiveScience"},
    {"url": "https://www.space.com/feeds/all",                                      "category": "Science",     "source": "Space.com"},
    # ── HEALTH ─────────────────────────────────────────────────────
    {"url": "https://www.who.int/feeds/entity/news/en/rss.xml",                     "category": "Health",      "source": "WHO"},
    {"url": "https://www.nih.gov/news-events/news-releases/feed",                   "category": "Health",      "source": "NIH"},
    {"url": "https://www.medicalnewstoday.com/rss/newsarticles.xml",                "category": "Health",      "source": "Medical News Today"},
    {"url": "https://health.harvard.edu/feed",                                      "category": "Health",      "source": "Harvard Health"},
    {"url": "https://www.statnews.com/feed/",                                       "category": "Health",      "source": "STAT News"},
    {"url": "https://www.medscape.com/features/index/rss",                          "category": "Health",      "source": "Medscape"},
    {"url": "https://www.healthline.com/rss/news",                                  "category": "Health",      "source": "Healthline"},
    {"url": "https://kffhealthnews.org/feed/",                                      "category": "Health",      "source": "KFF Health News"},
    # ── ENVIRONMENT ────────────────────────────────────────────────
    {"url": "https://www.theguardian.com/environment/rss",                          "category": "Environment", "source": "Guardian Env"},
    {"url": "https://www.climatechangenews.com/feed/",                              "category": "Environment", "source": "Climate Change News"},
    {"url": "https://insideclimatenews.org/feed/",                                  "category": "Environment", "source": "Inside Climate"},
    {"url": "https://grist.org/feed/",                                              "category": "Environment", "source": "Grist"},
    {"url": "https://carbonbrief.org/feed/",                                        "category": "Environment", "source": "Carbon Brief"},
    {"url": "https://electrek.co/feed/",                                            "category": "Environment", "source": "Electrek"},
    {"url": "https://www.cleantechnica.com/feed/",                                  "category": "Environment", "source": "CleanTechnica"},
    {"url": "https://e360.yale.edu/feed.xml",                                       "category": "Environment", "source": "Yale e360"},
    # ── STARTUPS ───────────────────────────────────────────────────
    {"url": "https://techcrunch.com/category/startups/feed/",                       "category": "Startups",    "source": "TC Startups"},
    {"url": "https://news.ycombinator.com/rss",                                     "category": "Startups",    "source": "Hacker News"},
    {"url": "https://yourstory.com/feed",                                           "category": "Startups",    "source": "YourStory"},
    {"url": "https://inc42.com/feed/",                                              "category": "Startups",    "source": "Inc42"},
    {"url": "https://sifted.eu/feed/",                                              "category": "Startups",    "source": "Sifted"},
    {"url": "https://techfundingnews.com/feed/",                                    "category": "Startups",    "source": "Tech Funding News"},
    {"url": "https://www.indiehackers.com/feed.rss",                                "category": "Startups",    "source": "Indie Hackers"},
    # ── FINANCE ────────────────────────────────────────────────────
    {"url": "https://www.marketwatch.com/rss/topstories",                           "category": "Finance",     "source": "MarketWatch"},
    {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/",                      "category": "Finance",     "source": "CoinDesk"},
    {"url": "https://cointelegraph.com/rss",                                        "category": "Finance",     "source": "CoinTelegraph"},
    {"url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",                     "category": "Finance",     "source": "WSJ Business"},
    {"url": "https://www.livemint.com/rss/markets",                                 "category": "Finance",     "source": "Mint Markets"},
    {"url": "https://seekingalpha.com/market_currents.xml",                         "category": "Finance",     "source": "Seeking Alpha"},
    # ── POLITICS ───────────────────────────────────────────────────
    {"url": "https://feeds.feedburner.com/politico/politics",                       "category": "Politics",    "source": "Politico"},
    {"url": "https://thehill.com/feed/",                                            "category": "Politics",    "source": "The Hill"},
    {"url": "https://www.vox.com/rss/index.xml",                                    "category": "Politics",    "source": "Vox"},
    {"url": "https://www.hindustantimes.com/feeds/rss/politics/rssfeed.xml",        "category": "Politics",    "source": "HT Politics"},
    {"url": "https://zeenews.india.com/rss/politics.xml",                           "category": "Politics",    "source": "Zee Politics"},
    # ── CULTURE ────────────────────────────────────────────────────
    {"url": "https://variety.com/feed/",                                            "category": "Culture",     "source": "Variety"},
    {"url": "https://deadline.com/feed/",                                           "category": "Culture",     "source": "Deadline"},
    {"url": "https://www.hollywoodreporter.com/feed/",                              "category": "Culture",     "source": "Hollywood Reporter"},
    {"url": "https://www.rollingstone.com/feed/",                                   "category": "Culture",     "source": "Rolling Stone"},
]


def fetch_feed(source):
    """Fetch and parse a single RSS feed. Returns list of article dicts."""
    url      = source["url"]
    category = source["category"]
    src_name = source["source"]
    articles = []

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; WorldMonitor/1.0)"}
        resp = requests.get(url, timeout=TIMEOUT, headers=headers)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        for entry in feed.entries[:PER_FEED]:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "").strip()
            if not title or not link:
                continue

            # Parse date
            date_str = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                date_str = dt.isoformat()
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                date_str = dt.isoformat()

            articles.append({
                "title":    title,
                "url":      link,
                "date":     date_str,
                "source":   src_name,
                "category": category,
            })

    except Exception as e:
        print(f"  ✗ {src_name}: {e}")

    return articles


def main():
    print(f"\n🌐 World Monitor — fetching {len(SOURCES)} RSS sources...")
    start = time.time()

    all_articles = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_feed, src): src for src in SOURCES}
        done = 0
        for future in as_completed(futures):
            articles = future.result()
            all_articles.extend(articles)
            done += 1
            src = futures[future]
            if articles:
                print(f"  ✓ {src['source']:30s} {len(articles):3d} articles  ({done}/{len(SOURCES)})")

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in all_articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    # Sort newest first
    unique.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Write feed.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    print(f"\n✅ Done! {len(unique)} articles from {len(SOURCES)} sources → feed.json  ({elapsed:.1f}s)\n")


if __name__ == "__main__":
    main()
