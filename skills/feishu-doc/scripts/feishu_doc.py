#!/usr/bin/env python3
"""
feishu-doc skill — 飞书文档和知识库操作封装
基于 lark-cli 实现，从 .env.feishu 读取配置
首次运行或配置不完整时自动触发交互引导
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ===== 配置路径 =====

SKILL_DIR = Path(__file__).parent.parent
ENV_FILE = SKILL_DIR / ".env.feishu"
_CONFIG_CACHE = None


# ===== 环境变量加载 =====

def _get_env(key, default=None):
    """从 .env.feishu 读取配置项"""
    if not ENV_FILE.exists():
        return default
    with open(ENV_FILE) as f:
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
    """返回 .env.feishu 中的配置字典（带缓存）"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cfg = {
        "wiki_space_id": _get_env("FEISHU_WIKI_SPACE_ID", ""),
        "parent_node_token": _get_env("FEISHU_PARENT_NODE_TOKEN", ""),
        "folder_token": _get_env("FEISHU_FOLDER_TOKEN", ""),
        "chat_id": _get_env("FEISHU_CHAT_ID", ""),
        "user_id": _get_env("FEISHU_USER_ID", ""),
        "send_as": _get_env("FEISHU_SEND_AS", "user"),
    }
    _CONFIG_CACHE = cfg
    return cfg


def _invalidate_config_cache():
    """清除配置缓存（写入文件后调用）"""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None


# ===== 启动引导 =====

def _run_setup_guide():  # noqa: D103
    pass  # 已迁移到 check_and_guide()


def is_configured():
    """
    检查飞书是否已配置（文档创建 或 消息发送 至少有一项可用）
    返回 True 表示配置了且有效，False 表示未配置或仅部分配置
    """
    if not ENV_FILE.exists():
        return False
    cfg = _load_config()
    # 文档创建：wiki 模式 或 文件夹模式
    has_doc = bool(cfg.get("wiki_space_id") or cfg.get("folder_token"))
    # 消息发送：chat_id 或 user_id
    has_msg = bool(cfg.get("chat_id") or cfg.get("user_id"))
    return has_doc or has_msg


def check_and_guide(skip_guide=False):
    """
    入口：检测配置，完成过向导则跳过，否则运行向导。

    Args:
        skip_guide: True 时跳过引导，仅返回当前配置状态
    """
    if skip_guide:
        return True

    # 先检查是否已完成过
    if ENV_FILE.exists():
        cfg = _load_config()
        if cfg.get("SETUP_COMPLETED", "").lower() == "true":
            return True

    guide_path = Path(__file__).parent / "setup_guide.py"
    if guide_path.exists():
        try:
            import runpy
            runpy.run_path(str(guide_path), run_name="__main__")
        except SystemExit:
            pass
    return True


# ===== 辅助函数 =====

