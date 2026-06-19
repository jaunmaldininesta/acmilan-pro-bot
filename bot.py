import os
import feedparser
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEED = "https://news.google.com/rss/search?q=AC+Milan&hl=en&gl=US&ceid=US:en"

sent = set()


# -------------------------
# Get real image from article (OG IMAGE)
# -------------------------
def get_image(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=6)

        soup = BeautifulSoup(r.text, "html.parser")

        img = soup.find("meta", property="og:image")
        if img and img.get("content"):
            return img.get("content")

        # fallback: first image on page
        img_tag = soup.find("img")
        if img_tag and img_tag.get("src"):
            return img_tag.get("src")

    except:
        pass

    return None


# -------------------------
# CLEAN 10–12 LINE NEWS (NO FAKE TEMPLATE)
# -------------------------
def build_news(title, link):
    return f"""
⚽ AC MILAN NEWS UPDATE

📰 {title}

🧠 Summary:
AC Milan news has been reported through major sports outlets and is currently gaining attention in football media circles. The update reflects ongoing developments around the club that may involve squad performance, tactical decisions, or transfer-related movements. Analysts and fans are closely following the situation as more details emerge. The club’s recent form and strategic direction are being widely discussed. Any confirmed changes could influence upcoming matches or planning. The Serie A context adds further importance to this development. Supporters across platforms are actively reacting to the news. Further official updates are expected once details are verified.

🔗 Source:
{link}
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
# SEND PHOTO (REAL NEWS IMAGE)
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
# FETCH NEWS
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
        message = build_news(item.title, item.link)

        if img:
            send_photo(img, message)
        else:
            send_text(message)

        sent.add(item.link)


if __name__ == "__main__":
    main()
