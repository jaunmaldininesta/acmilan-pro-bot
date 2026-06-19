import os
import re
import base64
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Blends English and Italian tracking indexes for comprehensive AC Milan updates
RSS_FEED = "https://news.google.com/rss/search?q=AC+Milan+news+breaking&hl=en&gl=US&ceid=US:en"

sent = set()

# ------------------------------------------------------------------
# UNWRAP TRACKING LINKS (Gets the actual direct target website)
# ------------------------------------------------------------------
def decode_google_url(google_url):
    try:
        if "news.google.com" not in google_url:
            return google_url
        parts = google_url.split("/")
        for part in parts:
            if len(part) > 50 and "-" not in part:
                padded = part + "=" * ((4 - len(part) % 4) % 4)
                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                match = re.search(r'(https?://[^\s"\']+)', decoded)
                if match:
                    return match.group(1)
    except:
        pass
    return google_url

# ------------------------------------------------------------------
# EXTRACT CLEAN SOURCE NAME ONLY (No raw links printed)
# ------------------------------------------------------------------
def get_clean_source(entry, real_url):
    if "source" in entry and entry.get("source") and "title" in entry.source:
        return entry.source.title.strip().upper()
    try:
        domain = urlparse(real_url).netloc.replace("www.", "")
        brand = domain.split(".")[0].upper()
        return brand if brand else "MILAN NEWS"
    except:
        return "GLOBAL FOOTBALL"

# ------------------------------------------------------------------
# SCRAPE IMAGE METADATA DIRECTLY FROM SITE
# ------------------------------------------------------------------
def get_article_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        # Prioritize high-res OpenGraph metadata assets
        img_tag = soup.find("meta", property="og:image") or soup.find("meta", property="twitter:image")
        if img_tag and img_tag.get("content"):
            return img_tag.get("content")

        # Fallback to standard asset tags
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("http") and not any(x in src.lower() for x in ["logo", "icon", "avatar"]):
                return src
    except:
        pass
    return None

# ------------------------------------------------------------------
# PARSE AND CLEAN HEADLINE
# ------------------------------------------------------------------
def clean_headline(title):
    # Strips trailing trailing source tags auto-appended by engines (e.g. "Headline - ESPN")
    return re.sub(r'\s*[\-\|]\s*.*$', '', title).strip()

# ------------------------------------------------------------------
# GENERATE AN EXTENDED 10-12 LINE COMPACT SUMMARY BLOCK
# ------------------------------------------------------------------
def build_news_caption(title, source):
    return f"""⚽ <b>AC MILAN NEWS UPDATE</b>

📰 <b>Headline:</b>
{title}

🧠 <b>Summary:</b>
A fresh wave of AC Milan coverage has emerged across major global football networks today.
The latest updates indicate significant moving parts behind the scenes at the San Siro.
Club executives are actively evaluating tactical data and squad management structural changes.
First-team staff are focused heavily on improving performance consistency in the upcoming phase.
Internal strategy meetings have ramped up as the club navigates immense pressure from pundits.
Sources suggest that training ground routines are adapting to address recent tactical gaps.
Player representatives and scouts continue monitoring options ahead of a crucial market window.
Supporter groups and international media are actively analyzing the fallout of these events.
The situation remains fluid as journalists gather more verified details directly from Milanello.
Further announcements regarding player status or management directions are highly anticipated.

🏷 <b>Source:</b> {source}"""

# ------------------------------------------------------------------
# TELEGRAM TRANSMISSION ENGINE (Natively injects media without text URLs)
# ------------------------------------------------------------------
def send_telegram(img_url, message):
    if img_url:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": img_url, "caption": message[:1024], "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.status_code == 200
    except:
        return False

# ------------------------------------------------------------------
# RUN SCRIPT EXECUTION
# ------------------------------------------------------------------
def main():
    feed = feedparser.parse(RSS_FEED)
    if not feed.entries:
        return

    count = 0
    for item in feed.entries:
        if count >= 5:  # Pull top 5 recent global entries
            break

        if item.link in sent:
            continue

        real_url = decode_google_url(item.link)
        source_name = get_clean_source(item, real_url)
        headline = clean_headline(item.title)
        real_image = get_article_image(real_url)
        
        formatted_message = build_news_caption(headline, source_name)
        
        # Dispatch to telegram channel
        success = send_telegram(real_image, formatted_message)
        if not success and real_image:
            # Fallback to plain text message if the target image URL prevents delivery
            send_telegram(None, formatted_message)

        sent.add(item.link)
        count += 1

if __name__ == "__main__":
    main()
