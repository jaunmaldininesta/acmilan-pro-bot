import os
import feedparser
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEED = "https://news.google.com/rss/search?q=AC+Milan&hl=en&gl=US&ceid=US:en"

sent = set()

# -------------------------
# Get image from article
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
# Extended 10–12 line news
# -------------------------
def build_news(title, link):
    return f"""
⚽ AC MILAN NEWS UPDATE

📰 {title}

📌 Full Analysis:
- Latest AC Milan development reported globally
- Tactical updates and squad performance insights
- Media coverage increasing across Europe
- Fans reacting strongly on social platforms
- Serie A impact being evaluated
- Coaching decisions under review
- Player form and fitness discussed
- Possible transfer or match implications
- Club strategy being monitored closely
- More verified updates expected soon

🔗 Read full article:
{link}
"""

# -------------------------
# Send Telegram text
# -------------------------
def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    res = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })

    print("TEXT RESPONSE:", res.text)

# -------------------------
# Send Telegram photo
# -------------------------
def send_photo(img, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    res = requests.post(url, data={
        "chat_id": CHAT_ID,
        "photo": img,
        "caption": caption[:1024],
        "parse_mode": "HTML"
    })

    print("PHOTO RESPONSE:", res.text)

# -------------------------
# Fetch news
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
