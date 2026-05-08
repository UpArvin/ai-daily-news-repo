#!/usr/bin/env python3
"""
ph-review-generator skill — Product Hunt 数据获取 + AI 点评生成
依赖 minimax-tasks skill 提供 MiniMax 调用
"""
import json
import re
import sys
from pathlib import Path

# ===== llm-tasks 路径注入 =====

_LLM_TASKS_PATH = Path(__file__).parent.parent.parent / "llm-tasks" / "scripts"
sys.path.insert(0, str(_LLM_TASKS_PATH))
import llm_tasks

# ===== 路径配置 =====

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
CONFIG_PATH = Path.home() / ".hermes" / "config" / "ph-review-generator.json"
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def _load_json(path):
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_config():
    """Load user config, falling back to bundled defaults."""
    cfg = _load_json(DEFAULT_CONFIG_PATH)
    cfg.update(_load_json(CONFIG_PATH))
    return cfg

# ===== HTML 清理 =====

def _clean_html_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    for entity in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                   ('&quot;', '"'), ('&#39;', "'"), ('&nbsp;', ' ')]:
        text = text.replace(*entity)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ===== Product Hunt 数据获取 =====

def get_product_hunt(cfg=None):
    """
    从 Product Hunt RSS 获取热门产品。

    Args:
        cfg: dict，包含 category、days_ago、limit

    Returns:
        list[dict]，每项包含 title、description、url
    """
    if cfg is None:
        cfg = {}
    import urllib.request
    from html.parser import HTMLParser

    class PHEntry(HTMLParser):
        def __init__(self):
            super().__init__()
            self.entries = []
            self.current = None
            self.in_title = False
            self.in_content = False
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "entry":
                self.current = {"title": "", "link": "", "content": ""}
            elif tag == "title" and self.current:
                self.in_title = True
            elif tag == "link" and self.current:
                if attrs.get("rel") == "alternate":
                    self.current["link"] = attrs.get("href", "")
            elif tag == "content" and self.current:
                self.in_content = True
        def handle_data(self, data):
            if self.in_title and self.current:
                self.current["title"] += data.strip()
            elif self.in_content and self.current:
                self.current["content"] += data.strip()
        def handle_endtag(self, tag):
            if tag == "title":
                self.in_title = False
            elif tag == "content":
                self.in_content = False
            elif tag == "entry" and self.current:
                self.entries.append(self.current)
                self.current = None

    try:
        url = "https://www.producthunt.com/feed"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode()

        parser = PHEntry()
        parser.feed(content)

        limit = cfg.get("limit", 5)
        results = []
        for entry in parser.entries[:limit]:
            raw = entry["content"].strip()
            clean = _clean_html_text(raw)
            clean = re.sub(r'\s*Discussion\s*\|\s*Link\s*$', '', clean)
            results.append({
                "title": entry["title"],
                "description": clean[:300],
                "url": entry["link"]
            })
        return results
    except Exception as e:
        print(f"[PH] 抓取失败: {e}", file=sys.stderr)
        return []

# ===== AI 点评生成 =====

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

def _load_prompt(name):
    path = PROMPTS_DIR / f"{name}.md"
    if path.exists():
        with open(path) as f:
            return f.read()
    return None


def _fallback_review(item):
    title = item.get("title", "这个产品")
    desc = _clean_html_text(item.get("description", "") or "")
    if desc:
        short_desc = desc[:80].rstrip("，。,. ")
        translated = f"{title}：{short_desc}"
        review = f"{title} 主要围绕「{short_desc}」场景展开，建议重点关注实际可用性、集成成本和与现有工作流的契合度。"
    else:
        translated = title
        review = f"{title} 的公开描述信息较少，建议先查看官网或演示，重点确认核心场景、集成成本和真实可用性。"
    return {
        "translated": translated,
        "review": review,
        "review_source": "fallback",
    }


def _normalize_review_result(raw_item, source="llm"):
    if isinstance(raw_item, list) and len(raw_item) >= 2:
        translated, review = raw_item[0], raw_item[1]
    elif isinstance(raw_item, list) and len(raw_item) == 1:
        translated, review = raw_item[0], ""
    elif isinstance(raw_item, dict):
        translated = raw_item.get("translated", "")
        review = raw_item.get("review", "")
    else:
        return None
    return {
        "translated": str(translated or "").strip(),
        "review": str(review or "").strip(),
        "review_source": source,
    }


