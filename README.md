# KB - Knowledge Base CLI

> Personal knowledge base automation tool with Telegram channel publishing

**Language / 语言**: [中文](#中文) | [English](#english)

---

# 中文

## 简介

KB 是一个个人知识库自动化 CLI 工具，支持将链接、文件、文字内容自动处理并发布到 Telegram 频道。通过 LLM 自动生成双语摘要和智能标签。

## 功能特性

### 内容处理
- **链接解析**: 自动抓取网页内容，提取标题和正文
  - 支持混合输入（URL + 文字描述）
  - ArXiv 论文链接自动转换为摘要页面解析
  - 微信公众号文章解析
- **文件处理**: 支持本地文件拖拽输入
  - PDF 文档：提取文本内容
  - 图片：JPG、PNG、GIF、WebP、BMP
- **纯文字**: 支持直接输入文字内容

### AI 能力
- **双语摘要生成**: 自动生成中英文标题和摘要
  - 原标题自动翻译（非自动生成）
  - 中英文摘要独立优化
- **智能标签推荐**:
  - 从预设标签中匹配所有相关标签（不限数量）
  - 自动生成额外的具体标签
  - 中英文标签自动互译
  - 大小写变体自动生成（提升 Telegram 搜索体验）

### 多 LLM 支持
| Provider | 模型 |
|----------|------|
| DeepSeek | deepseek-chat |
| OpenAI | gpt-4o-mini |
| Anthropic | claude-3-5-sonnet |
| Google Gemini | gemini-1.5-flash |
| Kimi (Moonshot) | moonshot-v1-8k |
| MiniMax | abab6.5s-chat |
| GLM (智谱) | glm-4-flash |

### 输出格式
```
📌 中文标题

📝 中文摘要

🔗 链接

🏷️ #中文标签 #英文标签

────────────────────

📌 English Title

📝 English summary

🔗 Link

🏷️ #EnglishTag #englishtag
```

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd telegram_channel_bot

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e .
```

## 配置

创建 `.env` 文件：

```bash
# Telegram 配置
KB_TELEGRAM_BOT_TOKEN=your_bot_token
KB_TELEGRAM_CHANNEL_ID=@your_channel

# LLM 配置
KB_LLM_PROVIDER=deepseek  # 或 openai, gemini, anthropic, kimi, minimax, glm
DEEPSEEK_API_KEY=your_api_key

# 预设标签（逗号分隔）
KB_PRESET_TAGS=Paper,LLM,Agent,Research,Tutorial
```

## 使用

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动 CLI
kb
```

### 输入示例

```bash
# 纯链接
https://arxiv.org/abs/2312.xxxxx

# 链接 + 描述
https://example.com/article
这是一篇关于 AI Agent 的文章，推荐阅读！

# 本地文件（支持拖拽）
/path/to/document.pdf

# 纯文字
今天学到了一个新概念：RAG（检索增强生成）...
```

## 限制

- 仅支持 PDF 和图片文件，不支持 Word、Excel 等格式
- 图片不会进行 OCR 或视觉理解，仅记录基本信息
- 需要稳定的网络连接访问 LLM API

---

# English

## Introduction

KB is a personal knowledge base automation CLI tool that processes links, files, and text content, then publishes them to a Telegram channel. It uses LLM to automatically generate bilingual summaries and smart tags.

## Features

### Content Processing
- **Link Parsing**: Automatically scrape web content, extract title and body
  - Support mixed input (URL + text description)
  - ArXiv paper links auto-convert to abstract page for parsing
  - WeChat article parsing
- **File Processing**: Support local file drag-and-drop
  - PDF documents: Extract text content
  - Images: JPG, PNG, GIF, WebP, BMP
- **Plain Text**: Support direct text input

### AI Capabilities
- **Bilingual Summary Generation**: Auto-generate Chinese and English titles and summaries
  - Original titles are translated (not auto-generated)
  - Chinese and English summaries are independently optimized
- **Smart Tag Suggestions**:
  - Match ALL relevant tags from presets (no limit)
  - Auto-generate additional specific tags
  - Auto-translate between Chinese and English tags
  - Auto-generate case variants (improves Telegram search)

### Multi-LLM Support
| Provider | Model |
|----------|-------|
| DeepSeek | deepseek-chat |
| OpenAI | gpt-4o-mini |
| Anthropic | claude-3-5-sonnet |
| Google Gemini | gemini-1.5-flash |
| Kimi (Moonshot) | moonshot-v1-8k |
| MiniMax | abab6.5s-chat |
| GLM (Zhipu) | glm-4-flash |

### Output Format
```
📌 Chinese Title

📝 Chinese summary

🔗 Link

🏷️ #ChineseTag #EnglishTag

────────────────────

📌 English Title

📝 English summary

🔗 Link

🏷️ #EnglishTag #englishtag
```

## Installation

```bash
# Clone the project
git clone <repo-url>
cd telegram_channel_bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
```

## Configuration

Create a `.env` file:

```bash
# Telegram Configuration
KB_TELEGRAM_BOT_TOKEN=your_bot_token
KB_TELEGRAM_CHANNEL_ID=@your_channel

# LLM Configuration
KB_LLM_PROVIDER=deepseek  # or openai, gemini, anthropic, kimi, minimax, glm
DEEPSEEK_API_KEY=your_api_key

# Preset Tags (comma-separated)
KB_PRESET_TAGS=Paper,LLM,Agent,Research,Tutorial
```

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Start CLI
kb
```

### Input Examples

```bash
# Pure link
https://arxiv.org/abs/2312.xxxxx

# Link + description
https://example.com/article
This is an article about AI Agents, recommended reading!

# Local file (drag-and-drop supported)
/path/to/document.pdf

# Plain text
Today I learned a new concept: RAG (Retrieval Augmented Generation)...
```

## Limitations

- Only supports PDF and image files, not Word, Excel, etc.
- Images are not OCR'd or visually understood, only basic info is recorded
- Requires stable network connection to access LLM APIs

---

## License

MIT
