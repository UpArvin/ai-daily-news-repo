---
name: llm-tasks
version: 0.2.0
description: 通用 LLM 批量任务封装 — 支持 mmx-cli、OpenAI、OpenRouter 等多种 provider
category: productivity
trigger_keywords: []
dependencies:
  - 至少配置以下一种 provider 的 API Key
---

# LLM Tasks Skill

首次运行时会自动触发交互式配置向导，引导你选择 LLM 提供商并填写 Key。

## 快速开始

```bash
# 直接运行，检测到未配置时自动引导
python3 ~/.hermes/skills/llm-tasks/scripts/llm_tasks.py
```

## 支持的 Provider

| # | Provider | 说明 | 必填字段 |
|---|----------|------|---------|
| 1 | **MiniMax CLI** | 需订阅 MMX Token Plan，使用 Token Plan Key | `MMX_TOKEN_PLAN_KEY` |
| 2 | OpenAI | GPT-4o、GPT-4o-mini 等 | `OPENAI_API_KEY` |
| 3 | OpenRouter | 聚合 Claude、Gemini、Mistral 等数十种模型 | `OPENROUTER_API_KEY` |
| 4 | Azure OpenAI | 企业用户推荐 | `AZURE_OPENAI_API_KEY` |
| 5 | Google AI | Gemini 系列 | `GOOGLE_API_KEY` |
| 6 | DashScope | 阿里通义（Qwen） | `DASHSCOPE_API_KEY` |
| 7 | Zhipu AI | 智谱（GLM） | `ZAI_API_KEY` |
| 8 | MiniMax HTTP API | 直接调用 MiniMax API（非 CLI） | `MINIMAX_HTTP_API_KEY` |

> ⚠️ **MiniMax CLI** 需要订阅 MMX Token Plan 才能用于 LLM 调用；这里填写的是 Token Plan Key，不是普通 MiniMax API Key。TTS 由 `tts-audio` 单独通过本机 `mmx speech synthesize` 调用，不直接读取 `MMX_TOKEN_PLAN_KEY`。

## 接口

### `chat(prompt, model=None, timeout=None) -> str | None`
单次对话调用，返回模型回复文本。

### `batch_task(prompt_template, items, output_format="json-array", field_specs=None) -> list | dict | None`
通用批量任务生成。

```python
from llm_tasks import chat, batch_task

# 单次对话
reply = chat("用一句话解释 Python")

# 批量生成
items = [{"Title": "产品A", "desc": "描述"}, ...]
results = batch_task(
    prompt_template="为以下产品生成一句话介绍：\n{items_text}",
    items=items,
    output_format="json-array",
    field_specs={"title": "名称", "desc": "描述"}
)
```

## 配置（`.env`）

首次运行时会自动引导配置，也可手动创建 `~/.hermes/skills/llm-tasks/.env`：

```env
LLM_PROVIDER=mmx-cli        # 提供商
LLM_TIMEOUT=180             # 超时（秒）

# MiniMax CLI 专用（需 MMX Token Plan，模型固定为 MiniMax-M2.7）
MMX_TOKEN_PLAN_KEY=

# OpenAI 兼容 API 通用
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

切换 provider：修改 `LLM_PROVIDER`，并填写对应 provider 的 Key。

## 重新配置

```bash
python3 ~/.hermes/skills/llm-tasks/scripts/setup_guide.py
```
