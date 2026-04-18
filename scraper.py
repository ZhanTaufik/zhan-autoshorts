"""
scraper.py – Fetches high-performing Reddit posts to turn into Shorts.
"""

import logging
import re
import praw
from config import Config

log = logging.getLogger(__name__)


class RedditScraper:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.reddit = praw.Reddit(
            client_id=cfg.REDDIT_CLIENT_ID,
            client_secret=cfg.REDDIT_CLIENT_SECRET,
            user_agent=cfg.REDDIT_USER_AGENT,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def fetch_posts(
        self,
        subreddits: list[str],
        min_score: int = 1000,
        limit: int = 25,
        sort: str = "hot",           # hot | top | rising
        time_filter: str = "day",    # hour | day | week (for 'top')
    ) -> list[dict]:
        """
        Returns a list of post dicts sorted by score (descending).
        Each dict contains: id, title, body, url, score, subreddit, comments.
        """
        posts = []

        for sub_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(sub_name)

                if sort == "hot":
                    submissions = subreddit.hot(limit=limit)
                elif sort == "top":
                    submissions = subreddit.top(time_filter=time_filter, limit=limit)
                elif sort == "rising":
                    submissions = subreddit.rising(limit=limit)
                else:
                    submissions = subreddit.hot(limit=limit)

                for sub in submissions:
                    if sub.stickied:
                        continue
                    if sub.score < min_score:
                        continue
                    if sub.over_18:
                        continue   # skip NSFW

                    body = self._extract_body(sub)
                    if not body:
                        continue

                    posts.append({
                        "id": sub.id,
                        "title": sub.title,
                        "body": body,
                        "url": f"https://reddit.com{sub.permalink}",
                        "score": sub.score,
                        "subreddit": sub_name,
                        "comments": sub.num_comments,
                        "top_comment": self._get_top_comment(sub),
                    })

            except Exception as e:
                log.warning("Failed to fetch r/%s: %s", sub_name, e)

        # Sort by score descending
        posts.sort(key=lambda p: p["score"], reverse=True)
        return posts

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _extract_body(self, submission) -> str:
        """
        Returns cleaned post text. For link-only posts we use the title.
        For text posts we use selftext. Skips very short / deleted posts.
        """
        if submission.is_self and submission.selftext:
            text = submission.selftext.strip()
            text = self._clean_text(text)
            if len(text) < 50:
                return ""
            return text[:3000]   # cap at 3000 chars; Claude will trim further

        # Link post – title is usually enough for a Short
        return submission.title

    def _get_top_comment(self, submission) -> str:
        """Returns the top comment body (for context)."""
        try:
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:5]:
                text = comment.body.strip()
                if len(text) > 20 and "[deleted]" not in text:
                    return self._clean_text(text)[:500]
        except Exception:
            pass
        return ""

    @staticmethod
    def _clean_text(text: str) -> str:
        """Strip markdown, links, and extra whitespace."""
        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)
        # Remove markdown images/links
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Remove markdown formatting
        text = re.sub(r"[*_~`#>]+", "", text)
        # Collapse whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
