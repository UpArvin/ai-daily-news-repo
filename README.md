# AI Daily News

一个可安装到 Hermes 的 AI 每日资讯 skill。它会聚合 Follow Builders、GitHub Trending、Product Hunt，生成一份结构稳定的中文日报；默认保存本地 Markdown，飞书文档、飞书消息和 TTS 语音都是可选增强。

## 安装/更新

```text
帮我安装这个skill：https://github.com/UpArvin/ai-daily-news-repo
```

首次安装和后续更新都用这句话。Hermes 会从 GitHub 获取最新仓库，并把 skills 安装到：

```text
~/.hermes/skills/
```

## 第一次使用

在 Hermes 中说：

```text
配置 AI 每日资讯
```

首次向导只配置最小必填项：LLM provider 和对应密钥。完成后说：

```text
生成今天的 AI 每日资讯
```

默认输出目录：

```text
~/.hermes/data/ai-daily-news-v2/YYYY-MM-DD/HHMMSS/
```

主要产物是 `index.md`。如果启用了 TTS 或飞书，也会生成 `audio.mp3`、`doc_url.txt` 等附加文件。

## Hermes 触发词

| 想做什么 | 对 Hermes 说 |
|---|---|
| 首次配置 | `配置 AI 每日资讯` |
| 检查配置 | `检查 AI 日报配置` |
| 生成日报 | `生成今天的 AI 每日资讯` |
| 配置飞书 | `配置 AI 日报飞书推送` |
| 失败补跑 | `补跑今天失败的 AI 日报` |

定时任务也只需要让 Hermes cron 每天固定时间触发：

```text
生成今天的 AI 每日资讯
```

推荐每天 08:00。

## 日报内容

固定结构如下：

1. 今日摘要
2. Follow Builders 讯息
3. GitHub 热门项目
4. Product Hunt 热门产品

今日摘要同时作为 TTS 文本来源，不会另行生成一版语音稿。

## 可选增强

飞书文档和消息：

```text
配置 AI 日报飞书推送
```

TTS 语音摘要：安装并认证本机 `mmx-cli`，然后把主配置里的 `tts.skip` 改为 `false`。

## 开发者信息

完整架构、配置项、组件职责、调试命令、模板说明和已知限制请看 [Agent.md](Agent.md)。

快速测试：

```bash
python3 skills/ai-daily-news-v2/tests/test_v2.py
```

## License

MIT
