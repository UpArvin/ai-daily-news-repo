---
name: feishu-doc
version: 0.2.0
description: 飞书文档和知识库操作封装 — 创建节点、写入内容、插入媒体、发送消息
category: productivity
trigger_keywords: []
dependencies:
  - lark-cli（已认证配置）
---

# Feishu Doc Skill

首次运行时会自动触发交互式配置向导，引导你完成所有设置。

## 快速开始

```bash
# 直接运行，检测到未配置时自动引导
python3 ~/.hermes/skills/feishu-doc/scripts/feishu_doc.py
```

## 功能

- 📄 **创建文档**：支持知识库模式和文件夹模式（我的空间）
- ✏️ **写入内容**：Markdown 格式，自动转飞书格式
- 🎵 **插入媒体**：音频、图片、视频
- 📨 **发送消息**：支持群聊（oc_）和私聊（ou_）

## 接口列表

### `create_node(title) -> dict | None`
自动选择模式创建文档：
- 有 `FEISHU_FOLDER_TOKEN` → 文件夹模式（我的空间）
- 有 `FEISHU_WIKI_SPACE_ID` → 知识库模式

返回 `{"token": "...", "obj_token": "...", "title": "...", "url": "..."}`

### `write_doc(obj_token, content, mode="overwrite") -> bool`
写入文档内容。`mode`: `"overwrite"`（覆盖）或 `"append"`（追加）。

### `send_message(chat_id=None, content="", user_id=None, ...) -> dict`
发送消息。群聊用 `chat_id`（oc_ 开头），私聊用 `user_id`（ou_ 开头）。

### `send_text_with_audio(doc_title, doc_url, summary_text, audio_path=None, chat_id=None, user_id=None) -> bool`
发送组合消息：文字摘要 + 文档链接 + 语音附件（可选）。

### `create_doc_and_write(title, markdown_content) -> dict | None`
一次性创建并写入内容。

### `is_configured() -> bool`
检查飞书是否已配置（文档创建 或 消息发送 至少有一项）。

### `check_and_guide()`
检测配置，不完整则触发交互式引导。

## 配置（`.env.feishu`）

安装脚本会在目标目录不存在 `.env.feishu` 时，由 `.env.example` 自动生成：

```text
~/.hermes/skills/feishu-doc/.env.example -> ~/.hermes/skills/feishu-doc/.env.feishu
```

已有 `.env.feishu` 会被保留，不会被更新覆盖。首次运行时也可通过 `setup_guide.py` 引导配置，或手动编辑 `~/.hermes/skills/feishu-doc/.env.feishu`：

```env
#━━━ 文档创建（二选一）━━━

# 【知识库模式】
# 用途：把日报创建到飞书知识库中，适合长期沉淀。
# FEISHU_WIKI_SPACE_ID：目标知识库 ID。
#   获取方式：浏览器打开飞书知识库首页，查看 URL 中的 wiki space 标识。
#   如果使用个人知识库，lark-cli 支持的特殊值通常是 my_library。
# FEISHU_PARENT_NODE_TOKEN：可选，目标父节点/目录 token。
#   获取方式：打开知识库中的目标目录或页面，查看 URL 中 node= 后面的值。
#   留空时通常创建在知识库根目录。
FEISHU_WIKI_SPACE_ID=
FEISHU_PARENT_NODE_TOKEN=

# 【文件夹模式】
# 用途：把日报创建到飞书云文档文件夹中，适合个人空间/共享文件夹。
# FEISHU_FOLDER_TOKEN：目标文件夹 token。
#   获取方式：浏览器打开目标文件夹，复制 URL 中 /folder/ 后面的字符。
# 注意：如果同时配置文件夹模式和知识库模式，代码优先使用文件夹模式。
FEISHU_FOLDER_TOKEN=

#━━━ 消息发送（二选一）━━━

# 【群聊】
# 用途：日报生成后，把摘要和文档链接推送到飞书群。
# FEISHU_CHAT_ID：群聊 open_chat_id，通常以 oc_ 开头。
#   获取方式：运行 lark-cli im chats list --as user，找到目标群的 chat_id。
#   也可以运行 lark-cli im +chat-search --as user --query "群名" 搜索。
#   或在飞书 Desktop 的群设置中复制群 ID。
FEISHU_CHAT_ID=

# 【私聊】
# 用途：日报生成后，把摘要和文档链接推送给某个用户。
# FEISHU_USER_ID：用户 open_id，通常以 ou_ 开头。
#   获取方式：运行 lark-cli contact +search-user "姓名"，找到 ou_ 开头的 ID。
#   或在飞书 Desktop 中打开联系人信息并复制用户 ID。
# 注意：消息发送目标二选一即可。若同时配置，发送逻辑会按代码规则选择目标。
FEISHU_USER_ID=

# FEISHU_SEND_AS：消息发送身份，user 或 bot。
# 默认 user；如果要用 bot，请先把应用机器人加入目标群。
FEISHU_SEND_AS=user
```

获取方式：
- `lark-cli im chats list --as user` → 查看当前用户可见群（oc_）
- `lark-cli im +chat-search --as user --query "群名"` → 按群名搜索
- `lark-cli contact +search-user "姓名"` → 查找用户 ID（ou_）
- 飞书 Desktop → 群设置 / 联系人 → 复制 ID

## 优先级规则

- **文档创建**：`FEISHU_FOLDER_TOKEN` > `FEISHU_WIKI_*`（前者存在就用文件夹模式）
- **消息发送**：`FEISHU_CHAT_ID` / `FEISHU_USER_ID` 指定目标，`FEISHU_SEND_AS` 指定用 `user` 还是 `bot` 身份发送。
