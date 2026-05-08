#!/usr/bin/env python3
"""
AI 每日资讯 v17 — 基于组件 skill 的重写版本
数据来源：GitHub Trending + Product Hunt + Follow Builders
AI 处理：llm-tasks provider
输出：本地 .md 文件（已配置飞书时额外写入飞书文档 + TTS 语音）
"""
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# ===== 路径配置 =====
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = Path(os.environ.get("AI_DAILY_NEWS_CONFIG", Path.home() / ".hermes" / "config" / "ai-daily-news-v2.json"))
_DEFAULT_CONFIG_PATH = SKILL_DIR / "config.json"
PROMPTS_DIR = SKILL_DIR / "prompts"
TEMPLATES_DIR = SKILL_DIR / "templates"
OUTPUT_DIR = None  # 初始化后从配置读取

# ===== 组件 skill 路径 =====

def _skill_path(name, *parts):
    """Resolve skill paths in Hermes flat installs or the local repo checkout."""
    candidates = [
        SKILL_DIR.parent / name,
        Path.home() / ".hermes" / "skills" / name,
    ]
    for base in candidates:
        path = base.joinpath(*parts)
        if path.exists():
            return path
    return candidates[0].joinpath(*parts)


FEISHU_DOC_PATH = _skill_path("feishu-doc", "scripts")
GITHUB_TRENDING_PATH = _skill_path("github-trending", "scripts")
PH_REVIEW_PATH = _skill_path("ph-review-generator", "scripts")
LLM_TASKS_PATH = _skill_path("llm-tasks", "scripts")
TTS_AUDIO_PATH = _skill_path("tts-audio", "scripts")
FOLLOW_BUILDERS_DATA_PATH = _skill_path("follow-builders-data", "scripts")

# ===== 加载组件 skill =====

sys.path.insert(0, str(FEISHU_DOC_PATH))
sys.path.insert(0, str(GITHUB_TRENDING_PATH))
sys.path.insert(0, str(PH_REVIEW_PATH))
sys.path.insert(0, str(LLM_TASKS_PATH))
sys.path.insert(0, str(TTS_AUDIO_PATH))
sys.path.insert(0, str(FOLLOW_BUILDERS_DATA_PATH))

import feishu_doc
import github_trending
import ph_review
import llm_tasks
import tts_audio
import follow_builders_data

# ===== 配置加载 =====

def load_config():
    """从 ~/.hermes/config/ai-daily-news-v2.json 加载配置；若不存在则用 skill 目录的默认值"""
    if not CONFIG_PATH.exists():
        defaults = _get_default_config()
        if defaults:
            print(f"[ai-daily-news-v2] 未找到用户配置 ({CONFIG_PATH})，使用内置默认值")
            return defaults
        raise FileNotFoundError(
            f"配置文件不存在：{CONFIG_PATH}\n"
            f"请在 ~/.hermes/config/ai-daily-news-v2.json 创建配置文件"
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _get_default_config():
    """从 skill 目录的 config.json 加载默认配置"""
    if _DEFAULT_CONFIG_PATH.exists():
        with open(_DEFAULT_CONFIG_PATH) as f:
            return json.load(f)
    return {}

def get_output_dir(cfg):
    """获取输出目录"""
    d = os.environ.get("AI_DAILY_NEWS_OUTPUT_DIR") or cfg.get("output", {}).get("dir", "~/.hermes/data/ai-daily-news-v2/")
    return Path(os.path.expanduser(d))

def get_date_str():
    return datetime.now().strftime("%Y-%m-%d")

# ===== 辅助函数 =====

def _mask_secret(value):
    if not value:
        return ""
    value = str(value)
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "..." + value[-4:]


def _looks_placeholder(value):
    if not value:
        return True
    value = str(value).strip().lower()
    return (
        value.startswith("your-")
        or value in {"sk-...", "changeme", "todo", "xxx"}
        or "your-" in value
        or "example" in value
    )


def _read_env_file(path):
    cfg = {}
    if not path.exists():
        return cfg
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key.strip()] = value.strip()
    return cfg


def _llm_env_status():
    env_path = LLM_TASKS_PATH.parent / ".env"
    cfg = _read_env_file(env_path)
    provider = cfg.get("LLM_PROVIDER", "mmx-cli")
    key_map = {
        "mmx-cli": "MMX_TOKEN_PLAN_KEY",
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "zai": "ZAI_API_KEY",
        "minimax": "MINIMAX_HTTP_API_KEY",
    }
    key_name = key_map.get(provider, "")
    key_value = cfg.get(key_name, "")
    complete = bool(key_name and key_value and not _looks_placeholder(key_value))
    if provider == "mmx-cli" and not complete and shutil.which("mmx"):
        complete = True
    return {
        "env_path": env_path,
        "provider": provider,
        "key_name": key_name,
        "complete": complete,
        "setup_completed": cfg.get("SETUP_COMPLETED", "").lower() == "true",
    }


def run_setup_wizard():
    """首次安装的最小初始化：只配置 LLM provider，确保本地 Markdown 能生成。"""
    print("\n" + "=" * 50)
    print("AI Daily News 首次初始化")
    print("=" * 50)
    print("最小功能只需要配置 LLM provider。")
    print("飞书文档、飞书消息和 TTS 都是可选扩展，之后需要时再配置。\n")

    guide_path = LLM_TASKS_PATH / "setup_guide.py"
    if not guide_path.exists():
        raise FileNotFoundError(f"LLM 初始化向导不存在：{guide_path}")

    import runpy
    runpy.run_path(str(guide_path), run_name="__main__")

    run_entry = Path(__file__).resolve().parent / "run.py"
    cfg = load_config()
    output_dir = get_output_dir(cfg)
    print("\n输出位置：")
    print(f"- 默认历史目录：{output_dir}")
    print("- 每次运行会保存到：<历史目录>/YYYY-MM-DD/HHMMSS/")
    print("- 如需自定义，可在 ~/.hermes/config/ai-daily-news-v2.json 中修改 output.dir")

    print("\n下一步：")
    print(f"1. python3 {run_entry} check")
    print(f"2. python3 {run_entry} run-local")
    print("\n可选扩展：")
    print(f"- 配置飞书：python3 {run_entry} setup-feishu")


def ensure_minimal_setup():
    status = _llm_env_status()
    if status["complete"]:
        return True
    if sys.stdin.isatty():
        print("检测到 LLM provider 还未完成配置，将启动首次初始化向导。")
        run_setup_wizard()
        return _llm_env_status()["complete"]
    return False


