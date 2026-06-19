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

# Gemini ক্লায়েন্ট
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ---------------------------------------------------
# গুগলের রিডাইরেক্ট লিংক থেকে আসল লিংক ও ছবি বের করা
# ---------------------------------------------------
def get_real_url_and_image(google_news_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(google_news_url, headers=headers, timeout=6, allow_redirects=True)
        real_url = response.url
        
        if "news.google.com" in real_url:
            soup = BeautifulSoup(response.text, "html.parser")
            meta_tag = soup.find("meta", attrs={"refresh": True})
            if meta_tag:
                content = meta_tag.get("content", "")
                if "url=" in content:
                    real_url = content.split("url=")[-1]

        article_response = requests.get(real_url, headers=headers, timeout=6)
        article_soup = BeautifulSoup(article_response.text, "html.parser")
        
        img_tag = article_soup.find("meta", property="og:image") or \
                  article_soup.find("meta", attrs={"name": "twitter:image"}) or \
                  article_soup.find("meta", property="twitter:image")
                  
        if img_tag and img_tag.get("content"):
            return real_url, img_tag.get("content")
            
        return real_url, None
    except Exception as e:
        print(f"Scraping Error: {e}")
        return google_news_url, None


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
# Telegram API Actions (ফাইল আপলোড মেথড সহ)
# ---------------------------------------------------
def send_text(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


def send_photo_as_file(img_url, caption):
    """ছবিটি লোকালি ডাউনলোড করে ফাইল হিসেবে টেলিগ্রামে আপলোড করার নতুন মেকানিজম"""
    headers = {"User-Agent": "Mozilla/5.0"}
    local_filename = "temp_image.jpg"
    
    try:
        # ১. ইমেজটি লোকালি ডাউনলোড করা
        img_data = requests.get(img_url, headers=headers, timeout=5).content
        with open(local_filename, 'wb') as handler:
            handler.write(img_data)
        
        # ২. ফাইল আকারে টেলিগ্রামে পোস্ট করা
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(local_filename, 'rb') as photo_file:
            files = {'photo': photo_file}
            data = {
                "chat_id": CHAT_ID,
                "caption": caption[:1024],
                "parse_mode": "HTML"
            }
            r = requests.post(url, data=data, files=files)
            
        # ৩. কাজ শেষে টেম্পোরারি ফাইলটি ডিলিট করা
        if os.path.exists(local_filename):
            os.remove(local_filename)
            
        return r.status_code == 200
    except Exception as e:
        print(f"Failed to download/upload image: {e}")
        if os.path.exists(local_filename):
            os.remove(local_filename)
        return False


def fetch():
    return feedparser.parse(RSS_FEED).entries


# ---------------------------------------------------
# MAIN FUNCTION (২৪ ঘণ্টার ডুপ্লিকেট ফিল্টারিং সহ)
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

        real_url, img_url = get_real_url_and_image(item.link)
        ai_summary = generate_ai_summary(item.title, real_url)
        message = build_news_message(item.title, ai_summary, real_url)

        # ইমেজ থাকলে তা ফাইল মেথডে পাঠানো হবে, ফেইল করলে ব্যাকআপ হিসেবে টেক্সট যাবে
        if img_url and img_url.startswith("http"):
            success = send_photo_as_file(img_url, message)
            if not success:
                send_text(message) # ইমেজ আপলোড ফেইল করলে শুধু টেক্সট পাঠাবে
        else:
            send_text(message)

        time.sleep(2)


if __name__ == "__main__":
    main()
