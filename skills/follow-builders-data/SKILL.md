---
name: follow-builders-data
version: 0.1.0
description: Minimal Follow Builders data source for AI Daily News. Fetches central Follow Builders feeds from GitHub raw URLs and normalizes tweets, podcasts, and blog posts for downstream summarization.
category: productivity
trigger_keywords: []
dependencies:
  - network access to raw.githubusercontent.com
---

# Follow Builders Data Skill

This skill is a small data adapter. It does not generate feeds, manage delivery, store local state, or use local bundled feed JSON as fallback.

## Data Source

Official data comes from remote GitHub raw feeds:

```text
https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json
https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json
https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json
```

## Interface

```python
from follow_builders_data import fetch

data = fetch()
```

Returns:

```python
{
    "status": "ok",
    "generatedAt": "...",
    "x": [...],
    "podcasts": [...],
    "blogs": [...],
    "stats": {...},
    "errors": [...]
}
```

If the remote feeds cannot be fetched, `fetch()` returns `None`.