def check_config():
    """检查运行配置和依赖，不执行抓取、生成、写入等有副作用的任务。"""
    checks = []

    def add(name, status, detail=""):
        checks.append({"name": name, "status": status, "detail": detail})

    def ok(name, detail=""):
        add(name, "OK", detail)

    def warn(name, detail=""):
        add(name, "WARN", detail)

    def fail(name, detail=""):
        add(name, "FAIL", detail)

    def info(name, detail=""):
        add(name, "INFO", detail)

    try:
        cfg = load_config()
        if CONFIG_PATH.exists():
            ok("主配置", f"使用用户配置 {CONFIG_PATH}")
        elif _DEFAULT_CONFIG_PATH.exists():
            warn("主配置", f"未找到用户配置 {CONFIG_PATH}，将使用内置默认配置")
        else:
            fail("主配置", f"用户配置和内置默认配置都不存在：{CONFIG_PATH}")
            cfg = {}
    except Exception as e:
        fail("主配置", e)
        cfg = {}

    output_dir = get_output_dir(cfg)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        ok("输出目录", str(output_dir))
        info("运行产物", f"每次运行保存到 {output_dir}/YYYY-MM-DD/HHMMSS/；当天 latest.json 指向最近一次运行")
    except Exception as e:
        fail("输出目录", e)

    skill_paths = {
        "feishu-doc": FEISHU_DOC_PATH,
        "github-trending": GITHUB_TRENDING_PATH,
        "ph-review-generator": PH_REVIEW_PATH,
        "llm-tasks": LLM_TASKS_PATH,
        "tts-audio": TTS_AUDIO_PATH,
        "follow-builders-data": FOLLOW_BUILDERS_DATA_PATH,
    }
    for name, path in skill_paths.items():
        if path.exists():
            ok(f"组件 skill: {name}", str(path))
        else:
            fail(f"组件 skill: {name}", f"路径不存在：{path}")

    github_cfg = cfg.get("github", {})
    if github_cfg.get("topics") and github_cfg.get("limit"):
        ok("GitHub 配置", f"topics={len(github_cfg.get('topics', []))}, limit={github_cfg.get('limit')}")
    else:
        warn("GitHub 配置", "topics 或 limit 为空，将影响 GitHub 板块")

    ph_cfg = cfg.get("product_hunt", {})
    if ph_cfg.get("limit"):
        ok("Product Hunt 配置", f"limit={ph_cfg.get('limit')}, category={ph_cfg.get('category', '')}")
    else:
        warn("Product Hunt 配置", "limit 为空，将影响 Product Hunt 板块")

    try:
        env_status = _llm_env_status()
        os.environ["LLM_TASKS_DISABLE_SETUP"] = "true"
        llm_cfg = llm_tasks._load_config()
        provider = llm_cfg.get("provider", "mmx-cli")
        timeout = llm_cfg.get("timeout")
        if provider == "mmx-cli":
            token_plan_key = llm_cfg.get("mmx", {}).get("token_plan_key", "")
            if shutil.which("mmx"):
                if token_plan_key and not _looks_placeholder(token_plan_key):
                    ok("LLM Provider", f"mmx-cli 可用，MMX_TOKEN_PLAN_KEY={_mask_secret(token_plan_key)}, timeout={timeout}s")
                else:
                    warn("LLM Provider", "mmx-cli 可用，但 .env 未配置有效 MMX_TOKEN_PLAN_KEY；将依赖本机 mmx config")
            else:
                fail("LLM Provider", "LLM_PROVIDER=mmx-cli，但未找到 mmx 命令")
        else:
            api_key = llm_cfg.get("openai", {}).get("api_key", "")
            model = llm_cfg.get("openai", {}).get("model", "")
            base_url = llm_cfg.get("openai", {}).get("base_url", "")
            if api_key and not _looks_placeholder(api_key):
                ok("LLM Provider", f"{provider} model={model}, base_url={base_url}, api_key={_mask_secret(api_key)}")
            else:
                fail("LLM Provider", f"{provider} 未配置有效 {env_status.get('key_name') or 'API key'}")
    except Exception as e:
        fail("LLM Provider", e)

    tts_cfg = cfg.get("tts", {})
    tts_provider = tts_cfg.get("provider") or tts_audio.get_provider()
    if tts_cfg.get("skip", False):
        info("TTS", "未启用；如需语音摘要，将主配置中的 tts.skip 改为 false，并安装 mmx-cli")
    elif tts_provider != "mmx-cli":
        warn("TTS", f"当前 provider={tts_provider}，目前仅支持 mmx-cli")
    elif tts_audio.is_available(tts_provider):
        ok("TTS", f"mmx-cli speech synthesize 可用，voice={tts_cfg.get('voice', '')}；TTS 不直接读取 MMX_TOKEN_PLAN_KEY")
    else:
        warn("TTS", "未找到 mmx 命令；日报仍可生成，但不会有语音")

    if shutil.which("lark-cli"):
        ok("lark-cli", shutil.which("lark-cli"))
    else:
        info("lark-cli", "未安装；不影响本地 Markdown，配置飞书扩展时再安装")

    try:
        feishu_cfg = feishu_doc._load_config()
        has_doc_target = bool(feishu_cfg.get("folder_token") or feishu_cfg.get("wiki_space_id"))
        has_msg_target = bool(feishu_cfg.get("chat_id") or feishu_cfg.get("user_id"))
        if not feishu_doc.ENV_FILE.exists():
            info("飞书配置", "未启用；如需飞书文档/消息，运行 --setup-feishu")
        elif has_doc_target or has_msg_target:
            target_bits = []
            if feishu_cfg.get("wiki_space_id"):
                target_bits.append(f"wiki_space_id={feishu_cfg.get('wiki_space_id')}")
            if feishu_cfg.get("parent_node_token"):
                target_bits.append(f"parent_node_token={feishu_cfg.get('parent_node_token')}")
            if feishu_cfg.get("folder_token"):
                target_bits.append(f"folder_token={feishu_cfg.get('folder_token')}")
            if feishu_cfg.get("chat_id"):
                target_bits.append(f"chat_id={feishu_cfg.get('chat_id')}")
            if feishu_cfg.get("user_id"):
                target_bits.append(f"user_id={feishu_cfg.get('user_id')}")
            target_bits.append(f"send_as={feishu_cfg.get('send_as', 'user')}")
            ok("飞书配置", ", ".join(target_bits))
        else:
            info("飞书配置", "已存在 .env.feishu，但未配置文档或消息目标；将只生成本地 Markdown")
    except Exception as e:
        fail("飞书配置", e)

    print("\n" + "=" * 50)
    print("AI Daily News 配置检查")
    print("=" * 50)
    for item in checks:
        marker = {"OK": "✓", "INFO": "i", "WARN": "⚠", "FAIL": "✗"}[item["status"]]
        print(f"{marker} [{item['status']}] {item['name']}")
        if item["detail"]:
            print(f"    {item['detail']}")
    failures = [i for i in checks if i["status"] == "FAIL"]
    warnings = [i for i in checks if i["status"] == "WARN"]
    print("=" * 50)
    print(f"结果：{len(failures)} 个失败，{len(warnings)} 个提醒")
    print("=" * 50)
    return len(failures) == 0

def get_follow_builders():
    """
    获取 Follow Builders 数据。
    通过 follow-builders-data skill 从 GitHub 远程中心化 feed 拉取。
    """
    return follow_builders_data.fetch()

