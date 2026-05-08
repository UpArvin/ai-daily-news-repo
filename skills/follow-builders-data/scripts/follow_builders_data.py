#!/usr/bin/env python3
"""
follow-builders-data skill — fetch central Follow Builders feeds from GitHub.

This adapter intentionally does not read bundled local feed JSON files. The
central GitHub raw feed is the source of truth for ai-daily-news.
"""
import json
import sys
import urllib.request


BASE_URL = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main"
FEED_URLS = {
    "x": f"{BASE_URL}/feed-x.json",
    "podcasts": f"{BASE_URL}/feed-podcasts.json",
    "blogs": f"{BASE_URL}/feed-blogs.json",
}


def _fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _combine(feeds):
    feed_x = feeds.get("x") or {}
    feed_podcasts = feeds.get("podcasts") or {}
    feed_blogs = feeds.get("blogs") or {}
    x_items = feed_x.get("x", [])
    podcasts = feed_podcasts.get("podcasts", [])
    blogs = feed_blogs.get("blogs", [])
    if not x_items and not podcasts and not blogs:
        return None
    return {
        "status": "ok",
        "generatedAt": (
            feed_x.get("generatedAt")
            or feed_podcasts.get("generatedAt")
            or feed_blogs.get("generatedAt")
        ),
        "x": x_items,
        "podcasts": podcasts,
        "blogs": blogs,
        "stats": {
            "xBuilders": len(x_items),
            "totalTweets": sum(len(i.get("tweets", [])) for i in x_items),
            "podcastEpisodes": len(podcasts),
            "blogPosts": len(blogs),
        },
        "errors": [e for feed in feeds.values() for e in (feed.get("errors") or [])],
    }


def fetch(timeout=30):
    """Fetch and normalize remote Follow Builders feeds."""
    try:
        feeds = {key: _fetch_json(url, timeout=timeout) for key, url in FEED_URLS.items()}
        return _combine(feeds)
    except Exception as e:
        print(f"[follow-builders-data] fetch failed: {e}", file=sys.stderr)
        return None


def main():
    data = fetch()
    if not data:
        return 1
    print("follow-builders-data skill")
    print(f"generatedAt: {data.get('generatedAt')}")
    print(f"x builders: {data.get('stats', {}).get('xBuilders', 0)}")
    print(f"tweets: {data.get('stats', {}).get('totalTweets', 0)}")
    print(f"podcasts: {data.get('stats', {}).get('podcastEpisodes', 0)}")
    print(f"blogs: {data.get('stats', {}).get('blogPosts', 0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
