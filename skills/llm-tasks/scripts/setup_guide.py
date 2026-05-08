#!/usr/bin/env python3
"""
llm-tasks skill — 交互式配置向导
首次运行或配置不完整时引导用户完成设置
"""
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
ENV_FILE = SKILL_DIR / ".env"


def _print_banner():
    print()
    print("\033[36m╔══════════════════════════════════════════════════════╗\033[0m")
    print("\033[36m║         🤖 LLM Tasks 初始化向导                         ║\033[0m")
    print("\033[36m╚══════════════════════════════════════════════════════╝\033[0m")
    print()


def _print_provider_menu():
    print("\033[1m请选择 LLM 提供商：\033[0m")
    print()
    options = [
        ("1", "MiniMax CLI", "适合已订阅 MMX Token Plan 的用户，需填写 Token Plan Key", ["MMX_TOKEN_PLAN_KEY"]),
        ("2", "OpenAI", "GPT-4o、GPT-4o-mini 等", ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]),
        ("3", "OpenRouter", "聚合 Claude、Gemini、Mistral 等数十种模型", ["OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL"]),
        ("4", "Azure OpenAI", "企业用户，稳定性高", ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_BASE_URL", "AZURE_OPENAI_DEPLOYMENT"]),
        ("5", "Google AI (Gemini)", "Gemini 系列模型", ["GOOGLE_API_KEY", "GOOGLE_BASE_URL", "GOOGLE_MODEL"]),
        ("6", "DashScope (阿里通义)", "Qwen、通义等", ["DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "DASHSCOPE_MODEL"]),
        ("7", "Zhipu AI (智谱)", "GLM 系列模型", ["ZAI_API_KEY", "ZAI_BASE_URL", "ZAI_MODEL"]),
        ("8", "MiniMax HTTP API", "直接调用 MiniMax API（非 CLI）", ["MINIMAX_HTTP_API_KEY", "MINIMAX_HTTP_BASE_URL", "MINIMAX_HTTP_MODEL"]),
        ("0", "稍后配置", "跳过，仅生成 .env 文件，稍后手动填写", []),
    ]
    for num, name, desc, _ in options:
        print(f"  \033[33m[{num}]\033[0m {name}")
        print(f"      {desc}")
        print()
    return options


def _read_env():
    """读取现有 .env 内容（如果存在）"""
    if not ENV_FILE.exists():
        return {}
    cfg = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


def _looks_placeholder(value):
    if not value:
        return True
    value = str(value).strip().lower()
    return (
        value.startswith("your-")
        or value in {"sk-...", "sk-or-...", "changeme", "todo", "xxx"}
        or "your-" in value
        or "example" in value
        or value.endswith("-here")
    )


def _write_env(cfg):
    """写入 .env 文件"""
    lines = [
        "#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "# llm-tasks 配置",
        "# 由 setup_guide.py 自动生成",
        "#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"LLM_PROVIDER={cfg.get('LLM_PROVIDER', '')}",
        f"LLM_TIMEOUT={cfg.get('LLM_TIMEOUT', '180')}",
        f"SETUP_COMPLETED={cfg.get('SETUP_COMPLETED', 'false')}",
        "",
    ]
    provider = cfg.get("LLM_PROVIDER", "")
    if provider == "mmx-cli":
        lines += [
            "# MiniMax CLI（模型固定为 MiniMax-M2.7；填写 MMX Token Plan Key，不是普通 MiniMax API Key）",
            f"MMX_TOKEN_PLAN_KEY={cfg.get('MMX_TOKEN_PLAN_KEY', '')}",
        ]
    elif provider == "openai":
        lines += [
            "# OpenAI",
            f"OPENAI_API_KEY={cfg.get('OPENAI_API_KEY', '')}",
            f"OPENAI_BASE_URL={cfg.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')}",
            f"OPENAI_MODEL={cfg.get('OPENAI_MODEL', 'gpt-4o')}",
        ]
    elif provider == "openrouter":
        lines += [
            "# OpenRouter",
            f"OPENROUTER_API_KEY={cfg.get('OPENROUTER_API_KEY', '')}",
            f"OPENROUTER_BASE_URL={cfg.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')}",
            f"OPENROUTER_MODEL={cfg.get('OPENROUTER_MODEL', 'google/gemini-3.1-flash')}",
        ]
    elif provider == "azure":
        lines += [
            "# Azure OpenAI",
            f"AZURE_OPENAI_API_KEY={cfg.get('AZURE_OPENAI_API_KEY', '')}",
            f"AZURE_OPENAI_BASE_URL={cfg.get('AZURE_OPENAI_BASE_URL', '')}",
            f"AZURE_OPENAI_DEPLOYMENT={cfg.get('AZURE_OPENAI_DEPLOYMENT', '')}",
        ]
    elif provider == "google":
        lines += [
            "# Google AI",
            f"GOOGLE_API_KEY={cfg.get('GOOGLE_API_KEY', '')}",
            f"GOOGLE_BASE_URL={cfg.get('GOOGLE_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')}",
            f"GOOGLE_MODEL={cfg.get('GOOGLE_MODEL', 'gemini-2.0-flash')}",
        ]
    elif provider == "dashscope":
        lines += [
            "# DashScope",
            f"DASHSCOPE_API_KEY={cfg.get('DASHSCOPE_API_KEY', '')}",
            f"DASHSCOPE_BASE_URL={cfg.get('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/api/v1')}",
            f"DASHSCOPE_MODEL={cfg.get('DASHSCOPE_MODEL', 'qwen-plus')}",
        ]
    elif provider == "zai":
        lines += [
            "# Zhipu AI",
            f"ZAI_API_KEY={cfg.get('ZAI_API_KEY', '')}",
            f"ZAI_BASE_URL={cfg.get('ZAI_BASE_URL', 'https://api.z.ai/api/paas/v4')}",
            f"ZAI_MODEL={cfg.get('ZAI_MODEL', 'glm-z1')}",
        ]
    elif provider == "minimax":
        lines += [
            "# MiniMax HTTP API",
            f"MINIMAX_HTTP_API_KEY={cfg.get('MINIMAX_HTTP_API_KEY', '')}",
            f"MINIMAX_HTTP_BASE_URL={cfg.get('MINIMAX_HTTP_BASE_URL', 'https://api.minimaxi.com')}",
            f"MINIMAX_HTTP_MODEL={cfg.get('MINIMAX_HTTP_MODEL', 'MiniMax-M2.7')}",
        ]

    lines.append("")
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines))