def remix_follow_builders(fb_data):
    """
    将 Follow Builders 数据 remix 成播客+推文摘要。
    调用 llm-tasks provider，返回 {"podcast_digest": ..., "tweets_digest": [...]}
    """
    builders = fb_data.get("builders", [])
    podcasts = fb_data.get("podcasts", [])
    x_data = fb_data.get("x", [])

    has_podcast = len(podcasts) > 0
    has_tweets = len(x_data) > 0

    # 构造推文 blocks
    tweet_blocks = []
    for entry in x_data:
        handle = entry.get("handle", "")
        name = entry.get("name", handle)
        role = entry.get("role", "")
        tweets = entry.get("tweets", [])
        if not tweets:
            continue
        block = f"【{name} {role} @{handle}】\n"
        for t in tweets[:3]:
            block += f"- {t.get('text', '')} {t.get('url', '')}\n"
        tweet_blocks.append(block)

    # 构造 prompt
    podcast_section = ""
    if has_podcast:
        p = podcasts[0]
        transcript = p.get("transcript", "")[:3000]
        podcast_section = f"""【播客 remixer 规则】
阅读以下播客 transcript，用 200-300 字 remixer 成一篇结构化中文笔记：
1. 以一句话「核心结论」开头——这期节目最重要的 insight 是什么
2. 介绍背景：嘉宾是谁、他们在做什么、为什么这个话题重要
3. 列出 3-5 个具体洞察（要具体到说了什么、为什么重要，不要泛泛而谈）
4. 包含至少一句直接引用（从 transcript 中挑最有力量的原话）
5. 适合不懂技术的成年人阅读，避免专业术语堆砌

{p['name']}：{p['title']}
链接：{p['url']}

Transcript：
{transcript}

"""
    else:
        podcast_section = "（今日无播客）\n\n"

    tweets_section = ""
    if tweet_blocks:
        tweets_section = "【推文 remixer 规则】\n" + "\n".join(tweet_blocks)
    else:
        tweets_section = "（今日无有效推文）"

    prompt = f"""你是一个专业的 AI 播客编辑。请将以下播客内容 remixer 成中文笔记，同时处理 builder 推文。

{podcast_section}
{tweets_section}

请返回如下格式的 JSON（严格 JSON，不要任何其他内容）：
{{
  "podcast_digest": "播客 remixer 后的中文文本（200-300字，含核心洞察和直接引用）",
  "tweets_digest": ["第一条推文摘要", "第二条推文摘要", ...]
}}

注意：
- podcast_digest 要有具体洞察，不要写成「节目讨论了XXX」这种泛泛描述
- tweets_digest 每条 2-4 句，格式：「人名 角色：摘要内容 链接」
- 只 remixer 有实质内容的 builders，无实质内容的 builder 跳过
- 返回严格 JSON，用双引号
"""

    raw = llm_tasks.chat(prompt, timeout=180)
    if raw is None:
        print(f"[FB] remix 失败", file=sys.stderr)
        return None

    raw = raw.strip()
    raw = re.sub(r"^```json\s*", "", raw).strip()
    raw = re.sub(r"\s*```$", "", raw).strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        print(f"[FB] remix JSON 解析失败", file=sys.stderr)
        return None
    try:
        data = json.loads(m.group())
        return {
            "podcast_digest": data.get("podcast_digest", ""),
            "tweets_digest": data.get("tweets_digest", [])
        }
    except json.JSONDecodeError:
        print(f"[FB] remix JSON 解析异常", file=sys.stderr)
        return None

# ===== 文档内容生成 =====

def _load_template(name):
    path = TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"模板不存在: {path}")
    with open(path) as f:
        return f.read()


def _load_prompt(name):
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt 不存在: {path}")
    with open(path) as f:
        return f.read()


def _render_template(template_text, values):
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", str(value or ""))
    return rendered


def _remove_template_block(template_text, start_marker, end_marker):
    start = "{{" + start_marker + "}}"
    end = "{{" + end_marker + "}}"
    if start not in template_text or end not in template_text:
        return template_text
    before, rest = template_text.split(start, 1)
    _, after = rest.split(end, 1)
    return before + after


def build_document(date_str, summary_text, sections, template_name="daily_markdown.md", metadata=None):
    """按模板组装完整日报文档。"""
    template = _load_template(template_name)
    metadata = metadata or {}
    has_audio = bool(metadata.get("has_audio"))
    if not has_audio:
        template = _remove_template_block(template, "audio_section_start", "audio_section_end")
    values = {
        "date": date_str,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "run_id": metadata.get("run_id", ""),
        "summary": summary_text,
        "follow_builders_section": sections.get("fb", ""),
        "product_hunt_section": sections.get("ph", ""),
        "github_section": sections.get("gh", ""),
        "status_section": sections.get("status", ""),
        "audio_section_start": "",
        "audio_section_end": "",
    }
    return _render_template(template, values).strip() + "\n"


def build_feishu_document_parts(date_str, summary_text, sections, has_audio=False, metadata=None):
    """按飞书模板组装文档；有音频时返回音频插入点前后的两段内容。"""
    metadata = dict(metadata or {})
    metadata["has_audio"] = has_audio
    content = build_document(date_str, summary_text, sections, template_name="daily_feishu.md", metadata=metadata)
    marker = "{{tts_audio_slot}}"
    if has_audio and marker in content:
        before, after = content.split(marker, 1)
        return before.strip() + "\n", after.strip() + "\n"
    return content.replace(marker, "").strip() + "\n", ""


def build_header(date_str):
    """Backward-compatible header helper used by existing smoke tests."""
    return _render_template(
        _load_template("daily_markdown.md"),
        {
            "date": date_str,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "run_id": "",
            "summary": "",
            "follow_builders_section": "",
            "product_hunt_section": "",
            "github_section": "",
            "status_section": "",
        },
    ).split("## 今日摘要", 1)[0]

def build_gh_section(items):
    if not items:
        return "今日暂无可展示的热门项目。\n"
    lines = []
    for i, item in enumerate(items, 1):
        extra = item.get("extra", {})
        if isinstance(extra, dict):
            topics = extra.get("topics", [])
            desc = extra.get("description", item.get("description", ""))
        else:
            topics = []
            desc = item.get("description", "")
        topics_str = " · ".join(topics[:5]) if topics else ""

        lines.append(f"### {i}. {item['title']}\n\n")
        meta = [f"Star {item.get('stars', 0):,}", item.get("language") or "N/A"]
        if topics_str:
            meta.append(topics_str)
        lines.append(f"**指标**：{' · '.join(meta)}\n\n")
        lines.append(f"**它是什么**：{desc or '暂无描述'}\n\n")
        lines.append(f"**专业点评**：{item.get('ai_review', '') or '暂无 AI 点评'}\n\n")
        lines.append(f"**链接**：[{item['url']}]({item['url']})\n\n")
    return "".join(lines)

