---
name: ai-daily-news-v2
version: 0.2.0
description: AI 每日资讯日报 — 聚合 GitHub Trending、Product Hunt、Follow Builders，生成中文 Markdown 日报；可选写入飞书和生成 TTS 音频摘要
category: productivity
trigger_keywords:
  - AI每日资讯
  - 每日AI资讯
  - AI日报
  - 生成AI日报
  - 生成今天的AI每日资讯
  - 跑一下AI Daily News
  - 检查AI日报配置
  - 配置AI日报
  - 配置AI Daily News
  - 配置飞书推送
  - 补跑AI日报
dependencies:
  - llm-tasks skill（必需，配置 LLM provider）
  - github-trending skill（必需，GitHub Trending 数据）
  - ph-review-generator skill（必需，Product Hunt 数据和点评）
  - follow-builders-data skill（必需，远程 Follow Builders feed 数据）
  - feishu-doc skill（可选，飞书文档和消息推送）
  - tts-audio skill（可选，TTS 音频摘要；当前仅支持 mmx-cli）
scheduled:
  schedule: "0 8 * * *"
  prompt: "生成今天的 AI 每日资讯"
---

# AI Daily News

这是 AI 每日资讯的主编排 skill。用户通常不需要输入 Python 命令，只需要在 Hermes 中用自然语言触发。

## 用户可以这样说

| 用户意图 | 推荐说法 | 内部动作 |
|---|---|---|
| 首次配置 | 配置 AI 每日资讯 | 运行 `scripts/run.py setup` |
| 检查配置 | 检查 AI 日报配置 | 运行 `scripts/run.py check` |
| 生成日报 | 生成今天的 AI 每日资讯 | 运行 `scripts/run.py run` |
| 只生成本地日报 | 生成今天的 AI 日报，不要飞书和语音 | 运行 `scripts/run.py run-local` |
| 配置飞书 | 配置 AI 日报飞书推送 | 运行 `scripts/run.py setup-feishu` |
| 失败补跑 | 补跑今天失败的 AI 日报 | 运行 `scripts/run.py resume` |

## 定时任务

如果用户希望每天自动生成，让 Hermes cron 每天固定时间触发这句话即可：

```text
生成今天的 AI 每日资讯
```

推荐时间：每天 08:00。

## 最小功能

最小功能只需要配置 LLM provider。完成后即可生成本地 Markdown 日报：

- 今日摘要
- Follow Builders 讯息
- Github 热门项目
- Product Hunt 热门产品

飞书文档、飞书消息、TTS 语音摘要都是可选扩展。未配置时不影响本地 Markdown 生成。

## 内容模板

日报内容结构由主 skill 管理：

```text
templates/daily_markdown.md  # 本地 index.md 输出模板
templates/daily_feishu.md    # 写入飞书前使用的日报内容模板
prompts/doc-summary.md       # 今日摘要 prompt，同时作为 TTS 文本来源
```

`feishu-doc` 只负责创建文档、写入 Markdown、插入媒体和发送消息，不决定 AI Daily News 的内容结构。

## 组件职责

```text
ai-daily-news-v2       # 编排层，负责日报流程、模板、补跑、产物管理
github-trending       # GitHub Trending 数据获取和开源项目点评
ph-review-generator   # Product Hunt 数据获取、翻译和产品点评
follow-builders-data  # 从远程 GitHub feed 拉取 Follow Builders 数据
llm-tasks             # 多 provider LLM 调用封装
tts-audio             # 可选 TTS 音频摘要
feishu-doc            # 可选飞书文档和消息推送
```

## 运行产物

每次运行会在 `output.dir/YYYY-MM-DD/HHMMSS/` 下保存，`output.dir/YYYY-MM-DD/latest.json` 指向当天最近一次非 skipped 运行：

默认 `output.dir` 是：

```text
~/.hermes/data/ai-daily-news-v2/
```

用户可在 `~/.hermes/config/ai-daily-news-v2.json` 中修改 `output.dir`，也可在开发调试时用 `AI_DAILY_NEWS_OUTPUT_DIR` 临时覆盖。

```text
index.md          # 完整 Markdown 日报
tts_text.txt      # 今日摘要文本，也是 TTS 文本来源
follow_builders_raw.json # Follow Builders 远程 feed 全量原始数据
audio.mp3         # 语音文件（如已生成）
doc_url.txt       # 飞书文档链接（如已创建）
checkpoint.json   # 失败补跑可复用的成功阶段产物
run_summary.json  # 结构化状态、产物路径、错误和提醒
```

## 开发调试

Hermes 正常使用时应通过触发词调用。开发和本地排查时可以直接运行稳定 action 入口：

```bash
python3 scripts/run.py check
python3 scripts/run.py run-local
python3 scripts/run.py resume
```
