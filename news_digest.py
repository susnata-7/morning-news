import feedparser
import requests
import re
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# ─── CONFIG ───────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

TELEGRAM_BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID        = os.getenv("TELEGRAM_CHAT_ID")
VOICEMONKEY_API_TOKEN   = os.getenv("VOICEMONKEY_API_TOKEN")
VOICEMONKEY_MONKEY_NAME = os.getenv("VOICEMONKEY_MONKEY_NAME")

# Fail fast
required = {
    "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    "VOICEMONKEY_API_TOKEN": VOICEMONKEY_API_TOKEN,
    "VOICEMONKEY_MONKEY_NAME": VOICEMONKEY_MONKEY_NAME,
}

missing = [k for k, v in required.items() if not v]
if missing:
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

OPENROUTER_API_KEY = OPENROUTER_API_KEY.strip()

print("Environment check:")
print("OpenRouter:", bool(OPENROUTER_API_KEY))
print("Telegram:", bool(TELEGRAM_BOT_TOKEN))

# ─── RSS FEEDS ────────────────────────────────────────────────────────────────
FEEDS = {
    "Reuters":        "https://www.reutersagency.com/feed/?best-topics=top-news",
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
            resp = requests.get(url, timeout=10)
            feed = feedparser.parse(resp.content)

            entries = feed.entries[:ARTICLES_PER_FEED]

            headlines = []
            for e in entries:
                title = e.get("title", "").strip()
                summary = e.get("summary", e.get("description", "")).strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]

                if title:
                    headlines.append(f"- {title}: {summary}")

            if headlines:
                all_headlines[source] = headlines
                print(f"Fetched: {source}")

        except Exception as ex:
            print(f"Failed: {source} - {ex}")

    return all_headlines

# ─── AI CALL (OPENROUTER) ─────────────────────────────────────────────────────
def call_ai(prompt):
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=30
        )

        if r.status_code == 200:
            print("OpenRouter OK")
            return r.json()["choices"][0]["message"]["content"]
        else:
            print(f"OpenRouter failed ({r.status_code}): {r.text}")
            return None

    except Exception as e:
        print(f"OpenRouter exception: {e}")
        return None

# ─── BUILD TEXT ───────────────────────────────────────────────────────────────
def build_raw_text(headlines_dict):
    lines = []

    for source, items in headlines_dict.items():
        lines.append(f"\n[{source}]")
        lines.extend(items)

    text = "\n".join(lines)

    # Deduplicate
    seen = set()
    unique = []
    for line in text.split("\n"):
        key = line[:80]
        if key not in seen:
            seen.add(key)
            unique.append(line)

    return "\n".join(unique)[:12000]

# ─── GENERATORS ───────────────────────────────────────────────────────────────
def generate_telegram_digest(raw_text):
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y")

    prompt = f"""You are a news assistant.

- Group into 3–4 sections
- 2–3 bullet points per section
- Under 400 words
- Conversational tone
- Use *bold* headers

Headlines:
{raw_text}

Output:

DAILY DIGEST - {today}
"""

    return call_ai(prompt)

def generate_alexa_summary(raw_text):
    prompt = f"""Write a spoken news briefing.

- Start: Good morning. Here is your news briefing for today.
- 4–5 stories
- 70–90 words
- Natural speech
- End: That is your morning briefing. Have a great day.

Headlines:
{raw_text}
"""

    text = call_ai(prompt)

    if text:
        words = text.split()
        text = " ".join(words[:90])

    return text

# ─── TELEGRAM ────────────────────────────────────────────────────────────────
def send_telegram(text):
    if not text or not text.strip():
        print("Empty Telegram message")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    for chunk in chunks:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown"
        })

        if r.status_code == 200:
            print("Telegram: sent")
        else:
            print(f"Telegram failed: {r.text}")

# ─── ALEXA ───────────────────────────────────────────────────────────────────
print("VM TOKEN:", repr(VOICEMONKEY_API_TOKEN))
print("VM MONKEY:", repr(VOICEMONKEY_MONKEY_NAME))

def send_alexa(text):
    if not text or not text.strip():
        print("Empty Alexa text")
        return

    clean = re.sub(r"[*_`#•\-]", "", text).strip()

    r = requests.get(
        "https://api.voicemonkey.io/trigger",
        params={
            "access_token": VOICEMONKEY_API_TOKEN,
            "monkey": VOICEMONKEY_MONKEY_NAME,
            "announcement": clean,
        }
    )

    if r.status_code == 200:
        print("Alexa: triggered")
    else:
        print(f"VoiceMonkey failed: {r.status_code} - {r.text}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    print(f"[{now.strftime('%d %b %Y %H:%M')} IST] Starting...")

    headlines = fetch_headlines()
    if not headlines:
        raise RuntimeError("No headlines fetched")

    raw_text = build_raw_text(headlines)

    print("Generating Telegram digest...")
    telegram_digest = generate_telegram_digest(raw_text)

    print("Generating Alexa summary...")
    alexa_summary = generate_alexa_summary(raw_text)

    if telegram_digest:
        send_telegram(telegram_digest)
    else:
        print("Telegram generation failed")

    if alexa_summary:
        send_alexa(alexa_summary)
    else:
        print("Alexa generation failed")

    print("[Done]")