def build_ph_section(items):
    if not items:
        return "今日暂无可展示的热门产品。\n"
    lines = []
    for i, item in enumerate(items, 1):
        translated = item.get("translated", item.get("title", ""))
        review = item.get("review", "")
        lines.append(f"### {i}. {item['title']}\n\n")
        lines.append(f"**它是什么**：{translated or item.get('description', '')}\n\n")
        lines.append(f"**专业点评**：{review or '暂无 AI 点评'}\n\n")
        lines.append(f"**链接**：[{item['url']}]({item['url']})\n\n")
    return "".join(lines)

def build_fb_section(fb_result):
    lines = []

    podcast_digest = ""
    tweets_digest = []
    if fb_result:
        podcast_digest = fb_result.get("podcast_digest", "")
        tweets_digest = fb_result.get("tweets_digest", [])

    lines.append("### 建造者动态\n\n")
    if tweets_digest:
        for t in tweets_digest:
            lines.append(f"- {t}\n")
        lines.append("\n")
    else:
        lines.append("今日暂无可展示的建造者动态。\n\n")

    lines.append("### 播客摘录\n\n")
    if podcast_digest:
        lines.append(f"{podcast_digest}\n\n")
    else:
        lines.append("今日暂无可展示的播客摘录。\n\n")

    return "".join(lines)


def build_status_section(run_summary, gh_ok, ph_ok, fb_ok, tts_ok, doc_url):
    """生成日报尾部状态，帮助读者判断本次报告完整性。"""
    if not run_summary:
        return ""
    status = run_summary.get("status", "running")
    if status == "running":
        status = "degraded" if run_summary.get("errors") else "success"
    lines = [
        f"- **运行状态**：{status}",
        f"- **数据源**：GitHub {'OK' if gh_ok else 'FAILED'} · Product Hunt {'OK' if ph_ok else 'FAILED'} · Follow Builders {'OK' if fb_ok else 'FAILED'}",
        f"- **TTS**：{'OK' if tts_ok else '未生成'}",
        f"- **飞书文档**：{doc_url or '未创建'}",
        f"- **Run ID**：{run_summary.get('run_id', '')}",
    ]
    errors = run_summary.get("errors", [])
    warnings = run_summary.get("warnings", [])
    if errors:
        lines.append(f"- **错误**：{len(errors)} 条，详见 `run_summary.json`")
    if warnings:
        lines.append(f"- **提醒**：{len(warnings)} 条，详见 `run_summary.json`")
    return "\n".join(lines) + "\n"

# ===== 主流程 =====

