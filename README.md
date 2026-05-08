# AI Daily News

> 每日 AI 资讯聚合推送 — 聚合 GitHub Trending + Product Hunt + Follow Builders，自动生成中文摘要和专业简评；默认输出本地 Markdown，可选写入飞书文档并生成语音摘要。

这是一个 **Hermes skills bundle**，不是传统独立 App。用户从 GitHub 获取仓库后，将 `skills/` 下的各个 skill 安装到本机 `~/.hermes/skills/`，然后可以：

- 通过 Hermes 触发词生成每日任务
- 通过 Hermes cron 定时触发日报生成
- 单独复用其中的组件 skill（如 `github-trending`、`llm-tasks`、`tts-audio`）

## 解决什么问题

AI 资讯碎片化严重，你可能同时关注着十几个信息源：

- GitHub Trending 太杂，不知道哪些值得看
- Product Hunt 每天几十个 AI 新品，分辨成本高
- Follow Builders 推送的 Twitter 信息流刷不完
- 看完标题点进去，发现毫无价值，浪费时间

**这个工具做的事**：把 GitHub Trending、Product Hunt、Follow Builders 三个来源的数据聚合起来，用 AI 做筛选、翻译、点评，生成一份每天 5 分钟就能读完的高密度简报。默认保存为本地 Markdown，配置飞书后可自动写入飞书文档并发送通知。

## 功能特性

| 模块 | 内容 |
|------|------|
| **GitHub Trending** | 抓取过去 24 小时 AI 相关热门项目，AI 生成一句话点评 |
| **Product Hunt** | 每日 AI 新品中文翻译 + 专业简评 |
| **Follow Builders** | 聚合 AI 核心建造者远程 feed，生成推文精华 + 播客摘要 |
| **飞书文档** | 自动创建文档，知识库模式或文件夹模式均可 |
| **TTS 语音** | 生成语音摘要，适合通勤收听（仅 mmx-cli 支持） |

## 系统要求

- **Hermes Agent** — 本 skill 运行于 Hermes 之上
- **Python 3.10+**
- **LLM provider 凭证** — OpenAI/OpenRouter/mmx-cli 等任选其一
- **mmx-cli** — TTS 可选，需要语音摘要时再配置
- **lark-cli** — 飞书可选，需要写入飞书文档/发消息时再配置（`npm install -g @larksuite/lark-cli`）
- **网络** — 抓取 GitHub、Product Hunt、Follow Builders 数据

## 目录结构

```
ai-daily-news/
├── README.md
├── .gitignore
├── scripts/
│   └── install.py              # 安装/更新 skills，保留用户配置
└── skills/
    ├── ai-daily-news-v2/         # 主 skill（编排层）
    │   ├── SKILL.md
    │   ├── config.json           # 默认配置
    │   ├── prompts/              # AI 生成 prompt
    │   ├── templates/            # 本地 Markdown / 飞书文档模板
    │   └── scripts/
    │       ├── run.py            # Hermes 稳定 action 入口
    │       └── ai_daily_news_task_v2.py
    │
    ├── feishu-doc/               # 飞书文档操作封装
    │   ├── SKILL.md
    │   ├── .env.example
    │   ├── config.json
    │   └── scripts/
    │       ├── feishu_doc.py
    │       └── setup_guide.py
    │
    ├── llm-tasks/                # 通用 LLM 调用封装
    │   ├── SKILL.md
    │   ├── .env.example
    │   └── scripts/
    │       ├── llm_tasks.py
    │       └── setup_guide.py
    │
    ├── tts-audio/                # TTS 语音生成封装
    │   ├── SKILL.md
    │   ├── config.json
    │   └── scripts/
    │       └── tts_audio.py
    │
    ├── github-trending/          # GitHub Trending 数据获取
    │   ├── SKILL.md
    │   ├── config.json
    │   ├── prompts/
    │   │   └── gh-review.md
    │   └── scripts/
    │       └── github_trending.py
    │
    ├── ph-review-generator/      # Product Hunt 数据 + AI 点评
    │   ├── SKILL.md
    │   ├── config.json
    │   ├── prompts/
    │   │   └── ph-review.md
    │   └── scripts/
    │       └── ph_review.py
    │
    └── follow-builders-data/     # Follow Builders 远程 feed 数据适配
        ├── SKILL.md
        └── scripts/
            └── follow_builders_data.py
```

