#!/usr/bin/env python3
"""
feishu-doc skill — 交互式配置向导
引导用户完成飞书文档和消息发送的配置
"""
import os
import sys
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
ENV_FILE = SKILL_DIR / ".env.feishu"


def _print_banner():
    print()
    print("\033[36m╔══════════════════════════════════════════════════════╗\033[0m")
    print("\033[36m║         📄 Feishu Doc 初始化向导                      ║\033[0m")
    print("\033[36m╚══════════════════════════════════════════════════════╝\033[0m")
    print()


def _check_lark_cli():
    """检查 lark-cli 是否已配置"""
    try:
        result = subprocess.run(
            ["lark-cli", "config", "show"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and "appId" in result.stdout:
            try:
                import json
                cfg = json.loads(result.stdout)
                return True, cfg.get("brand", "feishu")
            except:
                return True, "feishu"
    except Exception:
        pass
    return False, None


def _read_env():
    """读取现有 .env.feishu"""
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


def _write_env(cfg):
    """写入 .env.feishu 文件"""
    lines = [
        "#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "# 飞书配置",
        "# 由 setup_guide.py 自动生成",
        "# 所有敏感信息不要提交到 GitHub",
        "# .gitignore 已忽略 .env.feishu",
        "#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "# 安装完成标志（勿删）",
        f"SETUP_COMPLETED={cfg.get('SETUP_COMPLETED', 'false')}",
        "",
        "#━━━ 文档创建（二选一）━━━",
        "#",
        "# 【知识库模式】",
        "#   用途：把日报创建到飞书知识库中，适合长期沉淀。",
        "#   FEISHU_WIKI_SPACE_ID：目标知识库 ID。",
        "#     获取方式：浏览器打开飞书知识库首页，查看 URL 中的 wiki space 标识。",
        "#     如果使用个人知识库，lark-cli 支持的特殊值通常是 my_library。",
        "#   FEISHU_PARENT_NODE_TOKEN：可选，目标父节点/目录 token。",
        "#     获取方式：打开知识库中的目标目录或页面，查看 URL 中 node= 后面的值。",
        "#     留空时通常创建在知识库根目录。",
        f"FEISHU_WIKI_SPACE_ID={cfg.get('FEISHU_WIKI_SPACE_ID', '')}",
        f"FEISHU_PARENT_NODE_TOKEN={cfg.get('FEISHU_PARENT_NODE_TOKEN', '')}",
        "",
        "# 【文件夹模式】",
        "#   用途：把日报创建到飞书云文档文件夹中，适合个人空间/共享文件夹。",
        "#   FEISHU_FOLDER_TOKEN：目标文件夹 token。",
        "#     获取方式：浏览器打开目标文件夹，复制 URL 中 /folder/ 后面的字符。",
        "#   注意：如果同时配置文件夹模式和知识库模式，代码优先使用文件夹模式。",
        f"FEISHU_FOLDER_TOKEN={cfg.get('FEISHU_FOLDER_TOKEN', '')}",
        "",
        "#━━━ 消息发送（二选一）━━━",
        "#",
        "# 【群聊】",
        "#   用途：日报生成后，把摘要和文档链接推送到飞书群。",
        "#   FEISHU_CHAT_ID：群聊 open_chat_id，通常以 oc_ 开头。",
        "#     获取方式：运行 lark-cli im chats list --as user，找到目标群的 chat_id。",
        "#     也可以运行 lark-cli im +chat-search --as user --query \"群名\" 搜索。",
        "#     或在飞书 Desktop 的群设置中复制群 ID。",
        f"FEISHU_CHAT_ID={cfg.get('FEISHU_CHAT_ID', '')}",
        "",
        "# 【私聊】",
        "#   用途：日报生成后，把摘要和文档链接推送给某个用户。",
        "#   FEISHU_USER_ID：用户 open_id，通常以 ou_ 开头。",
        "#     获取方式：运行 lark-cli contact +search-user \"姓名\"，找到 ou_ 开头的 ID。",
        "#     或在飞书 Desktop 中打开联系人信息并复制用户 ID。",
        "#   注意：消息发送目标二选一即可。若同时配置，发送逻辑会按代码规则选择目标。",
        f"FEISHU_USER_ID={cfg.get('FEISHU_USER_ID', '')}",
        "",
        "# FEISHU_SEND_AS：消息发送身份，user 或 bot。",
        "#   默认 user：使用当前 lark-cli 登录用户发送，适合个人自动化和未把 bot 拉进群的场景。",
        "#   选择 bot：需要应用机器人已经加入目标群，否则飞书会返回 Bot/User can NOT be out of the chat。",
        f"FEISHU_SEND_AS={cfg.get('FEISHU_SEND_AS', 'user')}",
    ]
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


def _print_doc_mode_guide():
    """打印文档创建模式说明"""
    print("\033[1m请选择文档创建方式：\033[0m")
    print()
    print("  \033[33m[1]\033[0m 知识库模式（推荐）")
    print("      文档集中在知识库里，有目录结构，适合沉淀内容")
    print("      需要先在飞书 App 创建知识库，获取 space_id 和父节点 token")
    print()
    print("  \033[33m[2]\033[0m 文件夹模式（我的空间）")
    print("      普通飞书文档，像在飞书云文档里创建一样")
    print("      直接用飞书账号登录即可，无需额外创建知识库")
    print()
    print("  \033[33m[3]\033[0m 不创建飞书文档（仅生成 .md 文件）")
    print()


def _print_msg_mode_guide():
    """打印消息发送模式说明"""
    print("\033[1m请选择消息发送方式：\033[0m")
    print()
    print("  \033[33m[1]\033[0m 群聊")
    print("      发送到飞书群组，需要 oc_ 格式的 chat_id")
    print("      获取方式：lark-cli im chats list --as user")
    print()
    print("  \033[33m[2]\033[0m 私聊")
    print("      发送给自己或其他用户，需要 ou_ 格式的 user_id")
    print("      获取方式：lark-cli contact +search-user \"姓名\"")
    print()
    print("  \033[33m[3]\033[0m 不发送消息（仅生成文档）")
    print()


def _ask_doc_config(cfg):
    """询问并验证文档配置"""
    print()
    print("\033[36m━━━ 文档创建配置 ━━━\033[0m")
    _print_doc_mode_guide()

    while True:
        ans = input("请选择 [1/2/3]：").strip()
        if ans in ("1", "2", "3"):
            break
        print("\033[31m请输入 1、2 或 3\033[0m")

    if ans == "1":
        print("\n\033[33m请提供知识库信息：\033[0m")
        while True:
            space_id = input("space_id（知识库 ID）：").strip()
            if space_id:
                break
            print("\033[31mspace_id 不能为空\033[0m")
        parent_token = input("parent_node_token（父节点 token，可回车跳过）：").strip()
        cfg["FEISHU_WIKI_SPACE_ID"] = space_id
        cfg["FEISHU_PARENT_NODE_TOKEN"] = parent_token
        cfg.pop("FEISHU_FOLDER_TOKEN", None)

    elif ans == "2":
        print("\n\033[33m请提供文件夹信息：\033[0m")
        while True:
            folder_token = input("folder_token（文件夹 token）：").strip()
            if folder_token:
                break
            print("\033[31mfolder_token 不能为空\033[0m")
        cfg["FEISHU_FOLDER_TOKEN"] = folder_token
        cfg.pop("FEISHU_WIKI_SPACE_ID", None)
        cfg.pop("FEISHU_PARENT_NODE_TOKEN", None)

    else:  # ans == "3"
        cfg.pop("FEISHU_WIKI_SPACE_ID", None)
        cfg.pop("FEISHU_PARENT_NODE_TOKEN", None)
        cfg.pop("FEISHU_FOLDER_TOKEN", None)

    return cfg


def _ask_msg_config(cfg):
    """询问并验证消息配置"""
    print()
    print("\033[36m━━━ 消息发送配置 ━━━\033[0m")
    _print_msg_mode_guide()

    while True:
        ans = input("请选择 [1/2/3]：").strip()
        if ans in ("1", "2", "3"):
            break
        print("\033[31m请输入 1、2 或 3\033[0m")

    if ans == "1":
        print("\n\033[33m请提供群聊信息：\033[0m")
        print("提示：运行 \033[36mlark-cli im chats list --as user\033[0m 查看可见群")
        while True:
            chat_id = input("chat_id（oc_ 开头）：").strip()
            if chat_id.startswith("oc_"):
                break
            if not chat_id:
                print("\033[31mchat_id 不能为空\033[0m")
                continue
            print("\033[33m⚠ chat_id 应以 oc_ 开头，请确认是否输入正确\033[0m")
            break
        cfg["FEISHU_CHAT_ID"] = chat_id
        cfg.pop("FEISHU_USER_ID", None)

    elif ans == "2":
        print("\n\033[33m请提供私聊信息：\033[0m")
        print("提示：运行 \033[36mlark-cli contact +search-user \"姓名\"\033[0m 查找用户 ID")
        while True:
            user_id = input("user_id（ou_ 开头）：").strip()
            if user_id.startswith("ou_"):
                break
            if not user_id:
                print("\033[31muser_id 不能为空\033[0m")
                continue
            print("\033[33m⚠ user_id 应以 ou_ 开头，请确认是否输入正确\033[0m")
            break
        cfg["FEISHU_USER_ID"] = user_id
        cfg.pop("FEISHU_CHAT_ID", None)

    else:  # ans == "3"
        cfg.pop("FEISHU_CHAT_ID", None)
        cfg.pop("FEISHU_USER_ID", None)

    return cfg


def _confirm_and_save(cfg):
    """确认并保存配置"""
    print()
    print("\033[1m📋 配置摘要\033[0m")

    wiki_id = cfg.get("FEISHU_WIKI_SPACE_ID", "")
    parent_token = cfg.get("FEISHU_PARENT_NODE_TOKEN", "")
    folder_token = cfg.get("FEISHU_FOLDER_TOKEN", "")
    chat_id = cfg.get("FEISHU_CHAT_ID", "")
    user_id = cfg.get("FEISHU_USER_ID", "")

    if wiki_id or parent_token:
        print(f"  文档创建：\033[36m知识库模式\033[0m")
        print(f"    space_id：{wiki_id or '(未填)'}")
        print(f"    parent_node_token：{parent_token or '(未填)'}")
    elif folder_token:
        print(f"  文档创建：\033[36m文件夹模式\033[0m")
        print(f"    folder_token：{folder_token}")
    else:
        print(f"  文档创建：\033[33m不创建飞书文档\033[0m")

    print()
    if chat_id:
        print(f"  消息发送：\033[36m群聊\033[0m")
        print(f"    chat_id：{chat_id}")
    elif user_id:
        print(f"  消息发送：\033[36m私聊\033[0m")
        print(f"    user_id：{user_id}")
    else:
        print(f"  消息发送：\033[33m不发送消息\033[0m")

    print()
    while True:
        ans = input("确认保存？[Y/n] ").strip().lower()
        if ans in ("", "y", "yes"):
            break
        if ans in ("n", "no"):
            print("\033[33m已取消\033[0m")
            return False

    _write_env(cfg)
    cfg["SETUP_COMPLETED"] = "true"
    _write_env(cfg)
    print(f"\n\033[32m✓ 已保存到 {ENV_FILE}\033[0m")
    print("\033[33m！请确保该文件不被提交到 GitHub（.gitignore 已忽略 .env.feishu）\033[0m")
    print("\033[36m！后续如需重新配置，运行：python setup_guide.py\033[0m")
    return True


def check_and_guide():
    """检测配置，完成过向导则跳过，否则运行向导"""
    if not ENV_FILE.exists():
        print("\033[33m⚠ 飞书未配置，开始引导...\033[0m")
        run_wizard()
        return True

    cfg = _read_env()
    if cfg.get("SETUP_COMPLETED", "").lower() == "true":
        return True

    print("\033[33m⚠ 飞书配置未完成，开始引导...\033[0m")
    run_wizard()
    return True


def run_wizard():
    """运行交互式向导"""
    _print_banner()

    # 检查 lark-cli
    lark_ok, lark_brand = _check_lark_cli()
    if lark_ok:
        print(f"\033[32m✓ lark-cli 已配置\033[0m（品牌：{lark_brand}）")
    else:
        print("\033[31m✗ lark-cli 未配置或未初始化\033[0m")
        print("  请先运行：\033[36mlark-cli config init\033[0m")
        print("  或参考：https://github.com/youquto/lark-cli")
        print()

    # 读取现有配置
    cfg = _read_env()

    # 询问文档配置
    cfg = _ask_doc_config(cfg)

    # 询问消息配置
    cfg = _ask_msg_config(cfg)

    # 确认保存
    _confirm_and_save(cfg)

    # 总结
    print()
    print("\033[1m✨ 初始化完成！\033[0m")
    print()
    print("后续使用：")
    if not cfg.get("FEISHU_WIKI_SPACE_ID") and not cfg.get("FEISHU_FOLDER_TOKEN"):
        print("  · 当前配置不创建飞书文档，仅生成 .md 文件")
    if not cfg.get("FEISHU_CHAT_ID") and not cfg.get("FEISHU_USER_ID"):
        print("  · 当前配置不发送飞书消息")
    print(f"  · 配置文件：{ENV_FILE}")
    print(f"  · 重新运行向导：python {__file__}")


def check_and_guide():
    """
    入口：检测配置，不完整则运行向导。
    被 feishu_doc.py 导入时自动调用。
    """
    env_file = Path(__file__).parent.parent / ".env.feishu"
    if env_file.exists():
        cfg = _read_env()
        # 有文档配置 或 有消息配置 → 配置有效
        has_doc = bool(cfg.get("FEISHU_WIKI_SPACE_ID") or cfg.get("FEISHU_FOLDER_TOKEN"))
        has_msg = bool(cfg.get("FEISHU_CHAT_ID") or cfg.get("FEISHU_USER_ID"))
        # 至少有一项配置了（即使是空字符串也算配置了类型）
        # 这里宽松判断：有 .env.feishu 就不自动引导，除非用户主动运行
        if has_doc or has_msg:
            return True

    # 无配置或配置不完整
    print("\033[33m⚠ 飞书配置不完整，开始引导...\033[0m")
    run_wizard()
    return True


if __name__ == "__main__":
    run_wizard()