def run_one_day(date_str=None, skip_feishu=False, skip_tts_override=False, resume_failed=False):
    """
    执行一次完整的 AI 每日资讯生成。
    返回结果 dict，失败返回 None。
    """
    global OUTPUT_DIR

    cfg = load_config()
    OUTPUT_DIR = get_output_dir(cfg)

    run_dt = datetime.now()
    date_str = date_str or run_dt.strftime("%Y-%m-%d")
    date_dir_str = date_str.replace("-", "")
    run_time_label = run_dt.strftime("%H:%M")
    date_root = OUTPUT_DIR / date_str
    resume_checkpoint = None
    resume_summary = None
    resume_source_dir = None
    if resume_failed:
        latest_path = date_root / "latest.json"
        if latest_path.exists():
            try:
                with open(latest_path) as f:
                    latest = json.load(f)
                prev_summary_path = Path(latest.get("run_summary", ""))
                prev_output_dir = Path(latest.get("output_dir", ""))
                checkpoint_path = prev_output_dir / "checkpoint.json"
                if prev_summary_path.exists():
                    with open(prev_summary_path) as f:
                        resume_summary = json.load(f)
                if (
                    resume_summary
                    and resume_summary.get("status") in ("degraded", "failed")
                    and checkpoint_path.exists()
                ):
                    with open(checkpoint_path) as f:
                        resume_checkpoint = json.load(f)
                    resume_source_dir = prev_output_dir
            except Exception:
                resume_checkpoint = None
                resume_summary = None
                resume_source_dir = None
    base_run_id = run_dt.strftime("%H%M%S")
    run_id = base_run_id
    suffix = 1
    while (date_root / run_id).exists():
        run_id = f"{base_run_id}-{suffix:02d}"
        suffix += 1
    day_dir = date_root / run_id
    doc_title = f"AI 今日讯息 {date_str} {run_time_label}"
    started_at = run_dt.isoformat()
    run_summary = {
        "date": date_str,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": None,
        "status": "running",
        "degraded": False,
        "date_root": str(date_root),
        "output_dir": str(day_dir),
        "doc_title": doc_title,
        "doc_url": None,
        "artifacts": {
            "markdown": str(day_dir / "index.md"),
            "tts_text": str(day_dir / "tts_text.txt"),
            "audio": None,
            "doc_url": str(day_dir / "doc_url.txt"),
            "follow_builders_raw": str(day_dir / "follow_builders_raw.json"),
            "run_summary": str(day_dir / "run_summary.json"),
            "checkpoint": str(day_dir / "checkpoint.json"),
        },
        "data": {
            "github": {"ok": False, "count": 0, "details_enriched": 0, "ai_review_ok": False},
            "product_hunt": {
                "ok": False,
                "count": 0,
                "ai_review_ok": False,
                "ai_review_partial": False,
                "ai_review_fallback": 0,
            },
            "follow_builders": {"ok": False, "builders": 0, "podcasts": 0, "tweets_digest_count": 0},
        },
        "steps": {
            "summary": {"ok": False, "fallback": False},
            "feishu_create": {"ok": False, "skipped": False},
            "feishu_write": {"ok": False, "skipped": False},
            "tts": {"ok": False, "skipped": False},
            "local_save": {"ok": False},
            "feishu_notify": {"ok": False, "skipped": False},
        },
        "errors": [],
        "warnings": [],
        "options": {
            "skip_feishu": skip_feishu,
            "skip_tts": skip_tts_override,
            "resume_failed": resume_failed,
            "resume_source": str(resume_source_dir) if resume_source_dir else None,
        },
    }

    def add_error(stage, message):
        run_summary["errors"].append({"stage": stage, "message": str(message)})
        run_summary["degraded"] = True

    def add_warning(stage, message):
        run_summary["warnings"].append({"stage": stage, "message": str(message)})

    def can_resume(stage):
        return bool(
            resume_checkpoint
            and resume_checkpoint.get("stages", {}).get(stage, {}).get("ok")
        )

    def checkpoint_data(stage, key=None, default=None):
        if not resume_checkpoint:
            return default
        data = resume_checkpoint.get("data", {}).get(stage, {})
        if key is None:
            return data
        return data.get(key, default)

    def copy_cached_audio():
        cached_audio = checkpoint_data("tts", "audio")
        if not cached_audio or not os.path.exists(cached_audio):
            return None
        day_dir.mkdir(parents=True, exist_ok=True)
        dest = day_dir / "audio.mp3"
        if Path(cached_audio).resolve() != dest.resolve():
            import shutil
            shutil.copy2(cached_audio, dest)
        return str(dest)

    def save_run_summary():
        run_summary["finished_at"] = datetime.now().isoformat()
        if run_summary["status"] == "running":
            has_core_data = (
                run_summary["data"]["github"]["ok"]
                and run_summary["data"]["product_hunt"]["ok"]
                and run_summary["data"]["follow_builders"]["ok"]
            )
            run_summary["status"] = "success" if has_core_data and not run_summary["errors"] else "degraded"
        day_dir.mkdir(parents=True, exist_ok=True)
        with open(day_dir / "run_summary.json", "w") as f:
            json.dump(run_summary, f, ensure_ascii=False, indent=2)
        if run_summary["status"] != "skipped":
            date_root.mkdir(parents=True, exist_ok=True)
            latest = {
                "date": date_str,
                "run_id": run_id,
                "status": run_summary["status"],
                "doc_title": run_summary["doc_title"],
                "doc_url": run_summary["doc_url"],
                "output_dir": run_summary["output_dir"],
                "run_summary": run_summary["artifacts"]["run_summary"],
                "finished_at": run_summary["finished_at"],
            }
            with open(date_root / "latest.json", "w") as f:
                json.dump(latest, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"AI 每日资讯 v17 — {date_str}")
    print(f"{'='*50}\n")
    if resume_failed and resume_checkpoint:
        reusable = [
            name for name, state in resume_checkpoint.get("stages", {}).items()
            if state.get("ok")
        ]
        reusable_text = "、".join(reusable) if reusable else "无"
        print(f"🔁 失败补跑模式：读取 {resume_source_dir}")
        print(f"   可复用阶段：{reusable_text}\n")
    elif resume_failed:
        print("🔁 失败补跑模式：未找到可复用的失败运行，按普通新运行执行\n")

    # --- 幂等锁 ---
    lock_file = OUTPUT_DIR / f".lock_{date_dir_str}"
    if lock_file.exists():
        print("⏭️ 任务正在进行中或刚完成（锁文件存在），跳过。\n")
        run_summary["status"] = "skipped"
        add_warning("lock", "lock file exists")
        save_run_summary()
        return run_summary

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    day_dir.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "w") as f:
        f.write(datetime.now().isoformat() + "\n")

    def release_lock():
        try:
            if lock_file.exists():
                os.unlink(lock_file)
        except Exception:
            pass

    try:
        # === 1. 抓取数据 ===
        if can_resume("github"):
            gh_items = checkpoint_data("github", "items", [])
            gh_ok = len(gh_items) > 0
            run_summary["data"]["github"].update(resume_checkpoint.get("summary", {}).get("data", {}).get("github", {}))
            add_warning("github", "复用上一轮已成功的 GitHub 板块")
            print(f"📡 GitHub Trending：复用上一轮结果 {len(gh_items)} 条\n")
        else:
            print("📡 正在抓取 GitHub Trending...")
            gh_items = github_trending.get_trending(
                topics=cfg.get("github", {}).get("topics"),
                period=cfg.get("github", {}).get("period", "past_24_hours"),
                limit=cfg.get("github", {}).get("limit", 10)
            )
            gh_ok = len(gh_items) > 0
            run_summary["data"]["github"]["ok"] = gh_ok
            run_summary["data"]["github"]["count"] = len(gh_items)
            if not gh_ok:
                add_error("github_fetch", "GitHub Trending 获取失败或结果为空")
            print(f"✓ GitHub：{'获取到 ' + str(len(gh_items)) + ' 条' if gh_ok else '获取失败'}\n")

        if can_resume("product_hunt"):
            ph_items = checkpoint_data("product_hunt", "items", [])
            ph_ok = len(ph_items) > 0
            run_summary["data"]["product_hunt"].update(resume_checkpoint.get("summary", {}).get("data", {}).get("product_hunt", {}))
            add_warning("product_hunt", "复用上一轮已成功的 Product Hunt 板块")
            print(f"📡 Product Hunt：复用上一轮结果 {len(ph_items)} 条\n")
        else:
            print("📡 正在抓取 Product Hunt...")
            ph_items = ph_review.get_product_hunt(cfg.get("product_hunt", {}))
            ph_ok = len(ph_items) > 0
            run_summary["data"]["product_hunt"]["ok"] = ph_ok
            run_summary["data"]["product_hunt"]["count"] = len(ph_items)
            if not ph_ok:
                add_error("product_hunt_fetch", "Product Hunt 获取失败或结果为空")
            print(f"✓ Product Hunt：{'获取到 ' + str(len(ph_items)) + ' 条' if ph_ok else '获取失败'}\n")

        # === 2. GitHub 详情补充 ===
        if can_resume("github"):
            print("🔍 GitHub 详情补充：复用上一轮结果\n")
        else:
            print("🔍 正在为 GitHub 项目补充详细信息...")
            enriched = 0
            for i, item in enumerate(gh_items, 1):
                extra = github_trending.get_repo_details(item["title"])
                if extra:
                    item["extra"] = extra
                    enriched += 1
                print(f"  ✓ [{i}/{len(gh_items)}] {item['title']}")
                time.sleep(0.5)
            run_summary["data"]["github"]["details_enriched"] = enriched
            if gh_items and enriched < len(gh_items):
                add_error("github_details", f"GitHub 详情只成功 {enriched}/{len(gh_items)} 条")
            print(f"\n✓ GitHub API 成功获取 {enriched}/{len(gh_items)} 条详情\n")

        # === 3. 生成 PH AI 翻译+点评 ===
        if can_resume("product_hunt"):
            print("🤖 Product Hunt AI 点评：复用上一轮结果\n")
        else:
            print("🤖 正在生成 Product Hunt AI 翻译和点评...")
            ph_reviewed = ph_review.ph_ai_review(ph_items)
            if ph_reviewed:
                for i, item in enumerate(ph_items):
                    if i < len(ph_reviewed):
                        item["translated"] = ph_reviewed[i].get("translated", item.get("description", ""))
                        item["review"] = ph_reviewed[i].get("review", "")
                        item["review_source"] = ph_reviewed[i].get("review_source", "llm")
                llm_count = sum(1 for item in ph_items if item.get("review_source") == "llm")
                fallback_count = sum(1 for item in ph_items if item.get("review_source") == "fallback")
                run_summary["data"]["product_hunt"]["ai_review_ok"] = bool(ph_items and llm_count == len(ph_items))
                run_summary["data"]["product_hunt"]["ai_review_partial"] = bool(llm_count and fallback_count)
                run_summary["data"]["product_hunt"]["ai_review_fallback"] = fallback_count
                if fallback_count and llm_count:
                    add_warning("product_hunt_ai_review", f"PH AI 点评部分成功：LLM {llm_count}/{len(ph_items)}，本地兜底 {fallback_count}/{len(ph_items)}")
                    print(f"⚠ PH AI 点评部分完成：LLM {llm_count}/{len(ph_items)}，本地兜底 {fallback_count}/{len(ph_items)}\n")
                elif fallback_count:
                    add_warning("product_hunt_ai_review", "PH AI 点评 LLM 不可用，已全部使用本地兜底")
                    print(f"⚠ PH AI 点评使用本地兜底：{fallback_count}/{len(ph_items)} 条\n")
                else:
                    print(f"✓ PH AI 点评完成：{llm_count}/{len(ph_items)} 条成功\n")
            else:
                add_error("product_hunt_ai_review", "PH AI 点评失败，且本地兜底未返回结果")
                print("  ⚠ PH AI 点评失败，跳过\n")

        # === 4. 生成 GH AI 点评 ===
        if can_resume("github"):
            print("🤖 GitHub AI 点评：复用上一轮结果\n")
        else:
            print("🤖 正在生成 GitHub AI 点评...")
            gh_reviewed = github_trending.gh_ai_review(gh_items)
            if gh_reviewed:
                for i, item in enumerate(gh_items):
                    item["ai_review"] = gh_reviewed[i] if i < len(gh_reviewed) else ""
                run_summary["data"]["github"]["ai_review_ok"] = True
                print(f"✓ GitHub AI 点评完成：{len(gh_reviewed)}/{len(gh_items)} 条成功\n")
            else:
                add_error("github_ai_review", "GitHub AI 点评失败，已使用原始描述降级")
                print("  ⚠ GitHub AI 点评失败，跳过\n")

        # === 5. Follow Builders ===
        fb_data = None
        if can_resume("follow_builders"):
            fb_result = checkpoint_data("follow_builders", "result")
            fb_data = checkpoint_data("follow_builders", "raw")
            fb_ok = bool(fb_result)
            run_summary["data"]["follow_builders"].update(resume_checkpoint.get("summary", {}).get("data", {}).get("follow_builders", {}))
            add_warning("follow_builders", "复用上一轮已成功的 Follow Builders 板块")
            print("📬 Follow Builders：复用上一轮 remix 结果\n")
        else:
            print("📬 正在获取 Follow Builders 内容...")
            fb_data = get_follow_builders()
            fb_result = None
            fb_ok = False
            if fb_data:
                x_count = len(fb_data.get("x", []))
                pod_count = len(fb_data.get("podcasts", []))
                run_summary["data"]["follow_builders"]["builders"] = x_count
                run_summary["data"]["follow_builders"]["podcasts"] = pod_count
                print(f"  获取到 {x_count} 位 builders 的推文", end="")
                if pod_count > 0:
                    print(f" 和 {pod_count} 期播客", end="")
                print()
                fb_result = remix_follow_builders(fb_data)
                if fb_result:
                    fb_ok = True
                    run_summary["data"]["follow_builders"]["ok"] = True
                    pd = fb_result.get("podcast_digest", "")
                    td_count = len(fb_result.get("tweets_digest", []))
                    run_summary["data"]["follow_builders"]["tweets_digest_count"] = td_count
                    print(f"  ✓ Follow Builders remix 完成")
                    print(f"    播客：{pd[:60]}..." if pd else "    播客：（无）")
                    print(f"    推文：{td_count} 条")
                else:
                    add_error("follow_builders_remix", "Follow Builders remix 失败")
                    print("  ✗ Follow Builders remix 失败")
            else:
                add_error("follow_builders_fetch", "Follow Builders 远程 feed 获取失败")
                print("  ✗ Follow Builders 获取失败\n")
        print()

        # === 6. 生成文档内容 ===
        print("✍️ 正在生成文档各板块内容...")
        sections = {
            "gh": build_gh_section(gh_items),
            "ph": build_ph_section(ph_items),
            "fb": build_fb_section(fb_result),
        }
        print("✓ 文档各板块已生成\n")

        # === 7. 生成摘要 ===
        if can_resume("summary"):
            summary_text = checkpoint_data("summary", "summary_text", "")
            tts_text = checkpoint_data("summary", "tts_text", summary_text)
            run_summary["steps"]["summary"]["ok"] = True
            add_warning("summary", "复用上一轮已成功的今日摘要")
            print("📝 今日摘要：复用上一轮结果\n")
        else:
            print("📝 正在生成今日摘要...")
            summary_text, tts_text = _generate_summary(gh_items, ph_items, fb_result, date_str, cfg)
            if not summary_text:
                summary_text = _summary_fallback(gh_items, ph_items, fb_result, date_str)
                tts_text = summary_text
                run_summary["steps"]["summary"]["fallback"] = True
                add_error("summary_generation", "今日摘要 LLM 生成失败，已使用本地 fallback")
            else:
                run_summary["steps"]["summary"]["ok"] = True
            print(f"  摘要：{summary_text[:80]}...\n")

        # === 8. 创建飞书文档 ===
        feishu_enabled = (not skip_feishu) and feishu_doc.is_configured()
        doc_url = None
        obj_token = None
        node = None
        if not feishu_enabled:
            run_summary["steps"]["feishu_create"]["skipped"] = True
            if skip_feishu:
                add_warning("feishu_create", "本次运行指定 --skip-feishu，跳过飞书文档")
            else:
                add_warning("feishu_create", "未配置飞书凭证，跳过飞书文档")
            print("⏭️ 未配置飞书凭证（space_id/parent_node_token 为空），跳过飞书文档\n")
        else:
            print("📝 正在创建飞书文档...")
            try:
                if can_resume("feishu_create") and checkpoint_data("feishu", "obj_token"):
                    node = checkpoint_data("feishu", "node", {})
                    obj_token = checkpoint_data("feishu", "obj_token")
                    doc_url = checkpoint_data("feishu", "doc_url")
                    add_warning("feishu_create", "复用上一轮已创建的飞书文档")
                else:
                    node = feishu_doc.create_node(doc_title)
                if node or obj_token:
                    obj_token = obj_token or node.get("obj_token")
                    doc_url = doc_url or node.get("url") or f"https://feishu.cn/wiki/{node.get('token', '')}"
                    run_summary["doc_url"] = doc_url
                    run_summary["steps"]["feishu_create"]["ok"] = True
                    print(f"✓ 文档节点已创建：{node.get('token', obj_token)}\n")
                else:
                    add_error("feishu_create", "飞书文档创建返回空结果")
            except Exception as e:
                add_error("feishu_create", e)
                print(f"  ✗ 文档创建失败: {e}，跳过文档创建\n")

        # === 9. TTS 生成 ===
        all_data_ok = gh_ok and ph_ok and fb_ok
        skip_tts = skip_tts_override or cfg.get("tts", {}).get("skip", False)
        tts_ok = False
        mp3_path = None
        tts_provider = cfg.get("tts", {}).get("provider") or tts_audio.get_provider()
        if can_resume("tts"):
            mp3_path = copy_cached_audio()
            if mp3_path:
                tts_ok = True
                run_summary["steps"]["tts"]["ok"] = True
                run_summary["artifacts"]["audio"] = str(mp3_path)
                add_warning("tts", "复用上一轮已生成的语音文件")
                print(f"🎙️ 语音摘要：复用上一轮文件 {mp3_path}\n")
            else:
                add_warning("tts", "上一轮语音文件不存在，重新生成语音")
        if not tts_ok and not run_summary["steps"]["tts"]["skipped"] and not all_data_ok:
            run_summary["steps"]["tts"]["skipped"] = True
            add_warning("tts", "数据不完整（GH/FB/PH 之一失败），跳过 TTS")
            print("⏭️ 数据不完整（GH/FB/PH 之一失败），跳过 TTS\n")
        elif not tts_ok and not run_summary["steps"]["tts"]["skipped"] and skip_tts:
            run_summary["steps"]["tts"]["skipped"] = True
            add_warning("tts", "本次运行指定 --skip-tts 或配置 skip=true，跳过 TTS")
            print("⏭️ 跳过语音生成（config 中 skip=true）\n")
        elif not tts_ok and not run_summary["steps"]["tts"]["skipped"] and tts_provider != "mmx-cli":
            run_summary["steps"]["tts"]["skipped"] = True
            add_warning("tts", f"当前 TTS provider 为 {tts_provider}，跳过语音生成")
            print(f"⏭️ 当前 TTS provider 为 {tts_provider}，跳过语音生成（目前仅 mmx-cli 支持）\n")
        elif not tts_ok and not run_summary["steps"]["tts"]["skipped"] and not tts_audio.is_available(tts_provider):
            run_summary["steps"]["tts"]["skipped"] = True
            add_warning("tts", "tts-audio 不可用（未找到 mmx 命令）")
            print("⏭️ tts-audio 不可用（未找到 mmx 命令），跳过语音生成\n")
        elif not tts_ok and not run_summary["steps"]["tts"]["skipped"]:
            voice = cfg.get("tts", {}).get("voice", "Chinese (Mandarin)_Warm_Girl")
            print("🎙️ 正在生成语音摘要...")
            mp3_path = tts_audio.generate_audio(tts_text, day_dir, voice=voice, provider=tts_provider)
            if mp3_path:
                tts_ok = True
                run_summary["steps"]["tts"]["ok"] = True
                run_summary["artifacts"]["audio"] = str(mp3_path)
                print(f"  ✓ 语音已生成：{mp3_path}")
            else:
                add_error("tts", "语音生成失败")
                print("  ✗ 语音生成失败\n")

        # === 10. 写入文档文字内容 ===
        sections["status"] = build_status_section(run_summary, gh_ok, ph_ok, fb_ok, tts_ok, doc_url)
        if obj_token:
            if can_resume("feishu_write"):
                ok = True
                run_summary["steps"]["feishu_write"]["ok"] = True
                add_warning("feishu_write", "复用上一轮已写入的飞书正文")
                print("📝 飞书文档内容：复用上一轮写入结果\n")
            else:
                print("📝 正在写入文档内容...")
                feishu_before_audio, feishu_after_audio = build_feishu_document_parts(
                    date_str, summary_text, sections, has_audio=bool(mp3_path), metadata={"run_id": run_id}
                )
                ok = feishu_doc.write_doc(obj_token, feishu_before_audio, mode="append")
                if ok and mp3_path:
                    print("🎧 正在插入语音摘要到飞书文档...")
                    media_ok = feishu_doc.insert_media(obj_token, mp3_path, media_type="audio")
                    print(f"  {'✓' if media_ok else '✗'} 语音播放器已{'插入' if media_ok else '插入失败'}文档\n")
                    if feishu_after_audio:
                        ok = feishu_doc.write_doc(obj_token, feishu_after_audio, mode="append")
                elif ok and feishu_after_audio:
                    ok = feishu_doc.write_doc(obj_token, feishu_after_audio, mode="append")
                run_summary["steps"]["feishu_write"]["ok"] = bool(ok)
                if not ok:
                    add_error("feishu_write", "飞书文档内容写入失败")
                print(f"{'✓' if ok else '✗'} 文档内容已{'写入' if ok else '写入失败'}\n")
        else:
            run_summary["steps"]["feishu_write"]["skipped"] = True
            add_warning("feishu_write", "无 obj_token，跳过飞书文档写入")
            print("⚠ 跳过文档内容写入（无 obj_token）\n")

        # === 11. 保存本地数据 ===
        sections["status"] = build_status_section(run_summary, gh_ok, ph_ok, fb_ok, tts_ok, doc_url)
        full_content = build_document(
            date_str,
            summary_text,
            sections,
            template_name="daily_markdown.md",
            metadata={"run_id": run_id},
        )
        day_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(day_dir / "index.md", "w") as f:
                f.write(full_content)
            with open(day_dir / "doc_url.txt", "w") as f:
                f.write(doc_url or "")
            with open(day_dir / "tts_text.txt", "w") as f:
                f.write(tts_text or "")
            if fb_data:
                with open(day_dir / "follow_builders_raw.json", "w") as f:
                    json.dump(fb_data, f, ensure_ascii=False, indent=2)
            if mp3_path and os.path.exists(mp3_path):
                tts_dest = day_dir / "audio.mp3"
                if Path(mp3_path).resolve() != tts_dest.resolve():
                    import shutil
                    shutil.copy2(mp3_path, tts_dest)
                    run_summary["artifacts"]["audio"] = str(tts_dest)
                else:
                    run_summary["artifacts"]["audio"] = str(tts_dest)
            run_summary["steps"]["local_save"]["ok"] = True
            checkpoint = {
                "date": date_str,
                "run_id": run_id,
                "summary": {
                    "data": run_summary["data"],
                    "steps": run_summary["steps"],
                },
                "stages": {
                    "github": {
                        "ok": bool(run_summary["data"]["github"]["ok"] and run_summary["data"]["github"]["ai_review_ok"])
                    },
                    "product_hunt": {
                        "ok": bool(
                            run_summary["data"]["product_hunt"]["ok"]
                            and (
                                run_summary["data"]["product_hunt"]["ai_review_ok"]
                                or run_summary["data"]["product_hunt"]["ai_review_partial"]
                                or run_summary["data"]["product_hunt"]["ai_review_fallback"]
                            )
                        )
                    },
                    "follow_builders": {
                        "ok": bool(run_summary["data"]["follow_builders"]["ok"])
                    },
                    "summary": {
                        "ok": bool(run_summary["steps"]["summary"]["ok"])
                    },
                    "tts": {
                        "ok": bool(run_summary["steps"]["tts"]["ok"] and run_summary["artifacts"].get("audio"))
                    },
                    "feishu_create": {
                        "ok": bool(run_summary["steps"]["feishu_create"]["ok"] and obj_token and doc_url)
                    },
                    "feishu_write": {
                        "ok": bool(run_summary["steps"]["feishu_write"]["ok"] and obj_token and doc_url)
                    },
                },
                "data": {
                    "github": {"items": gh_items},
                    "product_hunt": {"items": ph_items},
                    "follow_builders": {"result": fb_result, "raw": fb_data},
                    "summary": {"summary_text": summary_text, "tts_text": tts_text},
                    "tts": {"audio": run_summary["artifacts"].get("audio")},
                    "feishu": {
                        "node": node,
                        "obj_token": obj_token,
                        "doc_url": doc_url,
                    },
                },
            }
            with open(day_dir / "checkpoint.json", "w") as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
            print(f"✓ 本地文档已保存：{day_dir}\n")
        except Exception as e:
            add_error("local_save", e)
            print(f"  ⚠ 本地文档保存失败: {e}，继续\n")

        # === 12. 发送飞书消息 ===
        if doc_url:
            print("📨 正在发送飞书通知...")
            try:
                ok = feishu_doc.send_text_with_audio(
                    doc_title=doc_title,
                    doc_url=doc_url,
                    summary_text=summary_text[:200],
                    audio_path=mp3_path if tts_ok else None
                )
                run_summary["steps"]["feishu_notify"]["ok"] = bool(ok)
                if not ok:
                    add_error("feishu_notify", "飞书消息发送失败")
                print(f"{'✓' if ok else '✗'} 飞书消息已{'发送' if ok else '发送失败'}\n")
            except Exception as e:
                add_error("feishu_notify", e)
                print(f"  ✗ 飞书消息发送失败: {e}，跳过\n")
        else:
            run_summary["steps"]["feishu_notify"]["skipped"] = True
            add_warning("feishu_notify", "无飞书文档链接，跳过消息发送")

        # === 13. 结果 ===
        save_run_summary()
        result_label = "✅ 任务完成"
        if run_summary["status"] == "degraded":
            result_label = "⚠️ 任务完成（有降级）"
        print("=" * 50)
        print(f"{result_label}！")
        print(f"📄 文档链接：{doc_url or '无'}")
        status = []
        status.append("GH:" + ("✓" if gh_ok else "✗"))
        status.append("PH:" + ("✓" if ph_ok else "✗"))
        status.append("FB:" + ("✓" if fb_ok else "✗"))
        print(f"📊 数据状态：{' '.join(status)}")
        print(f"🎙️ 语音摘要：{'✓' if tts_ok else '✗'}")
        print(f"🧾 运行摘要：{day_dir / 'run_summary.json'}")
        if run_summary["errors"]:
            print("⚠️ 降级/错误：")
            for err in run_summary["errors"][:5]:
                print(f"  - {err['stage']}: {err['message']}")
            if len(run_summary["errors"]) > 5:
                print(f"  - 还有 {len(run_summary['errors']) - 5} 条，详见 run_summary.json")
        if run_summary["warnings"]:
            print("ℹ️ 提醒：")
            for warn in run_summary["warnings"][:3]:
                print(f"  - {warn['stage']}: {warn['message']}")
            if len(run_summary["warnings"]) > 3:
                print(f"  - 还有 {len(run_summary['warnings']) - 3} 条，详见 run_summary.json")
        print("=" * 50)

        return run_summary

    except Exception as e:
        run_summary["status"] = "failed"
        add_error("fatal", e)
        save_run_summary()
        raise
    finally:
        release_lock()



