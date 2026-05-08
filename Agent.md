# AI Daily News Agent Guide

这份文档面向开发者和开发者 Agent。GitHub 首页 README 保持简洁；本文件记录 skill 定位、目录结构、安装行为、配置、运行流程、模板、调试方式和已知限制。

## 项目定位

`ai-daily-news-repo` 本身是一个可工程化发布的 Hermes skill 仓库。用户从 GitHub 安装到本机后，可以通过 Hermes 触发词运行，也可以由 Codex 或其他 agent 直接调用主入口脚本验证。

核心目标是：用最小配置生成一份 AI 每日资讯报告。飞书文档、飞书消息、TTS 语音都是可选扩展，不能阻塞最小功能。

## 最小功能

最小可用路径只要求：

- Python 3.10+
- 可用网络
- 一个 AI 模型 API Key

默认结果：

- 生成本地 Markdown 日报
- 输出到 `~/.hermes/data/ai-daily-news-v2/YYYY-MM-DD/HHMMSS/`
- 不创建飞书文档
- 不发送飞书消息
- 不生成 TTS 语音

## 目录结构

```text
ai-daily-news-repo/
├── README.md
├── Agent.md
├── RELEASE_NOTES.md
├── scripts/
│   └── install.py
└── skills/
    ├── ai-daily-news-v2/
    │   ├── SKILL.md
    │   ├── config.json
    │   ├── prompts/
    │   │   └── doc-summary.md
    │   ├── templates/
    │   │   ├── daily_markdown.md
    │   │   └── daily_feishu.md
    │   ├── scripts/
    │   │   ├── run.py
    │   │   └── ai_daily_news_task_v2.py
    │   └── tests/
    │       └── test_v2.py
    ├── follow-builders-data/
    ├── github-trending/
    ├── ph-review-generator/
    ├── llm-tasks/
    ├── tts-audio/
    └── feishu-doc/
```

## Component Responsibilities

| Skill | 职责 |
|---|---|
| `ai-daily-news-v2` | 主编排层。负责配置读取、checkpoint、内容聚合、摘要生成、Markdown/飞书模板渲染、输出保存和可选飞书/TTS 调用。 |
| `follow-builders-data` | 从远程 GitHub raw feed 获取 Follow Builders 数据；拉取失败时可回退到本地生成逻辑。 |
| `github-trending` | 抓取 GitHub Trending/OSSInsight 数据，并用专业 prompt 生成简洁点评。 |
| `ph-review-generator` | 抓取 Product Hunt RSS，并用专业 prompt 生成中文翻译和简洁点评。 |
| `llm-tasks` | 统一封装 LLM provider。主 skill 不应直接硬编码某个 provider。 |
| `tts-audio` | TTS 语音摘要生成。当前只封装本机 `mmx-cli` 的 speech synthesis。 |
| `feishu-doc` | 飞书文档创建、写入、音频插入和消息推送。它不负责日报内容结构。 |

## 安装和更新

推荐用户通过 Hermes 自然语言安装/更新：

```text
帮我安装这个skill：https://github.com/UpArvin/ai-daily-news-repo
```

开发者本地验证安装脚本时，可以在已 clone 的仓库中运行：

```bash
python3 scripts/install.py
```

安装目标：

```text
~/.hermes/skills/
```

`scripts/install.py` 的行为：

- 将 `skills/` 下每个子 skill 复制到 `~/.hermes/skills/`
- 更新代码时保留用户已有 env 文件
- 如果 env 文件不存在，则由对应 example 文件生成
- 安装时忽略 `tests/`、`__pycache__/`、`.DS_Store`
- 不写入 `~/.hermes/config/`，用户配置由运行向导生成或由默认配置兜底

会自动生成的 env：

```text
llm-tasks/.env.example   -> llm-tasks/.env
feishu-doc/.env.feishu.example -> feishu-doc/.env.feishu
```

## Hermes Triggers

用户不需要记 CLI。Hermes 入口在 `skills/ai-daily-news-v2/SKILL.md` 中定义，推荐触发词如下：

| 用户意图 | 触发说法 | run.py action |
|---|---|---|
| 首次配置 | `配置 AI 每日资讯` | `setup` |
| 检查配置 | `检查 AI 日报配置` | `check` |
| 生成日报 | `生成今天的 AI 每日资讯` | `run` |
| 只生成本地文件 | `生成今天的 AI 日报，不要飞书和语音` | `run-local` |
| 配置飞书 | `配置 AI 日报飞书推送` | `setup-feishu` |
| 失败补跑 | `补跑今天失败的 AI 日报` | `resume` |

Hermes cron 只需要定时触发：

```text
生成今天的 AI 每日资讯
```

## Developer Commands

这些命令用于开发和验证，不是普通用户入口：

```bash
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py setup
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py setup-feishu
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py check
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py run
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py run-local
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py resume
```

开发时可以临时指定输出目录，避免写入真实 Hermes 历史目录：

```bash
AI_DAILY_NEWS_OUTPUT_DIR=/tmp/ai-daily-news-run python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py run-local
```

测试 repo 源码：

```bash
python3 skills/ai-daily-news-v2/tests/test_v2.py
python3 skills/github-trending/tests/test_github_trending.py
python3 skills/feishu-doc/tests/test_feishu_doc.py
```

测试安装到临时目录：

```bash
HERMES_SKILLS_DIR=/tmp/hermes-skills-test python3 scripts/install.py
```

## Configuration

主配置默认来自：

