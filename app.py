
from flask import Flask, render_template, request, redirect
import time, html, re, urllib.parse
import requests, feedparser
from bs4 import BeautifulSoup

try:
    from readability import Document
    HAVE_READABILITY = True
except Exception:
    HAVE_READABILITY = False

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque

app = Flask(__name__)

# Configuration

COMPANIES = [
    "Apple","Microsoft","Alphabet","Amazon","NVIDIA","Meta","Tesla","Berkshire Hathaway","TSMC","Saudi Aramco",
    "Eli Lilly","JPMorgan Chase","Visa","Johnson & Johnson","Walmart","Mastercard","Procter & Gamble",
    "UnitedHealth Group","Novo Nordisk","ICBC","Samsung Electronics","Nestlé","Roche","Tencent","Kweichow Moutai",
    "ASML","Oracle","Broadcom","Costco","AbbVie","PepsiCo","Bank of America","ExxonMobil","Coca-Cola","Adobe",
    "Netflix","Intel","Cisco","Accenture","Toyota","LVMH","Shell","Pfizer","Reliance Industries","IBM","Salesforce",
    "Qualcomm","Nike","AT&T","Sony","SAP","Comcast","McDonald’s","UPS","HSBC","TotalEnergies","BP","Alibaba",
    "ByteDance","Tencent Music","Baidu","AMD","Booking Holdings","PayPal","ServiceNow","Shopify","Airbnb",
    "Snowflake","Uber","Dell","Siemens","Unilever","Honda","General Motors","Ford","Intuit","Walt Disney",
    "Starbucks","Zoom","Taiwan Mobile","Infosys","TCS","HCLTech","Capgemini","NIO","Ferrari","Volkswagen",
    "Mercedes-Benz","Prudential","AstraZeneca","GlaxoSmithKline","Sanofi","Danaher","CATL","BYD","PetroChina",
    "Charter Communications","American Express","BlackRock","Morgan Stanley","Goldman Sachs","UBS"
]

