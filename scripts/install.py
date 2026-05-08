#!/usr/bin/env python3
"""
Install or update ai-daily-news skills into ~/.hermes/skills.

The installer updates skill code but preserves user environment and config files.
When an env file is missing, it is generated from the bundled .env.example.
"""
import shutil
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_SKILLS = REPO_ROOT / "skills"
TARGET_SKILLS = Path(os.environ.get("HERMES_SKILLS_DIR", Path.home() / ".hermes" / "skills")).expanduser()

ENV_TARGETS = {
    "llm-tasks": ".env",
    "feishu-doc": ".env.feishu",
}


def _ignore(dir_path, names):
    ignored = {"__pycache__", ".DS_Store", "tests"}
    for name in names:
        if name.startswith(".env") and name != ".env.example":
            ignored.add(name)
    return ignored


def copy_skill(skill_dir):
    target = TARGET_SKILLS / skill_dir.name
    shutil.copytree(skill_dir, target, dirs_exist_ok=True, ignore=_ignore)
    return target


def ensure_env(skill_name):
    target_name = ENV_TARGETS.get(skill_name)
    if not target_name:
        return None
    skill_dir = TARGET_SKILLS / skill_name
    example = skill_dir / ".env.example"
    target = skill_dir / target_name
    if not example.exists():
        return f"  - {skill_name}: 未找到 .env.example，跳过 env 生成"
    if target.exists():
        return f"  - {skill_name}: 保留已有 {target_name}"
    shutil.copy2(example, target)
    return f"  - {skill_name}: 已由 .env.example 生成 {target_name}"


def main():
    if not SOURCE_SKILLS.exists():
        raise SystemExit(f"skills 目录不存在：{SOURCE_SKILLS}")

    try:
        TARGET_SKILLS.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise SystemExit(
            f"无法写入目标目录：{TARGET_SKILLS}\n"
            "请确认当前用户有权限，或通过 HERMES_SKILLS_DIR 指定安装目录。"
        ) from e
    print(f"安装/更新 skills 到：{TARGET_SKILLS}")

    copied = []
    try:
        for skill_dir in sorted(p for p in SOURCE_SKILLS.iterdir() if p.is_dir()):
            target = copy_skill(skill_dir)
            copied.append(skill_dir.name)
            print(f"✓ {skill_dir.name} -> {target}")
    except PermissionError as e:
        raise SystemExit(
            f"安装过程中无法写入：{TARGET_SKILLS}\n"
            "请确认当前用户有权限，或通过 HERMES_SKILLS_DIR 指定安装目录。"
        ) from e

    print("\n环境变量文件：")
    for skill_name in sorted(copied):
        msg = ensure_env(skill_name)
        if msg:
            print(msg)

    print("\n完成。下一步在 Hermes 中说：")
    run_script = TARGET_SKILLS / "ai-daily-news-v2" / "scripts" / "run.py"
    print("配置 AI 每日资讯")
    print("\n开发调试命令：")
    print(f"python3 {run_script} setup")


if __name__ == "__main__":
    main()