def _is_setup_completed():
    """检查用户是否已完成初始化向导"""
    val = _get_env("SETUP_COMPLETED", "")
    return val.lower() == "true"


def _mark_setup_completed(provider):
    """在 .env 文件中标记向导已完成，并保存用户选择的 provider"""
    # 读取现有内容，保留其他字段
    existing = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    # 标记完成
    existing["SETUP_COMPLETED"] = "true"
    existing["LLM_PROVIDER"] = provider
    _write_env(existing)


def _ask_api_key(provider):
    """询问并验证 API Key"""
    prompts = {
        "mmx-cli": ("MMX Token Plan Key（mmx-cli 专用，需先订阅 MMX Token Plan；不是普通 MiniMax API Key）", "MMX_TOKEN_PLAN_KEY", ""),
        "openai": ("OpenAI API Key", "OPENAI_API_KEY", "sk-..."),
        "openrouter": ("OpenRouter API Key", "OPENROUTER_API_KEY", "sk-or-..."),
        "azure": ("Azure OpenAI API Key", "AZURE_OPENAI_API_KEY", ""),
        "google": ("Google AI API Key", "GOOGLE_API_KEY", ""),
        "dashscope": ("DashScope API Key", "DASHSCOPE_API_KEY", ""),
        "zai": ("Zhipu AI API Key", "ZAI_API_KEY", ""),
        "minimax": ("MiniMax HTTP API Key", "MINIMAX_HTTP_API_KEY", ""),
    }
    prompt_text, key_name, placeholder = prompts.get(provider, ("API Key", "API_KEY", ""))
    while True:
        val = input(f"\033[33m{prompt_text}\033[0m\n（直接回车跳过，稍后手动填写）\n> ").strip()
        if val == "":
            return ""
        if len(val) < 8:
            print(f"\033[31m✗ API Key 太短，请检查后重新输入\033[0m")
            continue
        return val


def _confirm_and_save(cfg):
    """确认并保存配置"""
    print()
    print("\033[1m📋 配置摘要\033[0m")
    print(f"  提供商：\033[36m{cfg.get('LLM_PROVIDER')}\033[0m")

    provider = cfg.get("LLM_PROVIDER")
    key_labels = {
        "mmx-cli": ("MMX_TOKEN_PLAN_KEY", "Token Plan Key"),
        "openai": ("OPENAI_API_KEY", "API Key"),
        "openrouter": ("OPENROUTER_API_KEY", "API Key"),
        "azure": ("AZURE_OPENAI_API_KEY", "API Key"),
        "google": ("GOOGLE_API_KEY", "API Key"),
        "dashscope": ("DASHSCOPE_API_KEY", "API Key"),
        "zai": ("ZAI_API_KEY", "API Key"),
        "minimax": ("MINIMAX_HTTP_API_KEY", "API Key"),
    }
    if provider in key_labels:
        key_name, key_label = key_labels[provider]
        val = cfg.get(key_name, "")
        if val:
            print(f"  {key_label}：\033[32m已配置\033[0m")
        else:
            print(f"  {key_label}：\033[31m未配置（稍后需手动填写）\033[0m")

    print()
    while True:
        ans = input("确认保存到 .env 文件？[Y/n] ").strip().lower()
        if ans in ("", "y", "yes"):
            break
        if ans in ("n", "no"):
            print("\033[33m已取消，未写入文件\033[0m")
            return False

    cfg["SETUP_COMPLETED"] = "true"
    _write_env(cfg)
    print(f"\033[32m✓ 已保存到 {ENV_FILE}\033[0m")
    print("\033[33m！请确保该文件不被提交到 GitHub（.gitignore 已忽略 .env*）\033[0m")
    print("\033[36m！后续如需重新配置，运行：python setup_guide.py\033[0m")
    return True