# ===== 摘要生成 =====

def _generate_summary(gh_items, ph_items, fb_result, date_str, cfg):
    """调用 llm-tasks 生成今日摘要"""
    gh_top3 = []
    for i, item in enumerate(gh_items[:3], 1):
        ai_desc = item.get("ai_review", "")
        if ai_desc and len(ai_desc) > 10:
            first = ai_desc.split("。")[0].split("，")[0]
            if len(first) > 60:
                first = first[:60] + "..."
            gh_top3.append(f"{i}. **{item['title']}**（⭐{item.get('stars', 0):,}）— {first}")
        else:
            gh_top3.append(f"{i}. **{item['title']}**（⭐{item.get('stars', 0):,}）— {item.get('description', '')[:50]}")

    ph_top3 = []
    for i, item in enumerate(ph_items[:3], 1):
        review = item.get("review", "")
        translated = item.get("translated", item.get("description", ""))
        if review and len(review) > 10:
            first = review.split("。")[0]
            if len(first) > 60:
                first = first[:60] + "..."
            ph_top3.append(f"{i}. **{item['title']}** — {first}")
        else:
            ph_top3.append(f"{i}. **{item['title']}** — {translated[:60]}")

    fb_text = ""
    if fb_result:
        podcast = fb_result.get("podcast_digest", "")
        tweets = fb_result.get("tweets_digest", [])
        if tweets:
            snippets = [f"· {t[:120]}" for t in tweets]
            fb_text = "推文亮点：\n" + "\n".join(snippets)
        if podcast:
            fb_text += ("\n\n" if fb_text else "") + f"播客亮点：{podcast[:200]}..."

    prompt_template = _load_prompt("doc-summary.md")
    prompt = (
        prompt_template
        .replace("{date}", date_str)
        .replace("{gh_text}", "\n".join(gh_top3) or "无")
        .replace("{ph_text}", "\n".join(ph_top3) or "无")
        .replace("{fb_text}", fb_text or "无")
    )

    summary = llm_tasks.chat(prompt, timeout=cfg.get("llm", {}).get("timeout", 120))
    if not summary:
        return None, None

    summary = summary.strip()
    # TTS 文本 = 摘要（不做额外处理）
    return summary, summary


