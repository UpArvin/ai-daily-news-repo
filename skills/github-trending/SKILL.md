---
name: github-trending
version: 0.2.0
description: GitHub Trending 抓取 + AI 点评生成。通过 OSSInsight API 获取 Trending，支持 GitHub API 补充详情，并生成专业简评。
category: productivity
trigger_keywords: []
dependencies:
  - llm-tasks skill
---

# GitHub Trending Skill

## 接口列表

### `get_trending(topics=None, period="past_24_hours", limit=10) -> list[dict]`
获取 GitHub Trending 列表（AI 相关过滤）。

返回字段：
```python
{
    "title": "owner/repo",
    "description": "项目描述",
    "stars": 1234,
    "language": "Python",
    "url": "https://github.com/owner/repo",
    "forks": 123,
}
```

### `gh_ai_review(items) -> list[str]`
通过 `llm-tasks` 为 GitHub 项目生成专业简评。

### `review(items) -> list[dict]`
获取数据 + 生成 AI 点评，返回每项含 `ai_review` 字段。

## 配置（~/.hermes/config/github-trending.json）

```json
{
  "ai_keywords": ["ai", "llm", "agent", ...],
  "trending": { "period": "past_24_hours", "limit": 5 }
}
```

## 数据源

- **Trending**：OSSInsight API（公开无需认证），ai_keywords 过滤 AI 相关项目
- **AI 点评**：`llm-tasks` 当前配置的 LLM provider
