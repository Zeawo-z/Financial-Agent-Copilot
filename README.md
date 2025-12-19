# 🚀 Personal Copilot - 智能助手

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LangChain](https://img.shields.io/badge/LangChain-0.1-green)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)

## 📖 项目介绍
这是一个基于 **LLM Agent (ReAct 架构)** 开发的垂直领域智能助手。它不仅仅是一个聊天机器人，更是一个能够自主使用工具的**金融分析师**。

它可以帮助用户：
- 📈 **查询实时行情**：获取 A 股/美股的实时股价、PE、市值等核心指标。
- 📰 **分析舆情面**：自动检索互联网最新的财经新闻与利好利空消息。
- 🧠 **生成投资建议**：结合基本面数据与消息面，生成专业的深度分析报告。

## 🛠️ 技术架构
- **核心框架**: LangChain (ReAct Agent)
- **大模型**: Qwen-2.5-7B (via SiliconFlow API)
- **前端交互**: Streamlit (支持流式输出 + 动态 K 线图)
- **后端服务**: FastAPI (异步接口)
- **工具链**: yfinance (数据), DuckDuckGo (搜索)

## ⚡️ 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/你的用户名/Financial-Agent-Copilot.git
cd Financial-Agent-Copilot
```
### 2. 安装依赖
```bash
pip install -r requirements.txt
```
### 3. 配置环境变量
复制 .env.example 为 .env，并填入你的 API Key：
```bash
OPENAI_API_KEY=sk-xxxx
OPENAI_API_BASE=https://api.siliconflow.cn/v1
API_KEY=
```
### 4. 启动应用
后端：
```py
python main.py
```
前端：
```py
streamlit run app.py
```
### 5. 效果图
<img width="2421" height="1371" alt="image" src="https://github.com/user-attachments/assets/220a8ed3-5417-451a-937a-6f590d432901" />

