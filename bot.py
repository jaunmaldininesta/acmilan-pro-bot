import os
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEED = "https://news.google.com/rss/search?q=AC+Milan&hl=en&gl=US&ceid=US:en"

sent = set()


# -------------------------
# Extract source name only
# -------------------------
def get_source_name(entry):
    if "source" in entry and entry.source and "title" in entry.source:
        return entry.source.title

    # fallback from link domain
    try:
        domain = urlparse(entry.link).netloc.replace("www.", "")
        return domain
    except:
        return "AC Milan News"


# -------------------------
# Get REAL image (article / twitter / og:image)
# -------------------------
def get_image(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=6)

        soup = BeautifulSoup(r.text, "html.parser")

        # 1. OG image (best)
        img = soup.find("meta", property="og:image")
        if img and img.get("content"):
            return img.get("content")

        # 2. Twitter image fallback
        img = soup.find("meta", property="twitter:image")
        if img and img.get("content"):
            return img.get("content")

        # 3. First image fallback
        img_tag = soup.find("img")
        if img_tag and img_tag.get("src"):
            return img_tag.get("src")

    except:
        pass

    return None


# -------------------------
# CLEAN 10–12 LINE NEWS (NO SOURCE LINK)
# -------------------------
def build_news(title, source):
    return f"""
⚽ AC MILAN NEWS UPDATE

📰 Headline:
{title}

🧠 Summary:
AC Milan news has emerged through major sports coverage and is currently being discussed across football communities. The update reflects ongoing developments related to the club’s performance, strategy, or squad situation. Analysts and fans are closely following the situation as more details unfold. Tactical decisions and player conditions may be involved in this development. The club’s recent form continues to be evaluated in the Serie A context. Transfer or future planning implications cannot be ruled out depending on confirmation. Social media reactions from supporters are increasing. The situation remains dynamic as more verified information becomes available. Further updates are expected once official details are released.

🏷 Source:
{source}
"""


# -------------------------
# SEND TEXT
# -------------------------
def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })


# -------------------------
# SEND PHOTO (REAL IMAGE)
# -------------------------
def send_photo(img, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "photo": img,
        "caption": caption[:1024],
        "parse_mode": "HTML"
    })


# -------------------------
# FETCH RSS
# -------------------------
def fetch():
    return feedparser.parse(RSS_FEED).entries


# -------------------------
# MAIN
# -------------------------
def main():
    news = fetch()

    for item in news[:7]:

        if item.link in sent:
            continue

        img = get_image(item.link)
        source = get_source_name(item)
        message = build_news(item.title, source)

        if img:
            send_photo(img, message)
        else:
            send_text(message)

        sent.add(item.link)


if __name__ == "__main__":
    main()
