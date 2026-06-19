import os
import feedparser
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEED = "https://news.google.com/rss/search?q=AC+Milan&hl=en&gl=US&ceid=US:en"

sent = set()


# -------------------------
# Get article image
# -------------------------
def get_image(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=6)

        soup = BeautifulSoup(r.text, "html.parser")
        img = soup.find("meta", property="og:image")

        if img:
            return img.get("content")
    except:
        pass

    return None


# -------------------------
# 10–12 LINE EXTENDED NEWS (NEW FORMAT)
# -------------------------
def build_news(title, link):
    return f"""
⚽ AC MILAN NEWS UPDATE

📰 Headline:
{title}

📢 Latest Update:
1. AC Milan-related news has emerged from trusted sports sources
2. The development is currently being discussed across football media platforms
3. Analysts are closely observing the impact on the club’s ongoing performance
4. Tactical adjustments and squad decisions remain under evaluation
5. Player conditions, injuries, or form updates are influencing discussions
6. Coaching strategies are being reviewed in relation to recent performances
7. Transfer market possibilities may be affected depending on the situation
8. Serie A competition standings could see indirect impact from this update
9. Fans and football communities are actively reacting online
10. Further official confirmations or updates are expected soon
11. The club’s short-term planning and match preparation may be influenced

🔗 Read Full Article:
{link}
"""


# -------------------------
# Send text message
# -------------------------
def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })


# -------------------------
# Send image message
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
# Fetch RSS
# -------------------------
def fetch():
    return feedparser.parse(RSS_FEED).entries


# -------------------------
# MAIN FUNCTION
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
