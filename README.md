# Brandon's Job Bot 🤖

Always-on Telegram bot that scrapes Indeed, manages your job tracker,
generates tailored application packets, and sends you apply links —
all controlled via Telegram commands.

---

## Commands

| Command | What it does |
|---|---|
| `/run` | Search with current criteria |
| `/run director 100000 Sayreville NJ` | Search with updated criteria |
| `/review` | See next 5 pending jobs |
| `/review all` | See all pending jobs |
| `/review 3` | See job #3 |
| `/yes 1` | Approve job #1 → generates packet + sends apply link |
| `/no 2` | Reject job #2 forever (never shows again) |
| `/wait 3` | Hold job #3 for next review round |
| `/status` | Full tracker summary |
| `/stop` | Emergency kill switch |

---

## Deployment — Railway (5 minutes)

### Step 1 — Get your API keys

**RapidAPI (JSearch — free tier):**
1. Go to [rapidapi.com](https://rapidapi.com)
2. Search for **JSearch** by letscrape
3. Subscribe to the free tier (500 searches/month)
4. Copy your RapidAPI key from the dashboard

**Anthropic API:**
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Copy it

### Step 2 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial bot deploy"
git remote add origin https://github.com/YOUR_USERNAME/brandon-job-bot.git
git push -u origin main
```

### Step 3 — Deploy on Railway

1. Go to [railway.com](https://railway.com) → New Project → Deploy from GitHub
2. Select your `brandon-job-bot` repo
3. Click **Add Variables** and set ALL of these:

```
TELEGRAM_BOT_TOKEN  = 8642446478:AAHwoPD8OcEOX_g0B4z0QppZ1nqTHT9pxpw
ALLOWED_CHAT_ID     = 5637852861
ANTHROPIC_API_KEY   = [your key from console.anthropic.com]
RAPID_API_KEY       = [your key from rapidapi.com]
DB_PATH             = /data/jobs.db
```

4. **Add a Volume** (so the database persists across deploys):
   - In Railway dashboard → your service → **Volumes** tab
   - Add volume → Mount path: `/data`

5. **Disable Serverless mode** (critical for polling bots):
   - Settings → Deploy → make sure "Serverless" is OFF

6. Deploy — Railway will install dependencies and start the bot automatically

### Step 4 — Test it

Message your bot `/start` — you should get the help menu.
Then try `/run` to kick off your first search.

---

## Architecture

```
brandon-job-bot/
├── bot.py                  ← Entry point, command registration
├── core/
│   ├── state.py            ← SQLite DB, all read/write ops
│   ├── scraper.py          ← Indeed search via RapidAPI JSearch
│   ├── generator.py        ← Anthropic API cover letter + bullets
│   └── notifier.py         ← Telegram outbound messages
├── commands/
│   ├── run_cmd.py          ← /run
│   ├── stop_cmd.py         ← /stop
│   ├── review_cmd.py       ← /review
│   ├── yes_cmd.py          ← /yes
│   ├── no_wait_cmd.py      ← /no + /wait
│   ├── status_cmd.py       ← /status
│   └── help_cmd.py         ← /help
├── data/
│   └── jobs.db             ← SQLite (persisted via Railway Volume)
├── requirements.txt
├── railway.json
└── .env.example
```

---

## Workflow

```
/run                    → scrapes Indeed, adds new jobs to DB
/review                 → sends you short summaries, 5 at a time
/yes 1                  → generates cover letter + bullets → sends APPLY NOW button
/no 2                   → rejects forever, never scrapes again
/wait 3                 → holds for next review round
[tap APPLY NOW]         → opens pre-filled application
[submit on their site]  → you're applied!
/status                 → see full pipeline counts
```

---

## Monthly Cost

| Item | Cost |
|---|---|
| Railway Hobby plan | ~$3–5/month |
| RapidAPI JSearch (free tier) | $0 (500 searches/month) |
| Anthropic API (cover letters) | ~$0.50–2/month depending on volume |
| **Total** | **~$5–7/month** |