---

## 安装到 Hermes

### 第一步：从 GitHub 获取仓库

```bash
git clone <your-repo-url> ai-daily-news
cd ai-daily-news
```

### 第二步：安装或更新 skills

```bash
python3 scripts/install.py
```

这条命令会把 repo 中的 skills 安装/更新到 `~/.hermes/skills/`。更新时只覆盖 skill 代码和 `.env.example`，不会覆盖用户已有配置：

```text
~/.hermes/config/ai-daily-news-v2.json
~/.hermes/config/tts-audio.json
~/.hermes/skills/llm-tasks/.env
~/.hermes/skills/feishu-doc/.env.feishu
```

如果目标 env 文件不存在，安装脚本会自动从模板生成：

```text
llm-tasks/.env.example      -> llm-tasks/.env
feishu-doc/.env.example    -> feishu-doc/.env.feishu
```

安装后目录应类似：

```text
~/.hermes/skills/
├── ai-daily-news-v2/
├── feishu-doc/
├── github-trending/
├── llm-tasks/
├── ph-review-generator/
├── tts-audio/
└── follow-builders-data/
```

### 第三步：首次运行初始化向导（最小必填）

在 Hermes 中说：

```text
配置 AI 每日资讯
```

向导只配置最小功能所需的 `LLM_PROVIDER` 和对应凭证。完成后即可生成本地 Markdown 日报。

| Provider | 填写内容 |
|----------|----------|
| `mmx-cli` | `MMX_TOKEN_PLAN_KEY`（MMX Token Plan Key，不是普通 MiniMax API Key）|
| `openai` | `OPENAI_API_KEY` + `OPENAI_MODEL` |
| `openrouter` | `OPENROUTER_API_KEY` + `OPENROUTER_MODEL` |
| `azure` | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_DEPLOYMENT` |
| `google` | `GOOGLE_API_KEY` + `GOOGLE_MODEL` |
| `dashscope` | `DASHSCOPE_API_KEY` + `DASHSCOPE_MODEL` |
| `zai` | `ZAI_API_KEY` + `ZAI_MODEL` |
| `minimax` | `MINIMAX_HTTP_API_KEY` + `MINIMAX_HTTP_MODEL` |

> **mmx-cli 用户**：LLM 调用需要 MMX Token Plan Key。你可以在 `.env` 中填写 `MMX_TOKEN_PLAN_KEY`，或运行 `mmx config set-api-key <your-token-plan-key>` 配置本机 mmx。

### 第四步：跑一次 AI 每日资讯

先在 Hermes 中说：

```text
检查 AI 日报配置
```

这只检查配置、组件路径和外部命令，不抓取数据、不调用 LLM、不创建飞书文档。

然后说：

```text
生成今天的 AI 每日资讯
```

这会真实抓取 GitHub Trending、Product Hunt、Follow Builders，调用 LLM 生成摘要和点评，并在本机历史目录中生成 Markdown 文件。

默认历史目录是：

```text
~/.hermes/data/ai-daily-news-v2/
```

每次运行会保存到：

```text
~/.hermes/data/ai-daily-news-v2/YYYY-MM-DD/HHMMSS/
```

如需自定义，可在 `~/.hermes/config/ai-daily-news-v2.json` 中修改 `output.dir`。

开发调试时也可以临时指定输出目录：

```bash
AI_DAILY_NEWS_OUTPUT_DIR=/tmp/ai-daily-news-run \
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py run-local
```

这会在 `/tmp/ai-daily-news-run/YYYY-MM-DD/HHMMSS/` 生成 Markdown 文件，不触发飞书和 TTS。

### 第五步：配置定时任务

让 Hermes cron 每天固定时间触发这句话即可：

```text
生成今天的 AI 每日资讯
```

推荐每天 08:00。

### 扩展配置：飞书和 TTS（可选）

如需自动创建飞书文档和发送消息，再运行：

```text
配置 AI 日报飞书推送
```

如需 TTS 语音摘要，安装 `mmx-cli` 并在主配置中将 `tts.skip` 改为 `false`。TTS 调用本机 `mmx speech synthesize`，不直接读取 `MMX_TOKEN_PLAN_KEY`。

配置飞书或 TTS 后，继续用同一句触发日报：

```text
生成今天的 AI 每日资讯
```

正常情况下会输出：

```
==================================================
AI 每日资讯 v17 — 2026-05-07
==================================================

