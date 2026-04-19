import feedparser
import requests
import re
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# ─── CONFIG ───────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY      = os.environ.get("OPENROUTER_API_KEY",      "your_openrouter_key")
TELEGRAM_BOT_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN",      "your_telegram_bot_token")
TELEGRAM_CHAT_ID        = os.environ.get("TELEGRAM_CHAT_ID",        "your_chat_id")
VOICEMONKEY_API_TOKEN   = os.environ.get("VOICEMONKEY_API_TOKEN",   "your_api_token")
VOICEMONKEY_MONKEY_NAME = os.environ.get("VOICEMONKEY_MONKEY_NAME", "your_monkey_name")

# ─── RSS FEEDS ────────────────────────────────────────────────────────────────
FEEDS = {
    "Reuters":        "https://feeds.reuters.com/reuters/topNews",
    "BBC World":      "http://feeds.bbci.co.uk/news/world/rss.xml",
    "The Hindu":      "https://www.thehindu.com/news/national/feeder/default.rss",
    "NDTV":           "https://feeds.feedburner.com/ndtvnews-top-stories",
    "Al Jazeera":     "https://www.aljazeera.com/xml/rss/all.xml",
    "Economic Times": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
}

ARTICLES_PER_FEED = 3

# ─── FETCH HEADLINES ──────────────────────────────────────────────────────────
def fetch_headlines():
    all_headlines = {}
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            entries = feed.entries[:ARTICLES_PER_FEED]
            headlines = []
            for e in entries:
                title   = e.get("title", "").strip()
                summary = e.get("summary", e.get("description", "")).strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                headlines.append(f"- {title}: {summary}")
            all_headlines[source] = headlines
            print(f"Fetched: {source}")
        except Exception as ex:
            print(f"Failed: {source} - {ex}")
    return all_headlines

# ─── CALL OPENROUTER ──────────────────────────────────────────────────────────
def call_openrouter(prompt):
    for model in [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ]:
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                },
                timeout=30
            )
            if r.status_code == 200:
                print(f"OpenRouter OK ({model})")
                return r.json()["choices"][0]["message"]["content"]
            else:
                print(f"Model failed ({r.status_code}): {model}")
        except Exception as ex:
            print(f"Model error: {model} - {ex}")
    return None

# ─── BUILD RAW TEXT ───────────────────────────────────────────────────────────
def build_raw_text(headlines_dict):
    lines = []
    for source, items in headlines_dict.items():
        lines.append(f"\n[{source}]")
        lines.extend(items)
    return "\n".join(lines)

# ─── GENERATE TELEGRAM DIGEST ────────────────────────────────────────────────
def generate_telegram_digest(raw_text):
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y")
    prompt = f"""You are a sharp news briefing assistant. Below are today's top headlines from Indian and global sources.

Your job:
1. Group into 3-4 thematic sections (India, World, Economy, Tech)
2. Write 2-3 bullet points per section summarising key stories
3. End with a 2-line Big Picture - the most important thing happening today
4. Under 400 words total
5. Plain conversational English, no jargon

Headlines:
{raw_text}

Output:
DAILY DIGEST - {today}

[sections with emoji headers and bullet points]

Big Picture:
[2 lines]
"""
    return call_openrouter(prompt)

# ─── GENERATE ALEXA SUMMARY ───────────────────────────────────────────────────
def generate_alexa_summary(raw_text):
    prompt = f"""You are a radio news anchor writing a script for Alexa to read aloud.

Rules:
- Start with: Good morning. Here is your news briefing for today.
- Cover 4 to 5 most important stories across India and the world
- Natural spoken English only - no bullet points, no symbols, no dashes
- 1 to 2 sentences per story
- End with: That is your morning briefing. Have a great day.
- Strict limit: 70 to 90 words total.

Headlines:
{raw_text}
"""
    return call_openrouter(prompt)

# ─── SEND TO TELEGRAM ─────────────────────────────────────────────────────────
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
        })
        if r.status_code == 200:
            print("Telegram: sent")
        else:
            print(f"Telegram failed: {r.text}")

# ─── SEND TO ALEXA ────────────────────────────────────────────────────────────
def send_alexa(spoken_text):
    clean = re.sub(r"[*_`#•\-]", "", spoken_text).strip()
    r = requests.get(
        "https://api.voicemonkey.io/trigger",
        params={
            "access_token": VOICEMONKEY_API_TOKEN,
            "monkey":       VOICEMONKEY_MONKEY_NAME,
            "announcement": clean,
        }
    )
    if r.status_code == 200:
        print("Alexa: triggered")
    else:
        print(f"VoiceMonkey failed: {r.status_code} - {r.text}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[{datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y %H:%M')} IST] Starting...")

    headlines = fetch_headlines()
    if not headlines:
        print("No headlines. Exiting.")
        exit(1)

    raw_text = build_raw_text(headlines)

    print("Generating Telegram digest...")
    telegram_digest = generate_telegram_digest(raw_text)

    print("Generating Alexa summary...")
    alexa_summary = generate_alexa_summary(raw_text)

    if telegram_digest:
        print(telegram_digest)
        send_telegram(telegram_digest)
    else:
        print("Failed to generate Telegram digest")

    if alexa_summary:
        print(alexa_summary)
        send_alexa(alexa_summary)
    else:
        print("Failed to generate Alexa summary")

    print("[Done]")
    
