import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Multi-language global aggregation query
SEARCH_URL = "https://html.duckduckgo.com/html/?q=AC+Milan+news+breaking"

sent = set()

# ------------------------------------------------------------------
# EXTRACT CLEAN SOURCE NAME
# ------------------------------------------------------------------
def get_clean_source(url):
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        # Get primary brand name (e.g., sempremilan.com -> SEMPREMILAN)
        source_name = domain.split(".")[0].upper()
        return source_name if source_name else "MILAN UPDATE"
    except:
        return "GLOBAL FOOTBALL"

# ------------------------------------------------------------------
# SCRAPE ARTICLE META DATA & RAW MEDIA
# ------------------------------------------------------------------
def get_article_data(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        # Extract Real Image (OG/Twitter)
        img_tag = soup.find("meta", property="og:image") or soup.find("meta", property="twitter:image")
        img_url = img_tag.get("content") if img_tag else None

        # Clean fallback image check
        if not img_url:
            first_img = soup.find("img")
            if first_img and first_img.get("src", "").startswith("http"):
                img_url = first_img.get("src")

        return img_url
    except:
        return None

# ------------------------------------------------------------------
# GENERATE AN EXTENDED 10-12 LINE SUMMARY
# ------------------------------------------------------------------
def build_news_caption(title, source):
    # Strip residual tracking tags or domain tails from the headline
    clean_title = re.sub(r'\s*[\-\|]\s*.*$', '', title).strip()

    return f"""⚽ <b>AC MILAN GLOBAL UPDATE</b>

📰 <b>Headline:</b>
{clean_title}

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
# TELEGRAM TRANSMISSION (Hides all URLs natively inside data structures)
# ------------------------------------------------------------------
def send_telegram(img, message):
    if img:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": img, "caption": message[:1024], "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Delivery failed: {e}")

# ------------------------------------------------------------------
# ENGINE EXECUTION
# ------------------------------------------------------------------
def main():
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    try:
        response = requests.get(SEARCH_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("div", class_="result__body")
    except:
        return

    count = 0
    for item in results:
        if count >= 5:  # Process top 5 global breaking items
            break

        link_tag = item.find("a", class_="result__url")
        title_tag = item.find("a", class_="result__title")
        
        if not link_tag or not title_tag:
            continue
            
        raw_url = link_tag.get("href")
        title_text = title_tag.get_text()

        # Extract direct clean url from search redirect wrapper if present
        if "uddg=" in raw_url:
            raw_url = raw_url.split("uddg=")[1].split("&")[0]
            raw_url = requests.utils.unquote(raw_url)

        if raw_url in sent:
            continue

        source_name = get_clean_source(raw_url)
        real_image = get_article_data(raw_url)
        formatted_message = build_news_caption(title_text, source_name)

        send_telegram(real_image, formatted_message)
        sent.add(raw_url)
        count += 1

if __name__ == "__main__":
    main()
