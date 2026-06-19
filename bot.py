import os
import time
import feedparser
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google import genai

# পরিবেশ ভেরিয়েবল (GitHub Secrets থেকে আসবে)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

RSS_FEED = "https://news.google.com/rss/search?q=AC+Milan&hl=en&gl=US&ceid=US:en"

# ব্যাকআপ ইমেজের কালেকশন (যদি কোনো ছবিই ম্যাচ না করে)
DEFAULT_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/Logo_of_AC_Milan.svg/1200px-Logo_of_AC_Milan.svg.png"

# Gemini ক্লায়েন্ট
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def clean_title_for_search(title):
    """হেডলাইন থেকে অপ্রয়োজনীয় ক্যারেক্টার বাদ দিয়ে সার্চ কিওয়ার্ড তৈরি করা"""
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    words = clean.split()
    # প্রথম ৪-৫টি গুরুত্বপূর্ণ কি-ওয়ার্ড নেওয়া
    keywords = [w for w in words if len(w) > 3][:5]
    return "+".join(keywords) if keywords else "AC+Milan"


# ---------------------------------------------------
# ইন্টারনেট থেকে কিওয়ার্ড অনুযায়ী লাইভ ছবি খোঁজা (Unsplash API Free Source)
# ---------------------------------------------------
def search_fallback_image(title):
    try:
        query = clean_title_for_search(title)
        # Unsplash এর ওপেন লাইব্রেরি থেকে কিওয়ার্ড অনুযায়ী ফুটবল/ম্যাচ ছবি খোঁজা
        search_url = f"https://source.unsplash.com/featured/1600x900/?football,{query}"
        
        response = requests.get(search_url, timeout=5)
        if response.status_code == 200 and "html" not in response.url:
            return response.url
    except:
        pass
    return DEFAULT_LOGO


# ---------------------------------------------------
# গুগলের রিডাইরেক্ট লিংক থেকে আসল লিংক ও ছবি বের করা
# ---------------------------------------------------
def get_real_url_and_image(google_news_url, title):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    try:
        # ১. গুগলের লিংকটিতে রিকোয়েস্ট পাঠিয়ে ফাইনাল URL বের করা
        response = requests.get(google_news_url, headers=headers, timeout=6, allow_redirects=True)
        real_url = response.url
        
        if "news.google.com" in real_url:
            soup = BeautifulSoup(response.text, "html.parser")
            meta_tag = soup.find("meta", attrs={"refresh": True})
            if meta_tag:
                content = meta_tag.get("content", "")
                if "url=" in content:
                    real_url = content.split("url=")[-1]

        # ২. আসল নিউজ ওয়েবসাইট থেকে বাস্তব ছবি স্ক্র্যাপ করা
        article_response = requests.get(real_url, headers=headers, timeout=6)
        article_soup = BeautifulSoup(article_response.text, "html.parser")
        
        img_tag = article_soup.find("meta", property="og:image") or \
                  article_soup.find("meta", attrs={"name": "twitter:image"}) or \
                  article_soup.find("meta", property="twitter:image")
                  
        if img_tag and img_tag.get("content") and img_tag.get("content").startswith("http"):
            return real_url, img_tag.get("content")
            
        # [নতুন ট্রিক] সোর্স ওয়েবসাইটে ছবি না থাকলে হেডলাইন ম্যাচ করে ইন্টারনেট থেকে লাইভ ছবি আনা হবে
        return real_url, search_fallback_image(title)
    except Exception as e:
        print(f"Scraping Error: {e}")
        return google_news_url, search_fallback_image(title)


# ---------------------------------------------------
# Gemini AI দিয়ে বাস্তব ও নিখুঁত সামারি তৈরি
# ---------------------------------------------------
def generate_ai_summary(title, article_url):
    if not ai_client:
        return "• Extended summary details are currently being updated in the sports section."

    prompt = f"""
    You are an expert sports journalist for AC Milan. 
    Analyze this news headline: "{title}" and the article link: {article_url}.
    Write a 6 to 8 line bulleted analytical summary about this update in professional English.
    Focus only on real tactical points, fan reactions, or match/transfer impacts relevant to this headline.
    Do not use generic templates or placeholders. Make it sound like a real sports report.
    Format each line with a bullet point (•).
    """
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "• Direct article insights are currently evaluating by football media networks."


# ---------------------------------------------------
# মেসেজ ফরম্যাট (HTML স্টাইল)
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
# Telegram API Actions (ডাউনলোড অ্যান্ড আপলোড মেথড)
# ---------------------------------------------------
def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


def send_photo_as_file(img_url, caption, title):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    local_filename = "temp_image.jpg"
    
    try:
        # ১. ইমেজটি ডাউনলোড করা
        img_response = requests.get(img_url, headers=headers, timeout=8)
        if img_response.status_code != 200:
            # সোর্স ব্লক করলে ইন্টারনেট থেকে হেডলাইনের কিওয়ার্ড ভিত্তিক অল্টারনেটিভ ছবি ডাউনলোড করা হবে
            fallback_url = search_fallback_image(title)
            img_response = requests.get(fallback_url, headers=headers, timeout=6)
            
        with open(local_filename, 'wb') as handler:
            handler.write(img_response.content)
        
        # ২. ফাইল আকারে টেলিগ্রামে ডিরেক্ট আপলোড
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(local_filename, 'rb') as photo_file:
            files = {'photo': photo_file}
            data = {
                "chat_id": CHAT_ID,
                "caption": caption[:1024],
                "parse_mode": "HTML"
            }
            r = requests.post(url, data=data, files=files)
            
        if os.path.exists(local_filename):
            os.remove(local_filename)
            
        return r.status_code == 200
    except Exception as e:
        print(f"Image Send Error: {e}")
        if os.path.exists(local_filename):
            os.remove(local_filename)
        return False


def fetch():
    return feedparser.parse(RSS_FEED).entries


# ---------------------------------------------------
# MAIN FUNCTION (২৪ ঘণ্টার ফিল্টারিং সহ)
# ---------------------------------------------------
def main():
    news = fetch()

    now = datetime.utcnow()
    time_threshold = now - timedelta(hours=24, minutes=5)

    for item in news[:5]:

        if hasattr(item, "published_parsed") and item.published_parsed:
            pub_time = datetime(*item.published_parsed[:6])
            if pub_time < time_threshold:
                continue
        else:
            continue

        # বাস্তব URL এবং ইমেজ প্রসেসিং
        real_url, img_url = get_real_url_and_image(item.link, item.title)
        
        ai_summary = generate_ai_summary(item.title, real_url)
        message = build_news_message(item.title, ai_summary, real_url)

        # ইমেজ ডাউনলোডের মাধ্যমে ফাইল মেথডে পাঠানো হচ্ছে
        success = send_photo_as_file(img_url, message, item.title)
        if not success:
            send_text(message)

        time.sleep(3)


if __name__ == "__main__":
    main()
