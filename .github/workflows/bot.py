import os
import json
import feedparser
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS = "https://news.google.com/rss/search?q=AC+Milan&hl=en&gl=US&ceid=US:en"

# -------------------------
# Load cache (persistent)
# -------------------------
def load_cache():
    try:
        with open("cache.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_cache(data):
    with open("cache.json", "w") as f:
        json.dump(data, f)

cache = load_cache()

# -------------------------
# Important news filter
# -------------------------
def is_important(title):
    keywords = [
        "AC Milan", "Milan", "Rossoneri",
        "transfer", "injury", "coach",
        "signed", "deal", "breaking"
    ]
    t = title.lower()
    return any(k.lower() in t for k in keywords)

# -------------------------
# Image extractor
# -------------------------
def get_image(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        soup = BeautifulSoup(r.text, "html.parser")
        img = soup.find("meta", property="og:image")
        if img:
            return img.get("content")
    except:
        pass
    return None

# -------------------------
# AI-style summary generator
# -------------------------
def summarize(title):
    return f"""
⚽ AC MILAN BREAKING ANALYSIS

📰 {title}

📌 Key Insights:
- Latest development in AC Milan camp
- Tactical and squad implications under review
- Media and fan reaction growing rapidly
- Serie A impact being evaluated
- Possible future consequences discussed
- Club strategy being closely monitored
- Player condition and performance relevance noted
- Football analysts providing mixed opinions
- Transfer or injury angle may be involved
- More verified updates expected soon
"""

# -------------------------
# Telegram send photo
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
# Telegram send text
# -------------------------
def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })

# -------------------------
# Fetch news
# -------------------------
def fetch():
    return feedparser.parse(RSS).entries

# -------------------------
# MAIN
# -------------------------
def main():
    global cache

    news = fetch()

    for item in news[:10]:

        if item.link in cache:
            continue

        if not is_important(item.title):
            continue

        img = get_image(item.link)
        text = summarize(item.title)

        if img:
            send_photo(img, text)
        else:
            send_text(text)

        cache.append(item.link)

    save_cache(cache)

if __name__ == "__main__":
    main()