# -----------------------------
# Expanded RSS_FEEDS (~200+). Keep adding more if you like.
# -----------------------------
RSS_FEEDS = [
    # 🌍 Global News & Business
    "http://feeds.bbci.co.uk/news/business/rss.xml",
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.theguardian.com/uk/business/rss",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.reuters.com/reuters/topNews",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.ft.com/?format=rss",
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",   # Top news
    "https://www.cnbc.com/id/100003114/device/rss/rss.html", # Technology
    "https://www.npr.org/rss/rss.php?id=1006",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ Markets
    "https://feeds.a.dj.com/rss/RSSWSJD.xml",         # WSJ Tech
    "https://www.wsj.com/xml/rss/3_7014.xml",         # World
    "https://www.wsj.com/xml/rss/3_7085.xml",         # US Business


    "https://www.apple.com/newsroom/rss-feed.rss",  # Apple
    "https://blogs.microsoft.com/feed/",            # Microsoft
    "https://blog.google/rss/",                     # Alphabet (Google)
    "https://www.aboutamazon.com/rss",              # Amazon
    "https://nvidianews.nvidia.com/news?rss=true",  # NVIDIA
    "https://about.fb.com/news/feed/",              # Meta
    "https://newsroom.ibm.com/index.php?s=20423&pagetemplate=rss",  # IBM
    "https://newsroom.intel.com/feed/",             # Intel
    "https://newsroom.cisco.com/rss-feeds",         # Cisco
    "https://www.qualcomm.com/rss/newsroom/press-releases", # Qualcomm
    "https://www.salesforce.com/news/rss/",         # Salesforce
    "https://www.pfizer.com/news/rss",              # Pfizer
    "https://www.jnj.com/rss-feeds",                # Johnson & Johnson
    "https://usa.visa.com/rss/news.xml",            # Visa
    "https://newsroom.mastercard.com/feed/",        # Mastercard
    "https://news.adobe.com/en/rss",                # Adobe
    "https://global.toyota/en/newsroom/rss.json",   # Toyota (global)
    "https://www.coca-colacompany.com/rss",         # Coca-Cola
    "https://news.nike.com/rss",                    # Nike
    "https://www.sony.com/en/news/rss",             # Sony

    # Fallback to Yahoo Finance RSS (no official feed)
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA&region=US&lang=en-US",   # Tesla
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BRK.A&region=US&lang=en-US",  # Berkshire Hathaway
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSM&region=US&lang=en-US",    # TSMC
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=2222.SR&region=US&lang=en-US",# Saudi Aramco
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=LLY&region=US&lang=en-US",    # Eli Lilly
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=JPM&region=US&lang=en-US",    # JPMorgan Chase
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=WMT&region=US&lang=en-US",    # Walmart
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=PG&region=US&lang=en-US",     # Procter & Gamble
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=UNH&region=US&lang=en-US",    # UnitedHealth
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVO&region=US&lang=en-US",    # Novo Nordisk
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=1398.HK&region=US&lang=en-US",# ICBC
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=005930.KQ&region=US&lang=en-US",# Samsung
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NESN.SW&region=US&lang=en-US",# Nestlé
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=RHHBY&region=US&lang=en-US",  # Roche
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TCEHY&region=US&lang=en-US",  # Tencent
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=600519.SS&region=US&lang=en-US",# Kweichow Moutai
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=ASML&region=US&lang=en-US",   # ASML
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=ORCL&region=US&lang=en-US",   # Oracle
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AVGO&region=US&lang=en-US",   # Broadcom
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=COST&region=US&lang=en-US",   # Costco
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=ABBV&region=US&lang=en-US",   # AbbVie
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=PEP&region=US&lang=en-US",    # PepsiCo
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BAC&region=US&lang=en-US",    # Bank of America
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=XOM&region=US&lang=en-US",    # ExxonMobil
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NFLX&region=US&lang=en-US",   # Netflix
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=ACN&region=US&lang=en-US",    # Accenture
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=LVMUY&region=US&lang=en-US",  # LVMH
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SHEL&region=US&lang=en-US",   # Shell
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=RELIANCE.BO&region=US&lang=en-US",# Reliance
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=VZ&region=US&lang=en-US",     # AT&T
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CMCSA&region=US&lang=en-US",  # Comcast
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MCD&region=US&lang=en-US",    # McDonald’s
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=UPS&region=US&lang=en-US",    # UPS
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=HSBC&region=US&lang=en-US",   # HSBC
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TTE&region=US&lang=en-US",    # TotalEnergies
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BP&region=US&lang=en-US",     # BP
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BABA&region=US&lang=en-US",   # Alibaba
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=UBER&region=US&lang=en-US",   # Uber
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=DELL&region=US&lang=en-US",   # Dell
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SIEMENS.NS&region=US&lang=en-US", # Siemens
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=UN&region=US&lang=en-US",     # Unilever
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=HMC&region=US&lang=en-US",    # Honda
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GM&region=US&lang=en-US",     # General Motors
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=F&region=US&lang=en-US",      # Ford
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=INTU&region=US&lang=en-US",   # Intuit
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=DIS&region=US&lang=en-US",    # Walt Disney
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SBUX&region=US&lang=en-US",   # Starbucks
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=ZM&region=US&lang=en-US",     # Zoom
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=INFY&region=US&lang=en-US",   # Infosys
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TCS.NS&region=US&lang=en-US", # TCS
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=HCLTECH.NS&region=US&lang=en-US",# HCLTech
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CAP.PA&region=US&lang=en-US", # Capgemini
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NIO&region=US&lang=en-US",    # NIO
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=RACE&region=US&lang=en-US",   # Ferrari
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=VWAGY&region=US&lang=en-US",  # Volkswagen
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MBGYY&region=US&lang=en-US",  # Mercedes-Benz
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=PRU&region=US&lang=en-US",    # Prudential
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AZN&region=US&lang=en-US",    # AstraZeneca
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GSK&region=US&lang=en-US",    # GlaxoSmithKline
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SNY&region=US&lang=en-US",    # Sanofi
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=DHR&region=US&lang=en-US",    # Danaher
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=300750.SZ&region=US&lang=en-US",# CATL
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BYDDF&region=US&lang=en-US",  # BYD
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=PTR&region=US&lang=en-US",    # PetroChina
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CHTR&region=US&lang=en-US",   # Charter
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AXP&region=US&lang=en-US",    # Amex
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BLK&region=US&lang=en-US",    # BlackRock
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MS&region=US&lang=en-US",     # Morgan Stanley
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GS&region=US&lang=en-US",     # Goldman Sachs
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=UBS&region=US&lang=en-US",    # UBS


    # 💻 Tech & Startups
    "http://feeds.feedburner.com/TechCrunch/",
    "https://www.theverge.com/rss/index.xml",
    "http://feeds.arstechnica.com/arstechnica/index",
    "https://www.engadget.com/rss.xml",
    "https://www.wired.com/feed/rss",
    "https://www.zdnet.com/news/rss.xml",
    "https://venturebeat.com/feed/",
    "https://feeds.feedburner.com/thenextweb",
    "https://www.cnet.com/rss/news/",
    "https://www.theinformation.com/feed?type=rss",
    "https://techcrunch.com/tag/enterprise/feed/",
    "https://hnrss.org/frontpage",
    "https://techmeme.com/feed.xml",

    # 💰 US Business / Finance
    "https://www.marketwatch.com/feeds/topstories",
    "https://www.marketwatch.com/feeds/latest-news",
    "https://www.fool.com/feeds/index.aspx",
    "https://seekingalpha.com/market_currents.xml",
    "https://www.investopedia.com/feed/",
    "https://www.barrons.com/rss/homepage",
    "https://www.forbes.com/business/feed/",
    "https://www.forbes.com/most-popular/feed/",
    "https://www.businessinsider.com/rss",

    # 📈 Yahoo Finance (company specific)
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MSFT&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AMZN&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GOOGL&region=US&lang=en-US",

    # 🇮🇳 India / Asia
    "https://timesofindia.indiatimes.com/rssfeeds/1221656.cms",  # TOI Top
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
    "https://www.business-standard.com/rss/latest.rss",
    "https://www.moneycontrol.com/rss/latestnews.xml",
    "https://www.livemint.com/rss/companies",
    "https://www.livemint.com/rss/technology",
    "https://www.thehindubusinessline.com/feeder/default.rss",
    "https://www.financialexpress.com/feed/",
    "https://www.hindustantimes.com/feeds/rss/business/rssfeed.xml",
    "https://www.businessinsider.in/rssfeed",

    # 🇪🇺 Europe
    "https://www.euronews.com/rss?level=theme&name=business",
    "https://www.dw.com/en/rss",
    "https://www.handelsblatt.com/contentexport/feed/rss",
    "https://www.lemonde.fr/economie/rss_full.xml",
    "https://www.lesechos.fr/rss/rss_economie.xml",
    "https://www.elmundo.es/rss/economia.xml",

    # 🚗 Industry / Specialized
    "https://www.autonews.com/rss/all.xml",
    "https://www.retaildive.com/industry-news/rss",
    "https://www.pharmaceutical-technology.com/feed/",
    "https://www.energyintel.com/rss/news.xml",

    # 📰 Regional & Local Business
    "https://www.latimes.com/business/rss2.0.xml",
    "https://www.chicagotribune.com/business/rss2.0.xml",
    "https://www.bostonglobe.com/rss/region/business.xml",
    "https://www.smh.com.au/rss/business.xml",
    "https://www.afr.com/rss",
    "https://www.thehindu.com/business/feeder/default.rss",

    # ₿ Crypto / Finance Niche
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",

    # 📊 Aggregators
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://rssfeeds.usatoday.com/usatoday-NewsTopStories",
    "https://www.nasdaq.com/feed/rssoutbound?category=Market-Activity",

    # 📑 Business Blogs & Commentary
    "https://www.entrepreneur.com/latest.rss",
    "https://www.fastcompany.com/rss",
    "https://www.inc.com/rss",
    "https://www.sfgate.com/rss/feed.xml",
    "https://www.businesswire.com/rss/home.rss",
    "https://www.prnewswire.com/rss/all-news-releases.rss",
    "https://www.marketplace.org/feed/",
]

    # ... you can append hundreds more feeds here as needed

