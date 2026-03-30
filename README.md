# 三省六部 · Edict

> 一个以edict(中国古代「三省六部制」)为设计灵感的 **多 Agent 协作系统**，用 LLM 驱动的角色模拟任务分拣、方案规划、审核驳回、任务分发与执行汇聚的完整工作流。脱离openclaw, 完全独立。

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 特性

- **零框架依赖后端** — 纯 Python 标准库 HTTP 服务，`pip install -r requirements.txt` 即可运行
- **多 LLM 支持** — OpenAI / Anthropic / DeepSeek / Ollama / 任意兼容接口，一个配置切换
- **完整工作流引擎** — 太子分拣 → 中书省规划 → 门下省审议（可封驳回）→ 尚书省分发 → 六部执行 → 汇总审核
- **Web 看板 UI** — 古风主题单文件前端，实时查看任务流转、进展日志、最终结果
- **命令行 & 交互式终端** — 支持 dashboard / 单次运行 / 交互模式三种使用方式
- **状态机 + 持久化** — 任务全生命周期状态管理，JSON 文件持久化，重启不丢失

## 🏛️ 架构

```
用户旨意
  │
  ▼
👑 太子 (Taizi)          ← 消息分拣：闲聊 or 正式任务
  │
  ▼
📜 中书省 (Zhongshu)     ← 规划方案，拆分子任务
  │
  ▼
⚖️ 门下省 (Menxia)       ← 审核方案（可封驳，最多3轮）
  │
  ▼
📋 尚书省 (Shangshu)     ← 分发给六部执行并汇总
  │
  ├─▶ 户部 (hubu)     — 数据/资源
  ├─▶ 礼部 (libu)     — 文档/规范
  ├─▶ 兵部 (bingbu)   — 代码/工程
  ├─▶ 刑部 (xingbu)   — 安全/合规
  ├─▶ 工部 (gongbu)   — 基础设施
  └─▶ 吏部 (libu_hr)  — 人员/评估
  │
  ▼
汇总审核 → ✅ Done
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/edict-standalone.git
cd edict-standalone
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 LLM

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key 和模型配置
```

支持的 LLM 提供商：

| 提供商 | `LLM_PROVIDER` | 说明 |
|--------|---------------|------|
| OpenAI | `openai` | GPT-4o / GPT-3.5 等 |
| Anthropic | `anthropic` | Claude 系列模型 |
| DeepSeek | `deepseek` | deepseek-chat / deepseek-coder |
| Ollama | `ollama` | 本地模型，无需 API Key |
| 智谱 AI | `openai` + `LLM_BASE_URL` | GLM 系列，使用兼容接口 |

> 💡 使用任意 OpenAI 兼容 API 时，只需设置 `LLM_BASE_URL` 为对应的 endpoint 即可。

### 4. 启动

**看板模式**（推荐，有 Web UI）：
```bash
python main.py
# 浏览器访问 http://127.0.0.1:7891
```

**命令行单次运行**：
```bash
python main.py run "帮我写一个 Python 快速排序，并附上单元测试"
```

**交互式终端**：
```bash
python main.py chat
```

## 📁 项目结构

```
edict-standalone/
├── main.py                  # 程序入口（支持 dashboard / run / chat 三种模式）
├── logger.py                # 统一日志配置
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量模板
├── README.md
├── LICENSE
├── scripts/
│   ├── __init__.py
│   ├── agents.py            # 各 Agent 角色 & 系统提示词
│   ├── llm_client.py        # LLM 统一封装（多提供商路由）
│   ├── orchestrator.py      # 编排引擎（完整流水线驱动）
│   └── task_store.py        # 任务状态机 & JSON 持久化
├── dashboard/
│   ├── server.py            # 纯 Python HTTP 服务器（REST API）
│   └── static/
│       └── index.html       # 看板前端（单文件纯 HTML）
└── test/
    └── api.py               # API 连接测试脚本
```

## 🔧 环境变量

在 `.env` 文件中配置：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_PROVIDER` | 是 | `openai` | LLM 提供商：openai / anthropic / deepseek / ollama |
| `LLM_MODEL` | 是 | `gpt-4o` | 模型名称 |
| `LLM_API_KEY` | 是* | — | API Key（ollama 不需要） |
| `LLM_BASE_URL` | 否 | — | 自定义 API 地址（中转/Ollama） |
| `DASHBOARD_HOST` | 否 | `127.0.0.1` | Dashboard 监听地址 |
| `DASHBOARD_PORT` | 否 | `7891` | Dashboard 监听端口 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

## 📄 License

[MIT](LICENSE)
