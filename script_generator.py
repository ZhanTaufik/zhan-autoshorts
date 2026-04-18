"""
script_generator.py – Uses Claude to turn a Reddit post into a Short-ready script.

Returns a dict with:
  - voiceover   : clean narration text (~60s)
  - title       : YouTube title (≤100 chars, hook-first)
  - description : YouTube description with hashtags
  - tags        : list of keyword strings
  - subtitles   : list of {"text": str, "duration": float} chunks for on-screen text
"""

import json
import logging
import re
import anthropic
from config import Config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a viral YouTube Shorts scriptwriter.
Your job is to transform Reddit posts into engaging, fast-paced Short scripts.

Rules:
- Voiceover must be 150-180 words (approx 55-65 seconds at normal speaking pace).
- Open with a strong hook in the first sentence — make viewers stop scrolling.
- Write in a conversational, energetic tone. No jargon.
- Title must be click-worthy, ≤100 characters, NO ALL CAPS.
- Description: 2-3 sentences + 5 relevant hashtags on separate lines.
- Tags: 10–15 relevant single-word or short-phrase keywords.
- Subtitles: break the voiceover into short display phrases (3–7 words each),
  estimate each phrase's duration in seconds (based on natural speech pace).

Respond ONLY with a valid JSON object — no markdown, no commentary:
{
  "voiceover": "...",
  "title": "...",
  "description": "...",
  "tags": ["...", "..."],
  "subtitles": [
    {"text": "...", "duration": 2.5},
    ...
  ]
}"""


class ScriptGenerator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

    def generate(self, post: dict) -> dict:
        """
        Takes a Reddit post dict and returns a script dict.
        """
        user_message = self._build_user_message(post)

        log.debug("Sending to Claude: %s…", user_message[:200])

        message = self.client.messages.create(
            model=self.cfg.CLAUDE_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = message.content[0].text.strip()
        log.debug("Claude raw response: %s…", raw[:200])

        script = self._parse_response(raw)
        return script

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_user_message(self, post: dict) -> str:
        parts = [
            f"SUBREDDIT: r/{post['subreddit']}",
            f"TITLE: {post['title']}",
            f"BODY:\n{post['body'][:1500]}",
        ]
        if post.get("top_comment"):
            parts.append(f"TOP COMMENT:\n{post['top_comment'][:300]}")

        return "\n\n".join(parts)

    def _parse_response(self, raw: str) -> dict:
        """Parse Claude's JSON response, with a fallback for wrapped output."""
        # Strip potential ```json ... ``` fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            log.error("JSON parse failed: %s\nRaw: %s", e, raw[:500])
            # Return a safe fallback
            data = {
                "voiceover": raw[:900],
                "title": "You won't believe this Reddit story",
                "description": "Mind-blowing story from Reddit!\n#reddit #shorts #story #viral #fyp",
                "tags": ["reddit", "shorts", "viral", "story", "trending"],
                "subtitles": [{"text": raw[:50], "duration": 3.0}],
            }

        # Validate / sanitise
        data["title"] = data.get("title", "")[:100]
        data["tags"] = data.get("tags", [])[:15]
        data["voiceover"] = data.get("voiceover", "")[:self.cfg.MAX_VOICEOVER_CHARS]
        data.setdefault("subtitles", [])

        return data