def run_wizard():
    """运行交互式向导"""
    _print_banner()

    # 读取现有配置
    existing = _read_env()
    current_provider = existing.get("LLM_PROVIDER", "")

    # 如果已有完整配置，提示用户
    if current_provider:
        key_map = {
            "mmx-cli": "MMX_TOKEN_PLAN_KEY", "openai": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY", "azure": "AZURE_OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY", "dashscope": "DASHSCOPE_API_KEY",
            "zai": "ZAI_API_KEY", "minimax": "MINIMAX_HTTP_API_KEY",
        }
        key_name = key_map.get(current_provider, "")
        has_key = bool(existing.get(key_name, "") and not _looks_placeholder(existing.get(key_name, "")))
        if has_key:
            print(f"\033[32m✓ 已检测到 {key_name}\033[0m")
            print(f"  提供商：{current_provider}")
            print(f"  配置文件：{ENV_FILE}")
            print()
            ans = input("重新运行配置向导？[y/N] ").strip().lower()
            if ans not in ("y", "yes"):
                print("\033[33m取消，直接使用现有配置\033[0m")
                return True

    # 显示菜单
    options = _print_provider_menu()

    # 选择
    while True:
        ans = input("\033[36m请输入选项 [0-8]：\033[0m ").strip()
        if ans.isdigit() and 0 <= int(ans) <= 8:
            break
        print("\033[31m请输入 0-8 之间的数字\033[0m")

    choice = int(ans)
    if choice == 0:
        print("\033[33m已选择「稍后配置」\033[0m")
        print("将创建空白 .env 文件，下次运行时会再次提示")
        print(f"如需立即配置，运行：python {__file__}")
        # 创建空白 .env（SETUP_COMPLETED 不设置，这样下次还会提示）
        _write_env({"LLM_PROVIDER": "mmx-cli"})
        return True

    # 建立选项映射（显示编号 → provider id）
    provider_map = {
        1: "mmx-cli", 2: "openai", 3: "openrouter", 4: "azure",
        5: "google", 6: "dashscope", 7: "zai", 8: "minimax"
    }
    provider = provider_map.get(choice, "mmx-cli")

    # 构建配置
    cfg = {
        "LLM_PROVIDER": provider,
        "LLM_TIMEOUT": "180",
    }

    # 询问 API Key
    api_key = _ask_api_key(provider)
    if api_key:
        key_map = {
            "mmx-cli": "MMX_TOKEN_PLAN_KEY", "openai": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY", "azure": "AZURE_OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY", "dashscope": "DASHSCOPE_API_KEY",
            "zai": "ZAI_API_KEY", "minimax": "MINIMAX_HTTP_API_KEY",
        }
        key_name = key_map[provider]
        cfg[key_name] = api_key

    _confirm_and_save(cfg)
    return True


def check_and_guide():
    """
    入口：检测配置是否完整，不完整则运行向导。
    直接 import时自动调用。
    """
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        # 有 .env 文件，快速检查关键字段
        cfg = _read_env()
        provider = cfg.get("LLM_PROVIDER", "")
        if provider:
            key_map = {
                "mmx-cli": "MMX_TOKEN_PLAN_KEY", "openai": "OPENAI_API_KEY",
                "openrouter": "OPENROUTER_API_KEY", "azure": "AZURE_OPENAI_API_KEY",
                "google": "GOOGLE_API_KEY", "dashscope": "DASHSCOPE_API_KEY",
                "zai": "ZAI_API_KEY", "minimax": "MINIMAX_HTTP_API_KEY",
            }
            key_name = key_map.get(provider, "")
            if key_name and cfg.get(key_name, "") and not _looks_placeholder(cfg.get(key_name, "")):
                # 配置完整，不需要引导
                return True

    # 配置不完整或不存在，运行向导
    return run_wizard()


if __name__ == "__main__":
    # 手动运行：python setup_guide.py
    run_wizard()