def _merge_with_fallback(items, reviewed):
    merged = []
    for i, item in enumerate(items):
        normalized = None
        if reviewed and i < len(reviewed):
            normalized = _normalize_review_result(reviewed[i])
        if normalized and (normalized.get("translated") or normalized.get("review")):
            fallback = _fallback_review(item)
            merged.append({
                "translated": normalized.get("translated") or fallback["translated"],
                "review": normalized.get("review") or fallback["review"],
                "review_source": "llm" if normalized.get("review") else "fallback",
            })
        else:
            merged.append(_fallback_review(item))
    return merged


def _single_prompt(item):
    title = item.get("title", "")
    desc = item.get("description", "")
    return f"""你是一个严谨的科技产品点评师。请为以下 Product Hunt 产品生成精准中文翻译和专业简评。

要求：
1. 返回严格 JSON 对象，不要 markdown code fences。
2. 字段必须是 translated 和 review。
3. translated：产品名和描述的精准中文表达，产品名可保留英文。
4. review：1-2 句，70-130 个中文字，说明具体场景、一个看点或风险；不要营销话术。

产品名称：{title}
产品描述：{desc}

返回格式：
{{"translated":"...","review":"..."}}
"""


def _review_single(item, timeout=None):
    raw = llm_tasks.chat(_single_prompt(item), timeout=timeout)
    if raw is None:
        return None
    parsed = llm_tasks.parse_json(raw, list_mode=False)
    normalized = _normalize_review_result(parsed) if parsed is not None else None
    if normalized and (normalized.get("translated") or normalized.get("review")):
        fallback = _fallback_review(item)
        return {
            "translated": normalized.get("translated") or fallback["translated"],
            "review": normalized.get("review") or fallback["review"],
            "review_source": "llm" if normalized.get("review") else "fallback",
        }
    return None


def ph_ai_review(items, timeout=None):
    """
    为 Product Hunt 产品生成翻译+AI 点评。

    Args:
        items: list[dict]，每项需包含 title、description
        model: str，默认 MiniMax-M2.7
        timeout: int，默认 180s

    Returns:
        list[dict]，每项包含 {"translated": ..., "review": ..., "review_source": "llm|fallback"}
        批量失败时会逐条补救，单条仍失败时返回本地 fallback。
    """
    if not items:
        return []

    prompt_template = _load_prompt("ph-review")
    if not prompt_template:
        print("[ph-review] prompt 模板不存在: prompts/ph-review.md", file=sys.stderr)
        return [_fallback_review(item) for item in items]

    count = len(items)
    items_text = _render_items(items, {"title": "名称", "description": "描述"})
    full_prompt = prompt_template.replace("{count}", str(count)).replace("{items_text}", items_text)

    # llm_tasks.chat() 内部从 .env 配置读取 provider 和 model，不在此传 model
    raw = llm_tasks.chat(full_prompt, timeout=timeout)
    if raw is not None:
        result = llm_tasks.parse_json(raw, expected_count=count, list_mode=True)
        if result is not None:
            merged = _merge_with_fallback(items, result)
            if any(r.get("review_source") == "llm" for r in merged):
                return merged
            print("[ph-review] 批量结果无有效点评，改为逐条补救", file=sys.stderr)
        else:
            print("[ph-review] 批量 JSON 解析失败，改为逐条补救", file=sys.stderr)
    else:
        print("[ph-review] 批量 LLM 调用失败，改为逐条补救", file=sys.stderr)

    reviewed = []
    for i, item in enumerate(items, 1):
        single = _review_single(item, timeout=timeout)
        if single:
            reviewed.append(single)
        else:
            print(f"[ph-review] 单条点评失败，使用本地兜底: {i}/{len(items)} {item.get('title', '')}", file=sys.stderr)
            reviewed.append(_fallback_review(item))
    return reviewed

# ===== 入口函数 =====

def review(cfg=None):
    """
    获取 Product Hunt 数据并生成 AI 翻译+点评。

    Args:
        cfg: dict，可选，包含 category、days_ago、limit

    Returns:
        list[dict]，每项包含 title、description、url、translated、review
        失败返回 None
    """
    items = get_product_hunt(cfg)
    if not items:
        return None
    reviewed = ph_ai_review(items)
    if reviewed is None:
        return None
    # 合并
    for i, item in enumerate(items):
        if i < len(reviewed):
            item["translated"] = reviewed[i].get("translated", item.get("description", ""))
            item["review"] = reviewed[i].get("review", "")
    return items

def _print_human(items):
    print("ph-review-generator skill")
    print(f"获取到 {len(items)} 条产品")
    for item in items:
        translated = item.get("translated")
        review_text = item.get("review")
        print(f"  - {item['title']}: {(translated or item.get('description', ''))[:80]}...")
        if review_text:
            print(f"    点评: {review_text[:120]}...")


def main():
    """Minimal standalone smoke entrypoint."""
    cfg = load_config()
    items = get_product_hunt(cfg) or []
    _print_human(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
