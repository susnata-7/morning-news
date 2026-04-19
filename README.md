# Daily News Digest Bot

Fetches Indian + global headlines every morning, summarises via OpenRouter AI,
and delivers a full digest to Telegram + a spoken briefing to Alexa.
Fully free to run.

---

## How it works

```
RSS Feeds (7 sources)
    → feedparser
    → OpenRouter (Gemini Flash free)
        → Full digest        → Telegram (read on phone)
        → 80-word summary    → VoiceMonkey → Alexa reads it out loud
```

---

## Setup Guide

### Step 1 — Telegram Bot

Get your Bot Token:
1. Open Telegram → search @BotFather
2. Send /newbot → give it any name
3. BotFather gives you a token like 7123456789:AAFxxx... → save this

Get your Chat ID:
1. Start a chat with your new bot → send it any message (e.g. "hi")
2. Open in browser (replace TOKEN): https://api.telegram.org/botTOKEN/getUpdates
3. Find "chat":{"id": 123456789} → that number is your Chat ID

---

### Step 2 — VoiceMonkey (Alexa)

1. Go to https://voicemonkey.io → Sign up (free)
2. Click "Add Alexa Account" → log in with your Amazon account
3. Go to Monkeys → Add Monkey → name it (e.g. morning-news) → save
4. Go to API Credentials → copy your Access Token and Secret Token
5. Test it by clicking "Test" next to your monkey — Alexa should speak

---

### Step 3 — OpenRouter

1. Sign up at https://openrouter.ai
2. Go to API Keys → create a new key (starts with sk-or-...)
3. Free tier is enough

---

### Step 4 — Deploy on Render (free, runs 24/7)

1. Push all files to a GitHub repo
2. Go to https://render.com → New → Background Worker
3. Connect your GitHub repo
4. Build Command:  pip install -r requirements.txt
5. Start Command:  python news_digest.py
6. Add these Environment Variables:

   OPENROUTER_API_KEY       → your OpenRouter key
   TELEGRAM_BOT_TOKEN       → your bot token
   TELEGRAM_CHAT_ID         → your chat ID number
   VOICEMONKEY_ACCESS_TOKEN → from VoiceMonkey API Credentials
   VOICEMONKEY_SECRET_TOKEN → from VoiceMonkey API Credentials
   VOICEMONKEY_MONKEY_NAME  → your monkey name (e.g. morning-news)

7. Deploy — runs 24/7, sends digest at 7 AM IST daily

---

### Run locally instead (alternative)

   pip install -r requirements.txt
   
   export OPENROUTER_API_KEY="sk-or-..."
   export TELEGRAM_BOT_TOKEN="7123..."
   export TELEGRAM_CHAT_ID="123456789"
   export VOICEMONKEY_ACCESS_TOKEN="..."
   export VOICEMONKEY_SECRET_TOKEN="..."
   export VOICEMONKEY_MONKEY_NAME="morning-news"
   
   python news_digest.py

---

## Customisation

Change send time        →  SEND_TIME = "07:00"
Add/remove sources      →  FEEDS dict
More articles per feed  →  ARTICLES_PER_FEED = 3
Change AI model         →  models list in call_openrouter()

Free models on OpenRouter:
  google/gemini-2.0-flash-exp:free       (best, used first)
  meta-llama/llama-3.3-70b-instruct:free (fallback)
  mistralai/mistral-7b-instruct:free     (lightweight)

---

## What you get each morning

Telegram — full digest grouped by theme (India / World / Economy / Tech),
bullet points + Big Picture summary. ~300-400 words.

Alexa — clean 80-word spoken briefing in radio anchor style.
Reads out automatically at 8 AM, no command needed.
