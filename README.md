# Research Hub

yqzhao 的 AI 研究知识管理系统。通过 Brain Agent (Claude Code) 阅读论文和技术文章，自动构建结构化知识库和可视化知识图谱。

## 架构

```
用户 → Brain Agent (Claude Code)
         │
         ├── read-paper Skill
         │   ├── 获取内容 (arXiv API / WebFetch)
         │   ├── AI 阅读 + 结构化提取
         │   └── 存储到 data/papers/
         │
         ├── LightRAG 知识图谱
         │   ├── 自动提取实体和关系
         │   ├── 增量更新
         │   └── 跨文献查询
         │
         └── Dashboard (FastAPI + htmx + DaisyUI)
             ├── 论文列表 + 结构化摘要
             ├── 思维导图 (Markmap)
             └── 知识图谱可视化
```

## 知识源类型

| 来源 | 获取方式 |
|------|---------|
| arXiv 论文 | arXiv API |
| 技术博客 | WebFetch |
| 知乎专栏 | WebFetch |
| HN/Reddit | WebFetch |
| 会议 slides | 手动链接 |

## 数据结构

每篇论文/文章生成两个文件：

```
data/papers/
├── {date}_{id}.json          # 结构化数据
└── {date}_{id}.mindmap.md    # 思维导图 markdown
```

JSON schema:
```json
{
  "id": "2026-02-11_2602.10693",
  "source_type": "arxiv_paper | blog | zhihu | hn | reddit",
  "source_url": "https://...",
  "title": "...",
  "authors": [],
  "date": "YYYY-MM-DD",
  "summary": {
    "problem": "...",
    "method": "...",
    "innovation": "...",
    "results": "...",
    "one_liner": "中文一句话总结"
  },
  "tags": [],
  "benchmarks": [],
  "key_references": []
}
```

## 技术栈

- **后端**: Python 3.10+, FastAPI, Jinja2
- **前端**: htmx + DaisyUI (Tailwind CSS)
- **思维导图**: Markmap (CDN)
- **知识图谱**: LightRAG
- **元数据 API**: Semantic Scholar, OpenAlex
- **零外部服务**: 无 Redis, 无 Docker, 文件系统即数据库

## 关联

- Brain Agent 仓库: [yqzhao-dev-infra-v2](https://github.com/RanchiZhao/yqzhao-dev-infra-v2)
- Skill 定义: `.claude/skills/read-paper/SKILL.md` (在 Brain 仓库中)

## 开发

```bash
pip install -e ".[dev]"
python dashboard/app.py  # 启动 Dashboard
```
