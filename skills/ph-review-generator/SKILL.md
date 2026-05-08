---
name: ph-review-generator
version: 0.1.0
description: Product Hunt 数据获取 + AI 翻译点评生成。从 PH RSS 抓取产品，通过 llm-tasks 生成精准翻译和专业简评。
category: productivity
trigger_keywords: []
dependencies:
  - llm-tasks skill
  - python3
---

# ph-review-generator Skill

Product Hunt 热门产品数据获取 + AI 翻译与专业简评生成。批量点评失败时会逐条补救，单条仍失败时使用本地兜底短评。

## 接口

```python
from ph_review import get_product_hunt, ph_ai_review, review

# 方式1：获取数据（不含 AI 点评）
items = get_product_hunt(cfg={"limit": 5})

# 方式2：获取数据 + 生成 AI 点评
items = review(cfg={"limit": 5})
# 返回: [{"title": ..., "description": ..., "url": ..., "translated": ..., "review": ..., "review_source": "llm|fallback"}, ...]
```

## 配置

`~/.hermes/config/ph-review-generator.json`：

```json
{
  "category": "ai",
  "days_ago": 1,
  "limit": 5,
  "timeout": 180
}
```

LLM provider 由 `llm-tasks` 的 `.env` 统一决定。
