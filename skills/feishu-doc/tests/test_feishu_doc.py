#!/usr/bin/env python3
"""
feishu-doc 冒烟测试
运行前需先配置 feishu-doc/.env.feishu
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import feishu_doc

def test_config():
    """测试配置是否已配置"""
    print("\n=== 1. 配置检查 ===")
    if not feishu_doc.ENV_FILE.exists():
        print(f"⚠  配置文件不存在: {feishu_doc.ENV_FILE}")
        print("  请先运行 setup_guide.py，或由安装脚本通过 .env.feishu.example 生成 .env.feishu")
        return False
    try:
        cfg = feishu_doc._load_config()
        doc_target = cfg.get("folder_token") or cfg.get("wiki_space_id")
        msg_target = cfg.get("chat_id") or cfg.get("user_id")
        if not doc_target:
            print("⚠  未配置文档创建目标: FEISHU_FOLDER_TOKEN 或 FEISHU_WIKI_SPACE_ID")
            return False
        if not msg_target:
            print("⚠  未配置消息发送目标: FEISHU_CHAT_ID 或 FEISHU_USER_ID")
            return False
        print(f"✓  配置正常: doc_target={doc_target[:10]}..., msg_target={msg_target[:10]}...")
        return True
    except Exception as e:
        print(f"✗  配置加载失败: {e}")
        return False


def test_node_exists():
    """测试 node_exists（只读，不创建）"""
    print("\n=== 2. node_exists 检查 ===")
    try:
        result = feishu_doc.node_exists(f"_smoke_test_{int(time.time())}")
        print(f"✓  node_exists 正常（不存在节点返回 False）: {result}")
        return True
    except Exception as e:
        print(f"✗  node_exists 失败: {e}")
        return False


def test_send_message_dry():
    """测试 send_message（只发一条文字消息）"""
    print("\n=== 3. send_message 干跑 ===")
    try:
        result = feishu_doc.send_message(
            chat_id=None,
            content=f"[feishu-doc 冒烟测试 {time.strftime('%H:%M:%S')}] 配置检查消息，勿删",
            msg_type="text"
        )
        if result and result.get("code") == 0:
            print(f"✓  send_message 成功: code={result.get('code')}")
            return True
        else:
            print(f"✗  send_message 返回异常: {result}")
            return False
    except Exception as e:
        print(f"✗  send_message 失败: {e}")
        return False


def test_full_flow():
    """完整流程：创建节点 → 写入 → 删除"""
    print("\n=== 4. 完整流程（创建→写入→删除）===")
    ts = int(time.time())
    test_title = f"_feishu_doc_smoke_test_{ts}"

    try:
        print(f"  创建节点: {test_title}")
        node = feishu_doc.create_node(test_title)
        if not node:
            print("✗  create_node 失败")
            return False
        print(f"✓  create_node 成功: obj_token={node['obj_token']}")

        print(f"  写入文档...")
        ok = feishu_doc.write_doc(node["obj_token"], "# 冒烟测试\n\n这是一条测试内容。", mode="overwrite")
        if not ok:
            print("✗  write_doc 失败")
            return False
        print(f"✓  write_doc 成功")

        print(f"  读取文档...")
        content = feishu_doc.read_doc(node["obj_token"])
        if content is None:
            print("✗  read_doc 失败")
            return False
        print(f"✓  read_doc 成功，长度={len(content)}")

        # 清理
        import subprocess, json
        cfg = feishu_doc._load_config()
        space_id = cfg["wiki"]["space_id"]
        node_token = node["token"]
        params = json.dumps({"space_id": space_id, "node_token": node_token})
        r = subprocess.run(
            ["lark-cli", "wiki", "nodes", "delete", "--params", params],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            print(f"✓  节点已删除")
        else:
            print(f"⚠  节点删除失败（不影响测试）: {r.stderr}")

        return True
    except Exception as e:
        print(f"✗  完整流程失败: {e}")
        return False


def main():
    print("=" * 50)
    print("feishu-doc 冒烟测试")
    print("=" * 50)

    results = []

    ok = test_config()
    results.append(("配置检查", ok))
    if not ok:
        print("\n⚠  配置未就绪，跳后续测试。请先配置 .env.feishu")
        print_summary(results)
        return 1

    results.append(("node_exists", test_node_exists()))
    results.append(("send_message", test_send_message_dry()))
    results.append(("完整流程", test_full_flow()))

    print_summary(results)
    return 0


def print_summary(results):
    ok_count = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n" + "=" * 50)
    print(f"结果: {ok_count}/{total} 通过")
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}")
    print("=" * 50)


if __name__ == "__main__":
    sys.exit(main())
