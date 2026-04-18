# 🎬 YouTube Shorts Automation Bot

Automatically turns viral Reddit posts into YouTube Shorts.

```
Reddit post → Claude script → TTS voiceover → Video → YouTube
```

---

## ✨ Features

| Step | What it does |
|------|-------------|
| **Scrape** | Finds trending posts from configurable subreddits |
| **Script** | Claude AI rewrites the post as a punchy ~60s voiceover |
| **TTS** | Converts script to speech (gTTS free / OpenAI / ElevenLabs) |
| **Video** | moviepy composites background video + animated subtitles |
| **Upload** | Posts directly to YouTube via the Data API v3 |

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone <repo>
cd yt_shorts_bot
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

You also need **ffmpeg** on your PATH:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: download from https://ffmpeg.org/download.html

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` (free at reddit.com/prefs/apps)
- `ANTHROPIC_API_KEY` (console.anthropic.com)
- TTS settings (gTTS works with no key)
- Background video source (drop an MP4 in `assets/` or set `PEXELS_API_KEY`)

### 3. Set up YouTube OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **YouTube Data API v3**
3. Create **OAuth 2.0 credentials** → Desktop App
4. Download JSON → save as `client_secrets.json` in the project folder
5. First run will open a browser for one-time authorization

### 4. Add a background video

Drop any portrait-orientation (9:16) MP4 into the `assets/` folder.

Or set `PEXELS_API_KEY` in `.env` to auto-download one from Pexels.

> **Tip**: Minecraft parkour, subway surfers, or satisfying clips perform best.

---

## 🎮 Usage

```bash
# Make 1 Short (recommended for testing first)
python main.py

# Skip YouTube upload (dry run)
python main.py --dry-run

# Make 3 Shorts in one run
python main.py --count 3
```

---

## 🗂 Project Structure

```
yt_shorts_bot/
├── main.py               # Pipeline orchestrator
├── config.py             # All settings (reads from .env)
├── scraper.py            # Reddit post fetcher (PRAW)
├── script_generator.py   # Claude AI script writer
├── tts.py                # Text-to-speech engine
├── video_editor.py       # moviepy video compositor
├── youtube_uploader.py   # YouTube Data API v3 uploader
├── requirements.txt
├── .env.example          # ← copy to .env
├── client_secrets.json   # ← download from Google Cloud (gitignored)
├── youtube_token.json    # ← auto-created after first auth (gitignored)
├── processed.json        # ← auto-created, tracks uploaded posts
├── assets/               # ← put your background MP4s here
├── temp/                 # intermediate audio files
└── output/               # final MP4s
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SUBREDDITS` | AskReddit,tifu,todayilearned,LifeProTips,NoStupidQuestions | Comma-separated list |
| `MIN_SCORE` | 1000 | Minimum upvotes to consider |
| `FETCH_LIMIT` | 25 | Posts to inspect per run |
| `TTS_ENGINE` | gtts | `gtts` / `openai` / `elevenlabs` |
| `OPENAI_TTS_VOICE` | onyx | alloy / echo / fable / onyx / nova / shimmer |
| `BACKGROUND_VIDEO` | *(auto)* | Path to a specific MP4 |
| `PEXELS_API_KEY` | *(empty)* | For auto-downloading backgrounds |
| `YOUTUBE_PRIVACY` | public | `public` / `unlisted` / `private` |
| `SUBTITLE_FONT` | Arial-Bold | Must be installed on your system |

---

## 🔁 Automation (run daily)

### macOS / Linux (cron)
```bash
# Run every day at 9 AM
0 9 * * * cd /path/to/yt_shorts_bot && .venv/bin/python main.py
```

### Windows (Task Scheduler)
Create a task that runs:
```
C:\path\to\.venv\Scripts\python.exe C:\path\to\yt_shorts_bot\main.py
```

---

## 💡 Tips for Better Performance

1. **TTS quality**: OpenAI `onyx` voice sounds the most natural. ElevenLabs is best but costs money.
2. **Background videos**: Minecraft parkour, subway surfers, and satisfying slime content consistently outperform nature clips.
3. **Subreddits**: `tifu` and `AskReddit` tend to produce the most engaging stories.
4. **Posting time**: Schedule for 7–9 AM or 6–8 PM in your target audience's timezone.
5. **Dry run first**: Always test with `--dry-run` before enabling uploads.

---

## ⚠️ Disclaimer

- Always respect Reddit's API Terms of Service.
- Always attribute content appropriately in video descriptions.
- YouTube's policies prohibit spam — post no more than 1-2 Shorts per day.
- Verify your content doesn't violate copyright before publishing.
