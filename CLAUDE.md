# CLAUDE.md — Research Hub

> yqzhao 的论文/知识管理工具。由 Brain Agent 跨仓管理。

## 项目定位

AI 辅助的研究知识管理系统：
- 输入：arXiv 论文、技术博客、知乎、HN/Reddit 等知识源
- 处理：Claude 阅读 + 结构化提取 + 知识图谱入库
- 输出：思维导图、知识图谱、跨文献关联、可视化 Dashboard

## 核心原则

- **不重复造轮子** — 组合现有工具，造胶水层
- **Claude Code 原生集成** — 通过 Skill / MCP 与 Brain Agent 交互
- **零外部服务** — 无 Redis、无 Docker，文件系统即数据库
- **渐进式** — 先跑起来再优化

## 技术栈

- Python 3.10+, type hints, dataclasses
- FastAPI + htmx + DaisyUI (可视化 Dashboard)
- LightRAG (知识图谱)
- Markmap (思维导图渲染)
- Semantic Scholar API / OpenAlex (元数据)
- arXiv API (论文下载)

## 关联仓库

- Brain Agent: `RanchiZhao/yqzhao-dev-infra-v2`（通过该仓库的 Brain 调度）

## Commit 格式

```
<type>(<scope>): <subject>
```

Types: feat, fix, refactor, docs, chore, test

## 分支策略

- `main` — 稳定分支
- `feat/issue-<N>-<description>` — 功能分支
- PR 由 Brain 合并