# Headline limits
MIN_HEADLINES_PER_COMPANY = 3   # try to show at least 3 if available
MAX_HEADLINES_PER_COMPANY = 5   # cap per company card

# Parallel fetching
MAX_WORKERS_FEEDS = 32
HTTP_TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (CompanyNewsDashboard/2.0)"}

# Simple in-memory caches to reduce load
FEED_CACHE_TTL = 600  # seconds
ARTICLE_CACHE_TTL = 1800  # seconds
_feed_cache = {}   # url -> (fetched_at_epoch, entries)
_article_cache = {}  # url -> (fetched_at_epoch, [bullets])

# -----------------------------
# Utilities
# -----------------------------
import re

def filter_company_matches(items, company):
    variants = ALIASES.get(company, [company.lower()])
    patterns = [re.compile(rf"\b{re.escape(v.lower())}\b") for v in variants]

    results = []
    for it in items:
        text = " ".join([
            it.get("title", ""),
            it.get("summary") or "",
            it.get("link", "")
        ]).lower()

        if any(p.search(text) for p in patterns):
            results.append(it)

    return results


def _now():
    return int(time.time())

def get_from_feed_cache(url):
    rec = _feed_cache.get(url)
    if not rec:
        return None
    ts, entries = rec
    if _now() - ts > FEED_CACHE_TTL:
        return None
    return entries

