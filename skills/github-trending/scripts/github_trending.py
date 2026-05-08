#!/usr/bin/env python3
"""
github-trending skill — GitHub Trending 抓取
基于 OSSInsight API（公开），ai_keywords 过滤 AI 相关项目
"""
import json
import sys
import urllib.request
from pathlib import Path

# ===== llm-tasks 路径注入 =====

_LLM_TASKS_PATH = Path(__file__).parent.parent.parent / "llm-tasks" / "scripts"
sys.path.insert(0, str(_LLM_TASKS_PATH))
import llm_tasks

# ===== 配置路径 =====

CONFIG_PATH = Path.home() / ".hermes" / "config" / "github-trending.json"
_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

# ===== 配置加载 =====

def _get_default_config():
    """从 skill 目录的 config.json 加载默认配置"""
    if _DEFAULT_CONFIG_PATH.exists():
        with open(_DEFAULT_CONFIG_PATH) as f:
            return json.load(f)
    return {}

def _load_config():
    """从 ~/.hermes/config/github-trending.json 加载配置；若不存在则用 skill 目录的默认值"""
    if not CONFIG_PATH.exists():
        defaults = _get_default_config()
        if defaults:
            print(f"[github-trending] 未找到用户配置 ({CONFIG_PATH})，使用内置默认值")
            return defaults
        return {
            "ai_keywords": ["ai", "llm", "agent", "gpt", "deepseek", "openai",
                             "anthropic", "cursor", "langchain", "ollama", "vllm",
                             "embedding", "autonomous", "automation", "generative",
                             "qwen", "kimi", "minimax", "mistral", "gemini"],
            "trending": {"period": "past_24_hours", "limit": 5}
        }
    with open(CONFIG_PATH) as f:
        return json.load(f)

# ===== 辅助函数 =====

def _fetch_json(url, timeout=30):
    """通用 GET 请求，返回 parsed JSON 或 None"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[github-trending] fetch error: {url} — {e}", file=sys.stderr)
        return None

# ===== 核心函数 =====

def get_trending(topics=None, period="past_24_hours", limit=10):
    """
    获取 GitHub Trending 列表（AI 相关过滤）。

    Args:
        topics: list[str]，过滤关键词。
                为 None 时使用配置文件中的 ai_keywords。
        period: str，\"past_24_hours\" | \"past_7_days\" | \"past_30_days\"
        limit: int，最大返回条数

    Returns:
        list[dict]，每项包含：
        {
            "title": "owner/repo",
            "description": "项目描述",
            "stars": 1234,
            "language": "Python",
            "url": "https://github.com/owner/repo",
            "forks": 123,
            "extra": "123 forks"  # 兼容旧接口
        }
    """
    cfg = _load_config()
    keywords = topics if topics is not None else cfg.get("ai_keywords", [])

    # 从 OSSInsight 获取 Trending
    url = f"https://ossinsight.io/api/q/trending-repos?period={period}&language=All"
    data = _fetch_json(url)
    if not data:
        return []

    results = []
    raw_items = data.get("data", [])[:30]  # 多取一些用于过滤

    for item in raw_items:
        name = item.get("repo_name", "")
        desc = item.get("description") or "无描述"
        desc_lower = desc.lower()
        lang = item.get("language") or ""

        # 关键词过滤
        if keywords and not any(kw in name.lower() or kw in desc_lower for kw in keywords):
            continue

        results.append({
            "title": name,
            "description": desc,
            "stars": item.get("stars", 0),
            "language": lang,
            "url": f"https://github.com/{name}",
            "forks": item.get("forks", 0),
            "extra": f"{item.get('forks', 0)} forks"
        })

        if len(results) >= limit:
            break

    return results


def get_repo_details(repo_name):
    """
    单独查询某个仓库的详细信息。

    Args:
        repo_name: "owner/repo" 格式

    Returns:
        dict，仓库详情；失败返回 None
    """
    url = f"https://api.github.com/repos/{repo_name}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            gh_data = json.loads(resp.read().decode())
            return {
                "title": gh_data.get("full_name"),
                "description": gh_data.get("description"),
                "stars": gh_data.get("stargazers_count", 0),
                "forks": gh_data.get("forks_count", 0),
                "language": gh_data.get("language"),
                "topics": gh_data.get("topics", [])[:5],
                "url": gh_data.get("html_url"),
                "homepage": gh_data.get("homepage"),
            }
    except Exception as e:
        print(f"[github-trending] get_repo_details error: {e}", file=sys.stderr)
        return None


# ===== GH AI 点评 =====

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def _load_prompt(name):
    path = PROMPTS_DIR / f"{name}.md"
    if path.exists():
        with open(path) as f:
            return f.read()
    return None

def _render_items(items, field_specs=None):
    """将 items 列表渲染为可嵌入 prompt 的文本"""
    specs = field_specs or {}
    if not items:
        return ""
    lines = []
    for i, item in enumerate(items):
        if isinstance(item, dict):
            parts = [f"[{i}]"]
            for field, label in specs.items():
                val = item.get(field, "")
                if val:
                    parts.append(f"{label}：{val}" if label else str(val))
            lines.append(" | ".join(parts))
        else:
            lines.append(f"[{i}] {item}")
    return "\n".join(lines)

def gh_ai_review(items, timeout=None):
    """
    为 GitHub 项目生成深度 AI 点评。

    Args:
        items: list[dict]，每项需包含 title、description、stars、language
        model: str，默认 MiniMax-M2.7
        timeout: int，默认 180s

    Returns:
        list[str]，每项一条点评字符串
        失败返回 None
    """
    prompt_template = _load_prompt("gh-review")
    if not prompt_template:
        print("[gh-review] prompt 模板不存在: prompts/gh-review.md", file=sys.stderr)
        return None

    count = len(items)
    items_text = _render_items(items, {"title": "项目", "description": "描述", "stars": "⭐", "language": "语言"})
    full_prompt = prompt_template.replace("{count}", str(count)).replace("{items_text}", items_text)

    # llm_tasks.chat() 内部从 .env 配置读取 provider 和 model，不在此传 model
    raw = llm_tasks.chat(full_prompt, timeout=timeout)
    if raw is None:
        print("[gh-review] LLM 调用失败", file=sys.stderr)
        return None

    return llm_tasks.parse_json(raw, expected_count=count, list_mode=True)

def review(items):
    """
    为 GitHub 项目生成 AI 点评并合并到 items。

    Args:
        items: list[dict]

    Returns:
        list[dict]，每项包含 ai_review 字段
    """
    reviewed = gh_ai_review(items)
    if reviewed:
        for i, item in enumerate(items):
            if i < len(reviewed):
                item["ai_review"] = reviewed[i]
    return items

def _print_human(items):
    print("github-trending skill")
    print(f"返回 {len(items)} 条:")
    for r in items:
        print(f"  [{r.get('language') or '-'}] {r['title']} ⭐{r.get('stars', 0):,}")
        if r.get("ai_review"):
            print(f"    点评: {r['ai_review']}")


def main():
    """Minimal standalone smoke entrypoint."""
    cfg = _load_config()
    trending_cfg = cfg.get("trending", {})
    items = get_trending(
        period=trending_cfg.get("period", "past_24_hours"),
        limit=trending_cfg.get("limit", 5),
    )
    _print_human(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