def _run_lark(args, check=True, cwd=None):
    """执行 lark-cli 命令，返回 parsed JSON 输出"""
    result = subprocess.run(
        ["lark-cli"] + args,
        capture_output=True,
        text=True,
        cwd=cwd or os.path.dirname(os.path.abspath(__file__))
    )
    if result.returncode != 0:
        if check:
            print(f"[feishu-doc] lark-cli error: {result.stderr}", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        if check:
            print(f"[feishu-doc] JSON parse error: {result.stdout}", file=sys.stderr)
        return None


def _is_success_response(resp):
    """兼容 lark-cli 的 {code: 0} 和 {ok: true} 两种成功格式。"""
    if not isinstance(resp, dict):
        return False
    return resp.get("code") == 0 or resp.get("ok") is True


# ===== 文档创建 =====

def _create_docx_in_folder(title, folder_token):
    """在文件夹（我的空间）中创建普通文档"""
    data = json.dumps({
        "title": title,
        "folder_token": folder_token
    })
    out = _run_lark([
        "docs", "+create",
        "--data", data
    ])
    if out is None:
        return None
    try:
        doc = out.get("data", {}).get("document", {})
        return {
            "token": doc.get("document_id", ""),
            "obj_token": doc.get("document_id", ""),
            "title": doc.get("title", title),
            "url": doc.get("url", "")
        }
    except (KeyError, TypeError):
        print(f"[feishu-doc] _create_docx_in_folder 解析失败: {out}", file=sys.stderr)
        return None


def _create_node_in_wiki(title):
    """在知识库中创建节点"""
    cfg = _load_config()
    space_id = cfg.get("wiki_space_id", "")
    parent = cfg.get("parent_node_token", "")

    if not space_id:
        raise ValueError("FEISHU_WIKI_SPACE_ID 未配置，请运行 ai-daily-news-v2 的 setup-feishu 动作配置")

    data = json.dumps({
        "node_type": "origin",
        "obj_type": "docx",
        "title": title,
        "parent_node_token": parent
    })
    params = json.dumps({"space_id": space_id})

    out = _run_lark([
        "wiki", "nodes", "create",
        "--params", params,
        "--data", data
    ])
    if out is None:
        return None
    try:
        node = out["data"]["node"]
        return {
            "token": node.get("node_token"),
            "obj_token": node.get("obj_token"),
            "title": node.get("title"),
            "url": node.get("url", "")
        }
    except (KeyError, TypeError):
        print(f"[feishu-doc] _create_node_in_wiki 解析失败: {out}", file=sys.stderr)
        return None


def create_node(title):
    """
    创建新文档（自动选择知识库模式或文件夹模式）

    Args:
        title: 文档标题

    Returns:
        dict，包含 {"token": ..., "obj_token": ..., "title": ..., "url": ...}
        失败返回 None
    """
    cfg = _load_config()
    folder_token = cfg.get("folder_token", "")

    if folder_token:
        # 文件夹模式（我的空间）
        return _create_docx_in_folder(title, folder_token)
    else:
        # 知识库模式
        return _create_node_in_wiki(title)


def node_exists(title):
    """
    检查文档是否已存在（仅知识库模式）

    Returns:
        bool
    """
    cfg = _load_config()
    folder_token = cfg.get("folder_token", "")
    if folder_token:
        # 文件夹模式不支持快速检测
        return False

    space_id = cfg.get("wiki_space_id", "")
    parent = cfg.get("parent_node_token", "")
    if not space_id:
        return False

    params = json.dumps({
        "space_id": space_id,
        "parent_node_token": parent
    })
    out = _run_lark(["wiki", "nodes", "list", "--params", params], check=False)
    if out is None:
        return False
    try:
        nodes = out.get("data", {}).get("items", [])
        return any(n.get("title") == title for n in nodes)
    except (KeyError, TypeError):
        return False


def find_node(title):
    """
    查找指定标题的文档（仅知识库模式）

    Returns:
        dict 或 None
    """
    cfg = _load_config()
    folder_token = cfg.get("folder_token", "")
    if folder_token:
        return None

    space_id = cfg.get("wiki_space_id", "")
    parent = cfg.get("parent_node_token", "")
    if not space_id:
        return None

    params = json.dumps({
        "space_id": space_id,
        "parent_node_token": parent
    })
    out = _run_lark(["wiki", "nodes", "list", "--params", params], check=False)
    if out is None:
        return None
    try:
        nodes = out.get("data", {}).get("items", [])
        for n in nodes:
            if n.get("title") == title:
                return {
                    "token": n.get("node_token"),
                    "obj_token": n.get("obj_token"),
                    "title": n.get("title"),
                    "url": n.get("url", "")
                }
        return None
    except (KeyError, TypeError):
        return None


# ===== 文档写入 =====

def write_doc(obj_token, content, mode="overwrite", retries=8, retry_delay=5):
    """
    写入文档内容。

    Args:
        obj_token: 文档 obj_token
        content: Markdown 格式内容
        mode: "overwrite"（覆盖）或 "append"（追加）

    Returns:
        bool，操作是否成功
    """
    for attempt in range(retries):
        out = _run_lark([
            "docs", "+update",
            "--doc", obj_token,
            "--markdown", content,
            "--mode", mode
        ], check=False)
        if out is not None:
            return True
        if attempt < retries - 1:
            time.sleep(retry_delay)
    return False


def read_doc(obj_token):
    """
    读取文档内容。

    Args:
        obj_token: 文档 obj_token

    Returns:
        str，文档原始内容；失败返回 None
    """
    out = _run_lark([
        "docs", "+read",
        "--doc", obj_token
    ], check=False)
    if out is None:
        return None
    try:
        return out.get("data", {}).get("content", "")
    except (KeyError, TypeError):
        return None


# ===== 媒体插入 =====

def insert_media(obj_token, file_path, media_type="audio"):
    """
    向文档插入媒体文件（音频、图片、视频）。

    Args:
        obj_token: 文档 obj_token
        file_path: 本地媒体文件路径
        media_type: "audio" | "image" | "video"

    Returns:
        bool，操作是否成功
    """
    if not os.path.exists(file_path):
        print(f"[feishu-doc] 文件不存在: {file_path}", file=sys.stderr)
        return False

    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.basename(file_path)
    local_copy_name = f"_media_{filename}"
    local_path = os.path.join(script_dir, local_copy_name)
    shutil.copy2(file_path, local_path)
    try:
        out = _run_lark([
            "docs", "+media-insert",
            "--doc", obj_token,
            "--file", local_copy_name,
            "--type", "file",
            "--file-view", "preview"
        ], cwd=script_dir, check=False)
        return out is not None
    finally:
        if os.path.exists(local_path):
            os.unlink(local_path)


# ===== 消息发送 =====

def _resolve_target(chat_id=None, user_id=None):
    """
    解析消息发送目标。

    优先级：显式参数 > .env.feishu 配置
    群聊（chat_id） 和 私聊（user_id） 互斥，只能填一种

    Returns:
        (target_id, is_private) 或 (None, None)

    Raises:
        ValueError: 未配置目标
    """
    cfg = _load_config()
    # chat_id 参数优先，其次 user_id 参数，最后用配置文件
    target = chat_id or user_id or cfg.get("chat_id") or cfg.get("user_id")
    is_private = False

    if not target:
        raise ValueError(
            "飞书消息发送目标未配置。\n"
            "请设置 FEISHU_CHAT_ID（群聊）或 FEISHU_USER_ID（私聊），\n"
            "或运行时传入 chat_id / user_id 参数"
        )

    # 判断是群聊还是私聊
    if target.startswith("oc_"):
        is_private = False
    elif target.startswith("ou_"):
        is_private = True
    else:
        # 尝试从配置文件判断
        if cfg.get("user_id"):
            is_private = True
        elif cfg.get("chat_id"):
            is_private = False
        else:
            raise ValueError(
                f"无法识别 ID 类型：{target}（应为 oc_ 开头或 ou_ 开头）"
            )

    return target, is_private


def send_message(chat_id=None, content="", msg_type="text", audio_path=None, user_id=None):
    """
    发送飞书消息（群聊或私聊）。

    Args:
        chat_id: 目标群 ID（oc_ 开头），优先级高于 user_id
        user_id: 目标用户 ID（ou_ 开头）
        content: 消息内容文本
        msg_type: "text" | "post"（目前只实现 text）
        audio_path: 可选，语音文件路径

    Returns:
        dict，lark-cli 返回的完整响应
        失败返回 {"code": -1, "msg": "..."}
    """
    target, is_private = _resolve_target(chat_id, user_id)
    send_as = _load_config().get("send_as") or "user"
    if send_as not in ("user", "bot"):
        send_as = "user"

    if audio_path and os.path.exists(audio_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_name = "_msg_audio.mp3"
        local_path = os.path.join(script_dir, local_name)
        shutil.copy2(audio_path, local_path)
        try:
            if is_private:
                out = _run_lark([
                    "im", "+messages-send",
                    "--user-id", target,
                    "--audio", local_name,
                    "--as", send_as
                ], cwd=script_dir, check=False)
            else:
                out = _run_lark([
                    "im", "+messages-send",
                    "--chat-id", target,
                    "--audio", local_name,
                    "--as", send_as
                ], cwd=script_dir, check=False)
            return out or {"code": -1, "msg": "no output"}
        finally:
            if os.path.exists(local_path):
                os.unlink(local_path)
    else:
        if is_private:
            out = _run_lark([
                "im", "+messages-send",
                "--user-id", target,
                "--text", content,
                "--as", send_as
            ], check=False)
        else:
            out = _run_lark([
                "im", "+messages-send",
                "--chat-id", target,
                "--text", content,
                "--as", send_as
            ], check=False)
        return out or {"code": -1, "msg": "no output"}


def send_text_with_audio(doc_title, doc_url, summary_text, audio_path=None, chat_id=None, user_id=None):
    """
    发送组合消息：文字摘要 + 文档链接 + 语音（可选）。

    Args:
        doc_title: 文档标题
        doc_url: 文档 URL
        summary_text: 摘要文本
        audio_path: 可选，语音文件路径
        chat_id: 可选，指定发送目标（群聊）
        user_id: 可选，指定发送目标（私聊）

    Returns:
        bool，两条消息是否都发送成功
    """
    lines = [
        f"🤖 **{doc_title}**\n",
        f"📋 今日摘要：\n{summary_text}\n",
        f"\n📄 [查看完整文档]({doc_url})",
    ]
    text = "".join(lines)

    r1 = send_message(chat_id=chat_id, user_id=user_id, content=text, msg_type="text")
    ok1 = _is_success_response(r1)

    if audio_path and os.path.exists(audio_path):
        audio_text = "🎧 以上为今日资讯语音摘要"
        r2 = send_message(chat_id=chat_id, user_id=user_id, content=audio_text,
                         msg_type="text", audio_path=audio_path)
        ok2 = _is_success_response(r2)
        if not ok2:
            print("[feishu-doc] 音频消息发送失败，已保留文字通知；音频可在文档中收听", file=sys.stderr)
        return ok1

    return ok1


# ===== 快捷函数 =====

def create_doc_and_write(title, markdown_content):
    """
    一次性创建文档并写入内容。

    自动选择知识库模式或文件夹模式。

    Args:
        title: 文档标题
        markdown_content: Markdown 内容

    Returns:
        dict: {"token": ..., "obj_token": ..., "title": ..., "url": ...}
        失败返回 None
    """
    node = create_node(title)
    if not node:
        return None

    ok = write_doc(node["obj_token"], markdown_content)
    if not ok:
        print(f"[feishu-doc] 文档写入失败: {node['obj_token']}", file=sys.stderr)
        return None

    return node


# ===== 入口 =====

if __name__ == "__main__":
    check_and_guide()  # 检测配置，未完成向导则触发引导
    _invalidate_config_cache()  # 清除缓存，读取新配置

    print("feishu-doc skill")
    print(f"配置路径: {ENV_FILE}")
    print(f"配置存在: {ENV_FILE.exists()}")
    if ENV_FILE.exists():
        cfg = _load_config()
        print(f"wiki_space_id: {cfg.get('wiki_space_id') or '未配置'}")
        print(f"folder_token: {cfg.get('folder_token') or '未配置'}")
        print(f"chat_id: {cfg.get('chat_id') or '未配置'}")
        print(f"user_id: {cfg.get('user_id') or '未配置'}")
        print(f"已配置: {is_configured()}")
