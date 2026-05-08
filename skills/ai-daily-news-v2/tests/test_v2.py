#!/usr/bin/env python3
"""
ai-daily-news-v2 冒烟测试
运行前需先配置所有组件 skill 的 config.json
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# 尝试加载主脚本（会触发 import）
try:
    import ai_daily_news_task_v2 as task
    print("✓ 主脚本加载成功")
except FileNotFoundError as e:
    print(f"✗ 配置文件缺失: {e}")
    print("  请先配置 ~/.hermes/config/ai-daily-news-v2.json")
    sys.exit(1)
except Exception as e:
    print(f"✗ 主脚本加载失败: {e}")
    sys.exit(1)


def test_config():
    """测试配置加载"""
    print("\n=== 1. 配置加载 ===")
    try:
        cfg = task.load_config()
        print(f"✓ 配置加载成功")
        print(f"  github topics: {len(cfg.get('github', {}).get('topics', []))} 个")
        print(f"  tts voice: {cfg.get('tts', {}).get('voice')}")
        return True
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False


def test_components_import():
    """测试组件 skill 是否可导入"""
    print("\n=== 2. 组件 skill 导入 ===")
    try:
        from feishu_doc import create_node, write_doc, send_message
        print("✓ feishu_doc 可用")
    except Exception as e:
        print(f"✗ feishu_doc 导入失败: {e}")
        return False

    try:
        from github_trending import get_trending
        print("✓ github_trending 可用")
    except Exception as e:
        print(f"✗ github_trending 导入失败: {e}")
        return False

    try:
        from llm_tasks import chat, batch_task
        print("✓ llm_tasks 可用")
    except Exception as e:
        print(f"✗ llm_tasks 导入失败: {e}")
        return False

    try:
        from tts_audio import is_available, generate_audio
        print("✓ tts_audio 可用")
    except Exception as e:
        print(f"✗ tts_audio 导入失败: {e}")
        return False

    try:
        from follow_builders_data import fetch
        print("✓ follow_builders_data 可用")
    except Exception as e:
        print(f"✗ follow_builders_data 导入失败: {e}")
        return False

    return True


def test_build_functions():
    """测试文档内容构建函数"""
    print("\n=== 3. 文档构建函数 ===")
    try:
        # GH section
        gh_items = [{
            "title": "test/repo",
            "stars": 1234,
            "language": "Python",
            "description": "Test description",
            "url": "https://github.com/test/repo",
            "ai_review": "这是一个测试项目。",
            "extra": {"topics": ["ai", "llm"]}
        }]
        gh_section = task.build_gh_section(gh_items)
        assert "test/repo" in gh_section
        assert "1,234" in gh_section
        print("✓ build_gh_section 正常")

        # PH section
        ph_items = [{
            "title": "Test Product",
            "translated": "测试产品",
            "review": "这是一个测试点评。",
            "url": "https://producthunt.com"
        }]
        ph_section = task.build_ph_section(ph_items)
        assert "Test Product" in ph_section
        assert "测试产品" in ph_section
        print("✓ build_ph_section 正常")

        # FB section
        fb_result = {
            "podcast_digest": "播客测试内容",
            "tweets_digest": ["推文1", "推文2"]
        }
        fb_section = task.build_fb_section(fb_result)
        assert "播客测试内容" in fb_section
        print("✓ build_fb_section 正常")

        # Header
        header = task.build_header("2025-01-01")
        assert "AI 每日资讯" in header
        assert "2025-01-01" in header
        print("✓ build_header 正常")

        return True
    except Exception as e:
        print(f"✗ 构建函数异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ph_fallback_review():
    """测试 Product Hunt 点评失败时仍会生成本地兜底点评。"""
    print("\n=== 4. Product Hunt 点评兜底 ===")
    try:
        import ph_review

        items = [{
            "title": "Fallback Product",
            "description": "AI workflow automation for sales teams",
            "url": "https://producthunt.com/products/fallback-product",
        }]
        fallback = ph_review._fallback_review(items[0])
        assert fallback["translated"]
        assert fallback["review"]
        assert fallback["review_source"] == "fallback"

        merged = ph_review._merge_with_fallback(items, None)
        assert len(merged) == 1
        assert merged[0]["review"]
        assert merged[0]["review_source"] == "fallback"
        print("✓ PH 本地兜底点评正常")
        return True
    except Exception as e:
        print(f"✗ PH 兜底点评异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 50)
    print("ai-daily-news-v2 冒烟测试")
    print("=" * 50)

    results = [
        ("主脚本加载", True),
        ("配置加载", test_config()),
        ("组件 skill 导入", test_components_import()),
        ("文档构建函数", test_build_functions()),
        ("PH 点评兜底", test_ph_fallback_review()),
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
