import os
import time
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google import genai

# পরিবেশ ভেরিয়েবল
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

RSS_FEED = "https://news.google.com/rss/search?q=AC+Milan&hl=en&gl=US&ceid=US:en"

# Gemini ক্লায়েন্ট ইনিশিয়েট করা
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ---------------------------------------------------
# আর্টিকেলের বাস্তব ছবি (Feature Image) বের করা
# ---------------------------------------------------
def get_real_image(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        # গুগল নিউজের রিডাইরেক্ট লিংক থেকে আসল URL বের করা
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        
        img_tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if img_tag:
            return img_tag.get("content")
    except:
        pass
    return None

# ---------------------------------------------------
# Gemini AI দিয়ে বাস্তব ও নিখুঁত সামারি তৈরি
# ---------------------------------------------------
def generate_ai_summary(title, article_url):
    if not ai_client:
        return "• Extended summary details are currently being updated in the sports section."

    prompt = f"""
    You are an expert sports journalist for AC Milan. 
    Analyze this news headline: "{title}" and the article link: {article_url}.
    Write a 6 to 8 line bulleted analytical summary about this update in professional English.
    Focus only on real tactical points, fan reactions, or match/transfer impacts relevant to this headline.
    Do not use generic templates. Make it sound like a real sports report.
    Format each line with a bullet point (•).
    """
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "• Direct article insights are currently evaluating by football media networks."

# ---------------------------------------------------
# মেসেজ ফরম্যাট
# ---------------------------------------------------
def build_news_message(title, summary, link):
    return f"""
⚽ <b>AC MILAN NEWS UPDATE</b>

📰 <b>Headline:</b>
{title}

📢 <b>Latest Breakdown:</b>
{summary}

🔗 <b>Read Full Article:</b>
<a href="{link}">Click Here for Details</a>
"""

# ---------------------------------------------------
# Telegram Actions
# ---------------------------------------------------
def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def send_photo(img, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    requests.post(url, data={"chat_id": CHAT_ID, "photo": img, "caption": caption[:1024], "parse_mode": "HTML"})

def fetch():
    return feedparser.parse(RSS_FEED).entries

# ---------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------
def main():
    news = fetch()
    
    now = datetime.utcnow()
    time_threshold = now - timedelta(minutes=11) # ১০ মিনিটের আগের পুরোনো নিউজ বাদ দিবে

    for item in news[:5]:
        if hasattr(item, 'published_parsed') and item.published_parsed:
            pub_time = datetime(*item.published_parsed[:6])
            if pub_time < time_threshold:
                continue
        else:
            continue

        # বাস্তব ছবি ও এআই সামারি জেনারেট করা
        img_url = get_real_image(item.link)
        ai_summary = generate_ai_summary(item.title, item.link)
        
        message = build_news_message(item.title, ai_summary, item.link)

        if img_url and img_url.startswith("http"):
            send_photo(img_url, message)
        else:
            send_text(message)
            
        time.sleep(2)

if __name__ == "__main__":
    main()