def set_feed_cache(url, entries):
    _feed_cache[url] = (_now(), entries)

def get_from_article_cache(url):
    rec = _article_cache.get(url)
    if not rec:
        return None
    ts, bullets = rec
    if _now() - ts > ARTICLE_CACHE_TTL:
        return None
    return bullets

def set_article_cache(url, bullets):
    _article_cache[url] = (_now(), bullets)
from email.utils import parsedate_to_datetime

def normalize_published(entry):
    published = getattr(entry, "published", "") or getattr(entry, "updated", "")
    if not published:
        return "—"
    try:
        dt = parsedate_to_datetime(published)
        return dt.strftime("%d %b %Y %H:%M")
    except Exception:
        return published

from datetime import datetime
import requests, feedparser, html
from concurrent.futures import ThreadPoolExecutor, as_completed

def normalize_published(entry):
    # Try published_parsed (most reliable)
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6]).strftime("%b %d, %Y %I:%M %p")
    # Try updated_parsed
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6]).strftime("%b %d, %Y %I:%M %p")
    # Try raw published string
    elif hasattr(entry, "published"):
        return entry.published
    elif hasattr(entry, "updated"):
        return entry.updated
    return "No date"

def fetch_feed(url):
    # Cached?
    cached = get_from_feed_cache(url)
    if cached is not None:
        return cached
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        feed = feedparser.parse(r.text)
        items = []
        for e in feed.entries:
            title = html.unescape(getattr(e, "title", "")).strip()
            link = getattr(e, "link", "").strip()
            summary = getattr(e, "summary", "") or getattr(e, "description", "")
            if not title or not link:
                continue
            items.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published": normalize_published(e)   # ✅ fixed here
            })
        set_feed_cache(url, items)
        return items
    except Exception:
        # Return empty list on failure; caller will just have fewer matches
        return []

def fetch_all_feeds_parallel():
    all_items = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_FEEDS) as ex:
        futures = [ex.submit(fetch_feed, url) for url in RSS_FEEDS]
        for fut in as_completed(futures):
            items = fut.result()
            if items:
                all_items.extend(items)
    return all_items


def dedupe_by_link(items):
    seen = set()
    out = []
    for it in items:
        lk = it["link"]
        if lk in seen:
            continue
        seen.add(lk)
        out.append(it)
    return out

from fuzzywuzzy import fuzz

def slug_and_text_hit(company, item):
    """
    Improved matching:
    - Title, summary, link checked
    - Token variants
    - Fuzzy ratio threshold for near matches
    """
    cname = company.lower()
    title_l = item.get("title", "").lower()
    summary_l = (item.get("summary") or "").lower()
    link = item.get("link", "").lower()

    # Direct token in title/summary
    if cname in title_l or cname in summary_l:
        return True

    # Partial token matches
    tokens = re.split(r'\W+', company.lower())
    tokens = [t for t in tokens if len(t) > 2]
    for t in tokens:
        if t in title_l or t in summary_l or t in link:
            return True

    # Fuzzy matching threshold
    for text in [title_l, summary_l]:
        if fuzz.partial_ratio(cname, text) >= 80:
            return True

    return False

def filter_company_matches(all_items, company):
    """
    Returns top items per company based on relevance score.
    """
    scored = []
    cname = company.lower()
    for it in all_items:
        score = 0
        title_l = it.get("title", "").lower()
        summary_l = (it.get("summary") or "").lower()
        link = it.get("link","").lower()
        if cname in title_l: score += 3
        if cname in summary_l: score +=2
        if cname in link: score +=1
        # fuzzy match
        score += fuzz.partial_ratio(cname, title_l)//20
        if score>0: scored.append((score,it))
    scored.sort(key=lambda x:-x[0])
    return [it for s,it in scored]

