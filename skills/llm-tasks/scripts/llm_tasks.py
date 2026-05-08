#!/usr/bin/env python3
"""
llm-tasks skill — 通用 LLM 批量任务封装
支持 mmx CLI 和 OpenAI 兼容 API 两种调用方式
从 .env 文件读取配置（支持多 provider）
首次运行或配置不完整时自动触发交互引导
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ===== 启动引导 =====
_setup_done = False


def _is_setup_completed():
    """检查用户是否已完成初始化向导"""
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return False
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "SETUP_COMPLETED":
                    return v.strip().lower() == "true"
    return False


def _ensure_setup():
    """首次调用时检测配置，交互式终端中可触发引导。"""
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    if os.environ.get("LLM_TASKS_DISABLE_SETUP", "").lower() == "true":
        return

    # 已完成过向导 → 跳过自动引导
    if _is_setup_completed():
        return

    guide_path = Path(__file__).parent / "setup_guide.py"
    if not guide_path.exists():
        return

    # cron / 非交互运行时不能卡在 input()，直接让后续调用按当前配置失败并输出错误。
    if not sys.stdin.isatty():
        return

    # 未完成过向导，运行引导
    try:
        import runpy
        runpy.run_path(str(guide_path), run_name="__main__")
    except SystemExit:
        pass


# ===== 环境变量加载 =====

def _get_env(key, default=None):
    """读取环境变量，优先从 .env 文件加载（如果存在）"""
    # 优先使用已经设置的环境变量（进程级别）
    val = os.environ.get(key)
    if val is not None and val != "":
        return val

    # 其次从 .env 文件读取（项目级别）
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == key:
                        return v.strip()
    return default


def _load_config():
    """将 .env 文件聚合成统一配置字典（保持向后兼容接口）"""
    _ensure_setup()  # 首次加载时检测配置
    provider = _get_env("LLM_PROVIDER", "mmx-cli")
    timeout = int(_get_env("LLM_TIMEOUT", "180"))

    cfg = {
        "provider": provider,
        "timeout": timeout,
        "retry": {
            "enabled": _get_env("LLM_RETRY_ENABLED", "false").lower() == "true",
            "max_attempts": int(_get_env("LLM_RETRY_MAX_ATTEMPTS", "1")),
            "delay_seconds": int(_get_env("LLM_RETRY_DELAY", "3"))
        }
    }

    if provider == "mmx-cli":
        cfg["mmx"] = {
            "token_plan_key": _get_env("MMX_TOKEN_PLAN_KEY", ""),
        }
    elif provider == "openai":
        cfg["openai"] = {
            "base_url": _get_env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "api_key": _get_env("OPENAI_API_KEY", ""),
            "model": _get_env("OPENAI_MODEL", "gpt-4o")
        }
    elif provider == "openrouter":
        cfg["openai"] = {
            "base_url": _get_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            "api_key": _get_env("OPENROUTER_API_KEY", ""),
            "model": _get_env("OPENROUTER_MODEL", "google/gemini-3.1-flash")
        }
    elif provider == "azure":
        cfg["openai"] = {
            "base_url": _get_env("AZURE_OPENAI_BASE_URL", ""),
            "api_key": _get_env("AZURE_OPENAI_API_KEY", ""),
            "model": _get_env("AZURE_OPENAI_DEPLOYMENT", "")
        }
    elif provider == "google":
        cfg["openai"] = {
            "base_url": _get_env("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
            "api_key": _get_env("GOOGLE_API_KEY", ""),
            "model": _get_env("GOOGLE_MODEL", "gemini-2.0-flash")
        }
    elif provider == "dashscope":
        cfg["openai"] = {
            "base_url": _get_env("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"),
            "api_key": _get_env("DASHSCOPE_API_KEY", ""),
            "model": _get_env("DASHSCOPE_MODEL", "qwen-plus")
        }
    elif provider == "zai":
        cfg["openai"] = {
            "base_url": _get_env("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4"),
            "api_key": _get_env("ZAI_API_KEY", ""),
            "model": _get_env("ZAI_MODEL", "glm-z1")
        }
    elif provider == "minimax":
        cfg["openai"] = {
            "base_url": _get_env("MINIMAX_HTTP_BASE_URL", _get_env("MINIMAX_BASE_URL", "https://api.minimaxi.com")),
            "api_key": _get_env("MINIMAX_HTTP_API_KEY", _get_env("MINIMAX_API_KEY", "")),
            "model": _get_env("MINIMAX_HTTP_MODEL", _get_env("MINIMAX_MODEL", "MiniMax-M2.7"))
        }

    return cfg


# ===== 辅助函数 =====

def _render_items(items, field_specs=None):
    """
    将 items 列表渲染为可嵌入 prompt 的文本。

    Args:
        items: list[dict]
        field_specs: dict[field_name, label]，指定每个字段的标签名。
                      例如：{"title": "名称", "description": "描述"}
                      默认：{"title": "", "description": ""}（直接输出原始值）

    Returns:
        str，例如：
        "[0] 名称：Cursor | 描述：AI-first code editor"
        "[1] 名称：Claude | 描述：Anthropic's AI assistant"
    """
    if not items:
        return ""
    specs = field_specs or {}

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


def _strip_code_fences(raw):
    """去掉 markdown code fences，返回纯净内容"""
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    return raw


def parse_json(raw, expected_count=None, list_mode=True):
    """
    解析 JSON，支持两种模式：
    - list_mode=True：期望 JSON 数组
    - list_mode=False：期望 JSON 对象

    Args:
        raw: str，API 返回的原始文本
        expected_count: int，期望的元素数量（用于校验）
        list_mode: bool

    Returns:
        parsed data 或 None
    """
    raw = _strip_code_fences(raw)

    # 先尝试直接解析
    try:
        data = json.loads(raw)
        if list_mode:
            if isinstance(data, list):
                if expected_count and len(data) != expected_count:
                    print(f"[llm-tasks] 数量不匹配：期望 {expected_count}，实际 {len(data)}", file=sys.stderr)
                return data
        else:
            if isinstance(data, dict):
                return data
        return None
    except json.JSONDecodeError:
        pass

    # 正则提取 JSON
    pattern = r"\[.*\]" if list_mode else r"\{.*\}"
    m = re.search(pattern, raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


# ===== LLM 调用（多 Provider 支持） =====

def _call_mmx_cli(prompt, api_key, timeout):
    """执行 mmx-cli text chat，返回 (success, raw_output)"""
    env = {}
    if api_key:
        env["MINIMAX_API_KEY"] = api_key
    cmd = [
        "mmx", "text", "chat",
        "--message", prompt,
        "--output", "text"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env={**os.environ, **env} if env else None)
    except subprocess.TimeoutExpired:
        return False, f"mmx-cli timeout after {timeout}s"
    except Exception as e:
        return False, str(e)
    if result.returncode != 0 or not result.stdout.strip():
        return False, result.stderr or "no output"
    return True, result.stdout.strip()


def _call_openai_compat(prompt, base_url, api_key, model, timeout):
    """通过 OpenAI 兼容 API 调用，返回 (success, raw_output)"""
    try:
        import requests
    except ImportError:
        print("[llm-tasks] 缺少 requests 库，请运行: pip install requests", file=sys.stderr)
        return False, "requests not installed"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return False, "empty response"
        return True, content
    except requests.exceptions.Timeout:
        return False, "request timeout"
    except Exception as e:
        return False, str(e)


def _call_llm(prompt, model=None, timeout=None):
    """
    统一调用入口，根据 LLM_PROVIDER 环境变量选择 provider。
    返回 (success, raw_output)
    """
    cfg = _load_config()
    provider = cfg.get("provider", "mmx-cli")
    timeout = timeout or cfg.get("timeout", 180)

    if provider == "mmx-cli":
        mmx_cfg = cfg.get("mmx", {})
        mmx_api_key = mmx_cfg.get("token_plan_key", "")
        return _call_mmx_cli(prompt, mmx_api_key, timeout)
    elif provider in ("openai", "openrouter", "azure", "google", "dashscope", "zai", "minimax"):
        openai_cfg = cfg.get("openai", {})
        base_url = openai_cfg.get("base_url", "https://api.openai.com/v1")
        api_key = openai_cfg.get("api_key", "")
        openai_model = model or openai_cfg.get("model", "gpt-4o")
        return _call_openai_compat(prompt, base_url, api_key, openai_model, timeout)
    else:
        return False, f"unknown provider: {provider}"


# ===== 核心接口 =====

def batch_task(prompt_template, items, output_format="json-array",
               model=None, timeout=None, field_specs=None):
    """
    通用 LLM 批量任务生成。

    Args:
        prompt_template: str，包含占位符 {items_text} 的 prompt
        items: list[dict]，将被渲染到 {items_text} 位置
        output_format: "json-array" | "json-object"
        model: str，默认从配置读取
        timeout: int（秒），默认从配置读取
        field_specs: dict，用于渲染 items 的字段规格

    Returns:
        list[dict]（output_format=json-array）或 dict（output_format=json-object）
        失败返回 None
    """
    cfg = _load_config()
    timeout = timeout or cfg.get("timeout", 180)
    list_mode = (output_format == "json-array")

    # 渲染 items_text
    items_text = _render_items(items, field_specs)
    prompt = prompt_template.replace("{items_text}", items_text)

    # 批量调用
    success, raw = _call_llm(prompt, model=model, timeout=timeout)
    if success:
        data = parse_json(raw, expected_count=len(items) if list_mode else None,
                          list_mode=list_mode)
        if data:
            return data

    # 降级：逐条调用
    retry_cfg = cfg.get("retry", {})
    if not retry_cfg.get("enabled", False):
        return None

    print(f"[llm-tasks] 批量调用失败，尝试逐条调用（{len(items)} 条）...", file=sys.stderr)
    results = []
    for i, item in enumerate(items):
        item_text = _render_items([item], field_specs)
        single_prompt = prompt_template.replace("{items_text}", item_text)
        ok, raw = _call_llm(single_prompt, model=model, timeout=timeout)
        if ok:
            data = parse_json(raw, list_mode=list_mode)
            if data:
                results.append(data[0] if list_mode and isinstance(data, list) else data)
                continue
        print(f"[llm-tasks] 逐条调用失败 [{i}]: {item.get('title', item)}", file=sys.stderr)
        time.sleep(3)

    return results if results else None


def chat(prompt, model=None, timeout=None):
    """
    简单的单次对话调用。

    Args:
        prompt: str
        model: str，默认从配置读取
        timeout: int，默认从配置读取

    Returns:
        str，模型回复的原始文本；失败返回 None
    """
    success, raw = _call_llm(prompt, model=model, timeout=timeout)
    return raw if success else None


# ===== 入口（直接运行测试） =====

if __name__ == "__main__":
    _ensure_setup()
    print("llm-tasks skill")
    cfg = _load_config()
    provider = cfg.get("provider", "mmx-cli")
    print(f"Provider: {provider}")
    print(f"超时: {cfg.get('timeout')}s")
    print(f"逐条降级: {cfg.get('retry', {}).get('enabled')}")

    # 测试 chat 接口
    print("\n测试 chat 接口...")
    result = chat("用一句话解释 Python 是什么")
    if result:
        print(f"✓ chat 正常: {result[:80]}...")
    else:
        print("✗ chat 失败")
