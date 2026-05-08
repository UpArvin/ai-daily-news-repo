#!/usr/bin/env python3
"""
Stable action entrypoint for the ai-daily-news Hermes skill.

Hermes should call this thin wrapper with an action name instead of depending on
the main task script's CLI flags directly.
"""
import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()
MAIN_SCRIPT = SCRIPT_DIR / "ai_daily_news_task_v2.py"

ACTION_ARGS = {
    "setup": ["--setup"],
    "check": ["--check-config"],
    "run": [],
    "run-local": ["--skip-feishu", "--skip-tts"],
    "setup-feishu": ["--setup-feishu"],
    "resume": ["--resume-failed"],
}

ALIASES = {
    "config": "setup",
    "check-config": "check",
    "daily": "run",
    "generate": "run",
    "local": "run-local",
    "feishu": "setup-feishu",
    "resume-failed": "resume",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run ai-daily-news by stable action name.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Actions:\n"
            "  setup         First-time LLM provider setup\n"
            "  check         Check config and dependencies\n"
            "  run           Generate today's AI daily news\n"
            "  run-local     Generate local Markdown only\n"
            "  setup-feishu  Configure Feishu document/message delivery\n"
            "  resume        Resume the latest failed/degraded run\n"
        ),
    )
    parser.add_argument("action", nargs="?", default="run", help="Action name")
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed through to ai_daily_news_task_v2.py",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    action = ALIASES.get(args.action, args.action)
    if action not in ACTION_ARGS:
        valid = ", ".join(sorted(ACTION_ARGS))
        print(f"Unknown action: {args.action}", file=sys.stderr)
        print(f"Valid actions: {valid}", file=sys.stderr)
        return 2

    cmd = [sys.executable, str(MAIN_SCRIPT), *ACTION_ARGS[action], *args.extra_args]
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
