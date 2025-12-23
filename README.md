# LLM Daily - Telegram Knowledge Base CLI

> 输入链接，自动解析内容，生成双语摘要和标签，一键发布到 Telegram 频道
>
> Input a link, auto-parse content, generate bilingual summaries and tags, publish to Telegram with one click

**Language / 语言**: [中文](#中文) | [English](#english)

---

# 中文

输入链接 → 自动解析内容 → 生成双语摘要和标签 → 一键发布到 Telegram 频道

<video src="https://github.com/0xPabloxx/telegram_knowledge_base_agent/raw/main/demo.mp4" controls width="100%"></video>

**输出示例：**

```
输入: https://arxiv.org/abs/2312.xxxxx


输出到 Telegram:
📌 稳定大语言模型强化学习：公式化方法与实践

📅 2024-12-01

📝 本文提出了一种新颖的大语言模型强化学习公式...

🔗 https://arxiv.org/abs/2312.xxxxx

🏷️ #论文 #Paper #大语言模型 #LLM #强化学习 #RL

────────────────────

📌 Stabilizing Reinforcement Learning with LLMs: Formulation and Practices

📅 2024-12-01

📝 This paper proposes a novel formulation for RL with LLMs...

🔗 https://arxiv.org/abs/2312.xxxxx

🏷️ #Paper #paper #LLM #llm #RL #rl
```

## 支持的链接类型

| 类型 | 状态 | 说明 |
|------|------|------|
| ArXiv | ✅ 已支持 | 自动提取论文标题、摘要、发布日期 |
| 微信公众号 | ✅ 已支持 | 解析文章内容 |
| 通用网页 | ✅ 已支持 | 自动提取正文内容 |
| GitHub | 🚧 计划中 | 解析 README、仓库信息 |
| 知乎 | 🚧 计划中 | 专栏文章、回答 |
| HuggingFace | 🚧 计划中 | Papers、Models、Datasets |
| 小红书 | 🚧 计划中 | 笔记内容 |
| Twitter/X | 🚧 计划中 | 推文内容 |

## 核心功能

- **自动解析**: 输入链接，自动抓取网页内容
- **双语输出**: LLM 生成中英文标题和摘要
- **智能标签**: 从预设标签匹配 + 自动生成新标签
- **日期提取**: 自动提取文章发布日期
- **一键发布**: 确认后直接发布到 Telegram 频道

## 安装

```bash
git clone https://github.com/0xPabloxx/telegram_knowledge_base_agent.git
cd telegram_knowledge_base_agent

python3 -m venv venv
source venv/bin/activate

pip install -e .
```

## 配置

创建 `.env` 文件：

```bash
# Telegram
KB_TELEGRAM_BOT_TOKEN=your_bot_token
KB_TELEGRAM_CHANNEL_ID=@your_channel

# LLM (支持: deepseek, openai, gemini, anthropic, kimi, minimax, glm)
KB_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key

# 预设标签
KB_PRESET_TAGS=Paper,LLM,Agent,Research,Tutorial
```

## 使用

```bash
source venv/bin/activate
kb
```

然后输入链接即可：
```
▶ 有什么想收藏的？
https://arxiv.org/abs/2312.xxxxx
```

---

# English

Input a link → Auto-parse content → Generate bilingual summaries & tags → Publish to Telegram

**Output Example:**

```
Input: https://arxiv.org/abs/2312.xxxxx

Output to Telegram:
📌 Chinese Title (auto-translated)

📅 2024-12-01

📝 Chinese summary...

🔗 https://arxiv.org/abs/2312.xxxxx

🏷️ #Chinese #Tags

────────────────────

📌 English Title

📅 2024-12-01

📝 English summary...

🔗 https://arxiv.org/abs/2312.xxxxx

🏷️ #English #Tags
```

## Supported Link Types

| Type | Status | Description |
|------|--------|-------------|
| ArXiv | ✅ Supported | Auto-extract paper title, abstract, date |
| WeChat Articles | ✅ Supported | Parse article content |
| General Web | ✅ Supported | Auto-extract main content |
| GitHub | 🚧 Planned | Parse README, repo info |
| Zhihu | 🚧 Planned | Articles, answers |
| HuggingFace | 🚧 Planned | Papers, Models, Datasets |
| Xiaohongshu | 🚧 Planned | Note content |
| Twitter/X | 🚧 Planned | Tweet content |

## Core Features

- **Auto-parsing**: Input a link, automatically scrape web content
- **Bilingual Output**: LLM generates Chinese and English titles/summaries
- **Smart Tags**: Match from presets + auto-generate new tags
- **Date Extraction**: Auto-extract article publish date
- **One-click Publish**: Publish to Telegram channel after confirmation

## Installation

```bash
git clone https://github.com/0xPabloxx/telegram_knowledge_base_agent.git
cd telegram_knowledge_base_agent

python3 -m venv venv
source venv/bin/activate

pip install -e .
```

## Configuration

Create `.env` file:

```bash
# Telegram
KB_TELEGRAM_BOT_TOKEN=your_bot_token
KB_TELEGRAM_CHANNEL_ID=@your_channel

# LLM (supports: deepseek, openai, gemini, anthropic, kimi, minimax, glm)
KB_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key

# Preset Tags
KB_PRESET_TAGS=Paper,LLM,Agent,Research,Tutorial
```

## Usage

```bash
source venv/bin/activate
kb
```

Then input a link:
```
▶ What do you want to save?
https://arxiv.org/abs/2312.xxxxx
```

---

## Supported LLM Providers

| Provider | Model |
|----------|-------|
| DeepSeek | deepseek-chat |
| OpenAI | gpt-4o-mini |
| Anthropic | claude-3-5-sonnet |
| Google Gemini | gemini-1.5-flash |
| Kimi | moonshot-v1-8k |
| MiniMax | abab6.5s-chat |
| GLM | glm-4-flash |

## License

MIT