```text
skills/ai-daily-news-v2/config.json
```

用户可覆盖到：

```text
~/.hermes/config/ai-daily-news-v2.json
```

关键字段：

```json
{
  "github": {
    "topics": ["ai", "llm", "agent"],
    "period": "past_24_hours",
    "limit": 5
  },
  "product_hunt": {
    "category": "ai",
    "days_ago": 1,
    "limit": 5
  },
  "tts": {
    "provider": "mmx-cli",
    "voice": "Chinese (Mandarin)_Warm_Girl",
    "skip": true
  },
  "output": {
    "dir": "~/.hermes/data/ai-daily-news-v2/"
  }
}
```

默认关闭 TTS：`tts.skip=true`。

`output.dir` 可配置运行产物根目录。每次运行都会创建日期目录和时间戳目录。

## LLM Provider

LLM 配置在：

```text
~/.hermes/skills/llm-tasks/.env
```

`LLM_PROVIDER` 支持：

- `mmx-cli`
- `openai`
- `openrouter`
- `azure`
- `google`
- `dashscope`
- `zai`
- `minimax`

注意：

- `mmx-cli` 作为 LLM provider 时使用的是 `MMX_TOKEN_PLAN_KEY`，也就是 MMX Token Plan Key。
- TTS 不直接读取 `MMX_TOKEN_PLAN_KEY`；TTS 只调用本机 `mmx speech synthesize`，依赖本机 mmx 已安装并认证。

## Feishu

飞书配置在：

```text
~/.hermes/skills/feishu-doc/.env.feishu
```

核心字段：

```env
FEISHU_FOLDER_TOKEN=
FEISHU_WIKI_SPACE_ID=
FEISHU_PARENT_NODE_TOKEN=
FEISHU_CHAT_ID=
FEISHU_USER_ID=
```

创建文档支持两种模式：

- 文件夹模式：配置 `FEISHU_FOLDER_TOKEN`
- 知识库模式：配置 `FEISHU_WIKI_SPACE_ID` 和可选 `FEISHU_PARENT_NODE_TOKEN`

消息发送支持两种模式：

- 群聊：配置 `FEISHU_CHAT_ID`
- 私聊：配置 `FEISHU_USER_ID`

飞书能力依赖本机 `lark-cli` 和用户已完成飞书认证。

## Templates and Prompts

日报结构由主 skill 管理。

```text
skills/ai-daily-news-v2/templates/daily_markdown.md
skills/ai-daily-news-v2/templates/daily_feishu.md
```

今日摘要 prompt：

```text
skills/ai-daily-news-v2/prompts/doc-summary.md
```

分块点评 prompt：

```text
skills/github-trending/prompts/gh-review.md
skills/ph-review-generator/prompts/ph-review.md
```

结构要求：

- 标题顺序固定：今日摘要、Follow Builders 讯息、GitHub 热门项目、Product Hunt 热门产品
- 今日摘要是日报精华，也是 TTS 文本来源
- Follow Builders 展示结构化精选内容，原始全量 feed 另存
- GH/PH 每条点评保持专业、简约、可快速扫读
- Markdown 模板放主 skill
- 飞书日报模板也放主 skill
- `feishu-doc` 只做飞书平台动作，不定义日报内容结构

## Runtime Artifacts

默认根目录：

```text
~/.hermes/data/ai-daily-news-v2/
```

单次运行目录：

```text
~/.hermes/data/ai-daily-news-v2/YYYY-MM-DD/HHMMSS/
```

常见文件：

```text
index.md
tts_text.txt
audio.mp3
doc_url.txt
follow_builders_raw.json
checkpoint.json
run_summary.json
```

`latest.json` 位于当天日期目录，指向当天最近一次非 skipped 运行。

## Checkpoint and Resume

失败补跑只补失败部分，不全量重跑。

`checkpoint.json` 会保存已经成功的阶段产物。`run.py resume` 会复用已成功阶段，并只继续未完成或失败的阶段。若最近一次已经成功，或没有可用 checkpoint，则按普通新运行执行。

## Data Sources

| 来源 | 获取方式 | API Key |
|---|---|---|
| Follow Builders | 远程 GitHub raw feed | 否 |
| GitHub Trending | OSSInsight/GitHub 公开数据 | 否 |
| Product Hunt | 官方 RSS feed | 否 |
| LLM 生成 | 用户配置的 provider | 是 |
| TTS | 本机 `mmx-cli` | 需要本机 mmx 可用 |
| 飞书 | 本机 `lark-cli` | 需要飞书认证 |

## Known Limitations

- Product Hunt 的 `category` 和 `days_ago` 目前仍未真正参与 RSS 过滤，当前使用 Product Hunt 官方 feed。
- Follow Builders 正文展示的是 LLM remix 后的精选摘要，不是全部原文；全量原始数据保存在 `follow_builders_raw.json`。
- 飞书能力依赖 `lark-cli`，本 repo 不内置飞书认证流程。
- TTS 当前只支持 `mmx-cli`。

## Release Checklist

发布前建议：

```bash
python3 skills/ai-daily-news-v2/tests/test_v2.py
python3 skills/github-trending/tests/test_github_trending.py
python3 skills/feishu-doc/tests/test_feishu_doc.py
HERMES_SKILLS_DIR=/tmp/hermes-skills-test python3 scripts/install.py
```

如果验证真实全流程，使用临时输出目录先跑本地 Markdown，再按需测试飞书和 TTS。