def _summary_fallback(gh_items, ph_items, fb_result, date_str):
    """兜底摘要（当 AI 生成失败时使用）"""
    lines = [f"今日 AI 资讯汇总（{date_str}）"]
    if gh_items:
        lines.append(f"GitHub 热门：{', '.join([i['title'] for i in gh_items[:3]])}")
    if ph_items:
        lines.append(f"Product Hunt 新品：{', '.join([i['title'] for i in ph_items[:3]])}")
    if fb_result:
        tweets = fb_result.get("tweets_digest", [])
        if tweets:
            lines.append(f"Follow Builders 推文 {len(tweets)} 条")
    return "\n".join(lines)


# ===== 入口 =====

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    setup = "--setup" in sys.argv
    setup_feishu = "--setup-feishu" in sys.argv
    skip_feishu = "--skip-feishu" in sys.argv
    skip_tts = "--skip-tts" in sys.argv
    resume_failed = "--resume-failed" in sys.argv
    check_config_flag = "--check-config" in sys.argv
    if dry_run:
        print("[dry-run 模式] 跳过引导和实际执行")
        sys.exit(0)
    if check_config_flag:
        sys.exit(0 if check_config() else 1)
    if setup:
        run_setup_wizard()
        sys.exit(0)
    if setup_feishu:
        feishu_doc.check_and_guide()
        sys.exit(0)
    if not ensure_minimal_setup():
        print("LLM provider 未完成配置。请先运行：")
        print(f"python3 {Path(__file__).resolve()} --setup")
        sys.exit(1)
    run_one_day(skip_feishu=skip_feishu, skip_tts_override=skip_tts, resume_failed=resume_failed)