def extract_main_text(url):
    """
    Use Readability for best text extraction; fallback: <p> tags.
    Cleans out scripts/ads.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        html_text = r.text

        if HAVE_READABILITY:
            doc = Document(html_text)
            content_html = doc.summary()
            soup = BeautifulSoup(content_html, "html.parser")
        else:
            soup = BeautifulSoup(html_text, "html.parser")
        # remove scripts/styles
        for tag in soup(["script","style","noscript","header","footer","form","svg"]):
            tag.decompose()
        paras = [p.get_text(" ",strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True))>30]
        text = " ".join(paras)
        return text
    except Exception:
        return ""


def short_company_variants(company):
    """
    Return possible short forms for fallback matching:
    e.g. 'Johnson & Johnson' -> ['johnson', 'johnson johnson', 'j&j'...]
    """
    variants = set()
    base = company.lower()
    variants.add(re.sub(r'[^a-z0-9]+', ' ', base).strip())
    # add initials
    initials = "".join([w[0] for w in re.findall(r"[A-Za-z]+", base)])
    if initials:
        variants.add(initials.lower())
    # split words
    for w in re.findall(r"[A-Za-z]{3,}", base):
        variants.add(w.lower())
    return variants

def extract_main_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        html_text = r.text

        # Try readability first for better content targeting
        if HAVE_READABILITY:
            try:
                doc = Document(html_text)
                content_html = doc.summary()
                soup = BeautifulSoup(content_html, "html.parser")
                paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
                text = " ".join(paras)
                if len(text.split()) > 80:
                    return text
            except Exception:
                pass

        # Fallback: all <p> tags
        soup = BeautifulSoup(html_text, "html.parser")
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(paras)
        return text
    except Exception:
        return ""

def summarize_text(text, sentence_count=10):
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summ = TextRankSummarizer()
        sents = summ(parser.document, sentence_count)
        bullets = [str(s).strip() for s in sents if str(s).strip()]
        bullets = [re.sub(r"\s+", " ", b) for b in bullets]
        return bullets if bullets else []
    except Exception:
        return []

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    start = time.time()
    all_items = fetch_all_feeds_parallel()

    # --- 🌍 Country filtering ---
    code_to_country = {
        "us": "United States",
        "in": "India",
        "uk": "United Kingdom",
        "jp": "Japan",
        "de": "Germany",
        "fr": "France"
    }

    selected_code = request.args.get("country", "").strip().lower()
    selected_country = code_to_country.get(selected_code, "")

    filtered_items = all_items
    if selected_country:
        country_l = selected_country.lower()
        country_matches = [
            it for it in all_items
            if country_l in it.get("title", "").lower()
            or country_l in (it.get("summary") or "").lower()
            or country_l in it.get("link", "").lower()
        ]
        if country_matches:
            filtered_items = country_matches
        else:
            filtered_items = all_items   # fallback if no matches

    # --- company news build (same as before) ---
    company_news = {}
    for company in COMPANIES:
        matches = filter_company_matches(filtered_items, company)
        matches = dedupe_by_link(matches)

        if len(matches) < MIN_HEADLINES_PER_COMPANY:
            variants = short_company_variants(company)
            additional = []
            for it in filtered_items:
                title_l = it.get("title", "").lower()
                summary_l = (it.get("summary") or "").lower()
                for v in variants:
                    if v in title_l or v in summary_l or v in it.get("link", "").lower():
                        additional.append(it)
                        break
            additional = dedupe_by_link(additional)
            matches = matches + [a for a in additional if a not in matches]

        company_news[company] = matches[:MAX_HEADLINES_PER_COMPANY]

    elapsed = time.time() - start

    return render_template(
        "index.html",
        company_news=company_news,
        companies_count=len(COMPANIES),
        feeds_count=len(RSS_FEEDS),
        min_headlines=MIN_HEADLINES_PER_COMPANY,
        max_headlines=MAX_HEADLINES_PER_COMPANY,
        now=time.strftime("%Y-%m-%d %H:%M:%S"),
        elapsed_ms=int(elapsed * 1000),
        selected_country=selected_code  #  pass back the code for dropdown selection
    )

@app.route("/summary")
def summary():
    url = request.args.get("url", "").strip()
    company = request.args.get("t", "").strip()
    if not url:
        return "<h3>Missing URL</h3>", 400

    cached = get_from_article_cache(url)
    if cached:
        bullets = cached
    else:
        text = extract_main_text(url)
        bullets = summarize_text(text, 10) if len(text.split()) > 80 else []
        if not bullets:
            bullets = ["Could not summarize this article.", "Tip: Open original article."]
        set_article_cache(url, bullets)

    img_url = ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")

        # Prefer OpenGraph image
        og_img = soup.find("meta", property="og:image")
        twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
        img_tag = soup.find("img")

        if og_img and og_img.get("content"):
            img_url = og_img["content"]
        elif twitter_img and twitter_img.get("content"):
            img_url = twitter_img["content"]
        elif img_tag and "http" in img_tag.get("src", ""):
            img_url = img_tag["src"]
    except:
        pass

    return render_template(
        "summary.html",
        bullets=bullets,
        url=url,
        company=company,
        img_url=img_url
    )

# -----------------------------
# Entry
# -----------------------------
if __name__ == "__main__":
    # Run: python app.py  ->  http://127.0.0.1:5000/
    app.run(host="0.0.0.0", port=5000, debug=True)
