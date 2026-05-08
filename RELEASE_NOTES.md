# Release Notes

## v0.2.0 - 2026-05-08

### 当前定位

AI Daily News 是一个 Hermes skill 工程仓库。用户安装后通过 Hermes 触发词使用，不需要记 Python 脚本路径。

最小功能是生成本地 Markdown AI 日报：

- 今日摘要
- Follow Builders 讯息
- Github 热门项目
- Product Hunt 热门产品

### 默认行为

- 默认输出目录：`~/.hermes/data/ai-daily-news-v2/`
- 每次运行保存到：`YYYY-MM-DD/HHMMSS/`
- 默认只需要配置 LLM provider
- 默认关闭 TTS：`tts.skip=true`
- 飞书文档和飞书消息为可选扩展
- Follow Builders 正文展示精选摘要，同时保存全量远程 feed 到 `follow_builders_raw.json`

### Hermes 触发词

| 用户意图 | 触发说法 |
|---|---|
| 首次配置 | `配置 AI 每日资讯` |
| 检查配置 | `检查 AI 日报配置` |
| 生成日报 | `生成今天的 AI 每日资讯` |
| 配置飞书 | `配置 AI 日报飞书推送` |
| 失败补跑 | `补跑今天失败的 AI 日报` |

### 主要能力

- 稳定 action 入口：`skills/ai-daily-news-v2/scripts/run.py`
- 安装/更新脚本：`scripts/install.py`
- LLM provider 统一由 `llm-tasks` 管理
- Product Hunt 点评支持批量生成、逐条补救和本地兜底
- 失败补跑通过 `checkpoint.json` 复用已成功阶段
- 飞书模板和 Markdown 模板分离
- TTS 文本直接使用今日摘要，不另行生成

### 可选扩展

- 飞书文档/消息：运行 `配置 AI 日报飞书推送`
- TTS 语音摘要：安装并认证本机 `mmx-cli`，将主配置 `tts.skip` 改为 `false`

### 已知限制

- Product Hunt 的 `category` 和 `days_ago` 配置目前仍未真正参与 RSS 过滤，当前使用 Product Hunt 官方 feed。
- Follow Builders 正文不是全量内容，而是 LLM remix 后的精选摘要；全量原始数据保存在运行产物中。
- `mmx-cli` 作为 LLM provider 时需要 MMX Token Plan Key；TTS 不直接读取该 key。
- 飞书能力依赖本机 `lark-cli` 和用户已完成的飞书认证。

### 发布前验证

- `python3 skills/ai-daily-news-v2/tests/test_v2.py`：5/5 通过
- `py_compile`：主要脚本通过
- `run.py check`：可正常检查配置和输出路径
- `run.py run-local`：已验证可生成本地 Markdown，并保存 `follow_builders_raw.json`