📡 正在抓取 GitHub Trending...
✓ GitHub：获取到 5 条

📡 正在抓取 Product Hunt...
✓ Product Hunt：获取到 5 条

...
✅ 任务完成！
📄 文档链接：https://feishu.cn/wiki/xxx
```

---

## 配置说明

### 文档模板

日报内容结构由主 skill 管理：

```text
~/.hermes/skills/ai-daily-news-v2/templates/daily_markdown.md  # 本地 index.md
~/.hermes/skills/ai-daily-news-v2/templates/daily_feishu.md    # 写入飞书前的内容模板
```

`feishu-doc` skill 只负责飞书创建、写入、媒体插入和消息推送，不负责日报内容结构。

### 主配置 `~/.hermes/config/ai-daily-news-v2.json`

如果不存在，脚本会使用 skill 内置的 `config.json` 默认值。如需自定义，创建此文件：

```json
{
  "github": {
    "topics": ["ai", "llm", "agent", "claude", "gpt", ...],
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

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `github.topics` | 过滤关键词，匹配任一词即纳入 | 37 个 AI 相关词 |
| `github.period` | 时间范围：`past_24_hours` 或 `past_7_days` | `past_24_hours` |
| `github.limit` | 输出条数 | `5` |
| `product_hunt.category` | PH 分类 | `ai` |
| `product_hunt.days_ago` | 抓取几天前的数据 | `1` |
| `product_hunt.limit` | 输出条数 | `5` |
| `tts.provider` | TTS provider，目前仅支持 `mmx-cli` | `mmx-cli` |
| `tts.skip` | 跳过语音生成；默认关闭，用户主动启用 TTS 时改为 `false` | `true` |
| `tts.voice` | MiniMax TTS 音色 | `Chinese (Mandarin)_Warm_Girl` |
| `output.dir` | 本地数据输出目录 | `~/.hermes/data/ai-daily-news-v2/` |

### LLM Provider `.env`

```env
# Provider 选择
LLM_PROVIDER=mmx-cli

# mmx-cli
MMX_TOKEN_PLAN_KEY=your-mmx-token-plan-key

# 超时时间（秒）
LLM_TIMEOUT=180
```

### 飞书 `.env.feishu`

位于 `~/.hermes/skills/feishu-doc/.env.feishu`：

```env
# 文档创建（二选一）
FEISHU_FOLDER_TOKEN=          # 文件夹模式（我的空间）
FEISHU_WIKI_SPACE_ID=         # 知识库模式
FEISHU_PARENT_NODE_TOKEN=     # 知识库父节点

# 消息发送（二选一）
FEISHU_CHAT_ID=oc_xxx        # 群聊
FEISHU_USER_ID=ou_xxx        # 私聊
```

---

## 使用方法

### Hermes 触发词

安装后，用户优先通过 Hermes 自然语言触发，不需要记脚本路径。

| 用户想做什么 | 在 Hermes 中说 |
|---|---|
| 首次配置 | `配置 AI 每日资讯` |
| 检查配置 | `检查 AI 日报配置` |
| 生成日报 | `生成今天的 AI 每日资讯` |
| 不要飞书和语音 | `生成今天的 AI 日报，不要飞书和语音` |
| 配置飞书 | `配置 AI 日报飞书推送` |
| 失败补跑 | `补跑今天失败的 AI 日报` |

### 定时自动执行（推荐）

让 Hermes cron 每天固定时间触发主 skill：

```text
生成今天的 AI 每日资讯
```

推荐设置每天 08:00。输出会保存到本地历史目录；如果配置了飞书，会同时创建飞书文档并发送通知。

### 开发调试命令

Hermes 正常使用不需要输入命令。开发和本地排查时，可以直接调用主脚本：

```bash
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py setup
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py setup-feishu
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py check
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py run-local
python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py resume
```

本地验证时也可以临时指定输出目录：

```bash
AI_DAILY_NEWS_OUTPUT_DIR=/tmp/ai-daily-news-run python3 ~/.hermes/skills/ai-daily-news-v2/scripts/run.py run-local
```

### 查看历史

默认情况下，每天生成的数据保存在：

```
~/.hermes/data/ai-daily-news-v2/YYYY-MM-DD/
├── latest.json          # 指向当天最近一次非 skipped 运行
└── HHMMSS/              # 单次运行目录；同一秒重复运行会追加 -01 后缀
    ├── index.md         # 完整文档
    ├── tts_text.txt     # 语音摘要文本
    ├── follow_builders_raw.json # Follow Builders 远程 feed 全量原始数据
    ├── audio.mp3        # 语音文件（如已生成）
    ├── doc_url.txt      # 飞书文档链接
    ├── checkpoint.json  # 可复用的成功阶段产物，用于 --resume-failed
    └── run_summary.json # 本次运行的结构化状态、产物路径、错误和提醒
```

`run_summary.json` 适合排查 Hermes cron：`status` 会是 `success`、`degraded`、`failed` 或 `skipped`，`errors[]` 记录真实失败原因，`warnings[]` 记录主动跳过或可接受降级。

失败补跑时运行：

```text
补跑今天失败的 AI 日报
```

它只会读取当天 `latest.json` 指向的 `degraded/failed` 运行，并复用其中已经成功的 GitHub、Product Hunt、Follow Builders、摘要、TTS 或飞书文档阶段；如果最近一次已经成功，或没有 `checkpoint.json`，则按普通新运行执行。

---

## 数据来源

| 来源 | 数据获取方式 | 是否需要 API Key |
|------|-------------|-----------------|
| GitHub Trending | OSSInsight API（公开） | 否 |
| Product Hunt | 官方 RSS Feed | 否 |
| Follow Builders | `follow-builders-data` 从远程 GitHub raw 中央 Feed 拉取 | 否 |
| AI 翻译/点评 | 你配置的 LLM Provider | 是（必填）|
| 飞书文档写入 | lark-cli | 是（可选）|
| TTS 语音 | 本机 mmx-cli speech synthesize | 否（但需要 mmx 已安装并可用）|

---

## 故障排查

### 报错 "配置文件不存在"

**症状**：`FileNotFoundError: 配置文件不存在：~/.hermes/config/ai-daily-news-v2.json`

**原因**：用户配置文件不存在，且 skill 内置默认值也不存在。

**解决**：
```bash
cp ~/.hermes/skills/ai-daily-news-v2/config.json \
   ~/.hermes/config/ai-daily-news-v2.json
```

---

### 飞书文档创建失败

**症状**：日志显示 "未配置飞书凭证，跳过飞书文档"，但你明明配置过。

**排查**：
1. 检查 `.env.feishu` 文件是否存在且格式正确：
   ```bash
   cat ~/.hermes/skills/feishu-doc/.env.feishu
   ```
2. 运行交互式配置向导：
   ```text
   配置 AI 日报飞书推送
   ```
3. 确认 `FEISHU_FOLDER_TOKEN` 或 `FEISHU_WIKI_SPACE_ID` 有值（不是空字符串）

---

### TTS 语音未生成

**原因**：TTS 由 `tts-audio` skill 负责，目前仅支持 `mmx-cli` provider。它不直接读取 `MMX_TOKEN_PLAN_KEY`，只检查本机 `mmx` 命令是否已安装并能执行 speech synthesis。不可用时会跳过语音，继续输出文本摘要。

**解决**：安装并完成本机 mmx 认证，或将 `tts.skip` 设为 `true` 关闭语音。

---

### GitHub Trending 获取失败

**症状**：`✓ GitHub：获取失败`

**排查**：
- 网络是否可访问 `api.github.com`
- GitHub API 有频率限制，大量重复测试可能触发限流
- 等待几分钟后重试

---

### 摘要生成超时

**症状**：`mmx text chat ... timed out after 120 seconds`

**解决**：
- 检查网络状态
- 适当调高 `.env` 中的 `LLM_TIMEOUT`
- 重试一次

---

## 架构

```
ai-daily-news-v2（编排层）
├── github-trending   → 抓取 + AI 点评
├── ph-review-generator → 抓取 + AI 翻译+点评
├── follow-builders-data → 远程推文/播客/博客 feed 数据
├── llm-tasks         → 所有 AI 生成（摘要、remix）
├── tts-audio         → TTS 语音摘要生成
└── feishu-doc        → 飞书写入 + 消息推送
```

各组件 skill 独立可复用，可单独安装使用。

---

## License

MIT
