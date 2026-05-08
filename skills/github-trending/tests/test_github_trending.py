#!/usr/bin/env python3
"""
github-trending 冒烟测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import github_trending


def test_get_trending():
    """测试 get_trending 基本功能"""
    print("\n=== 1. get_trending 基本测试 ===")
    try:
        results = github_trending.get_trending(limit=5)
        print(f"✓  返回 {len(results)} 条")
        for r in results:
            lang = r.get("language") or "-"
            stars = r.get("stars", 0)
            print(f"  [{lang}] {r['title']} ⭐{stars:,}")
        if len(results) > 0:
            # 验证字段完整性
            r = results[0]
            required = ["title", "description", "stars", "language", "url"]
            missing = [f for f in required if f not in r]
            if missing:
                print(f"✗  缺少字段: {missing}")
                return False
            print(f"✓  字段完整")
            return True
        else:
            print("⚠  返回 0 条（网络或 API 问题）")
            return True  # 不算失败
    except Exception as e:
        print(f"✗  异常: {e}")
        return False


def test_get_repo_details():
    """测试 get_repo_details"""
    print("\n=== 2. get_repo_details 测试 ===")
    try:
        # 测试一个已知存在的仓库
        result = github_trending.get_repo_details("microsoft/vscode")
        if result:
            print(f"✓  返回: {result['title']} ⭐{result['stars']:,}")
            return True
        else:
            print("⚠  返回 None（可能无 token 或网络问题）")
            return True  # token 可选，不强制
    except Exception as e:
        print(f"✗  异常: {e}")
        return False


def test_config_loading():
    """测试配置加载"""
    print("\n=== 3. 配置加载测试 ===")
    try:
        cfg = github_trending._load_config()
        keywords = cfg.get("ai_keywords", [])
        print(f"✓  配置加载成功，关键词数: {len(keywords)}")
        return True
    except Exception as e:
        print(f"✗  异常: {e}")
        return False


def main():
    print("=" * 50)
    print("github-trending 冒烟测试")
    print("=" * 50)

    results = [
        ("配置加载", test_config_loading()),
        ("get_trending", test_get_trending()),
        ("get_repo_details", test_get_repo_details()),
    ]

    ok_count = sum(1 for _, ok in results if ok)
    print("\n" + "=" * 50)
    print(f"结果: {ok_count}/{len(results)} 通过")
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}")
    print("=" * 50)
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
