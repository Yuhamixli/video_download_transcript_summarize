# 🏥 TCM RAG 知识库系统

基于 RAG (Retrieval-Augmented Generation) 的中医知识问答系统。

## 功能

- **知识整合**: 自动合并 `outlines/` 和 `transcripts_corrected/` 到知识库
- **语义检索**: 使用 BGE 中文嵌入模型进行相似度搜索
- **智能问答**: 基于检索内容的中医专业问答
- **课程过滤**: 可按具体课程范围进行检索

## 目录结构

```
knowledge/              # 知识库 (合并 outlines + transcripts)
├── outlines/          # 结构化大纲
└── transcripts/       # 纠错后的转录文本

vector_db/             # 向量数据库 (ChromaDB)
rag/                   # RAG 模块
├── config.py          # 配置
├── knowledge_base.py  # 知识库管理
├── embeddings.py      # 嵌入模型
├── vector_store.py    # 向量存储
├── retriever.py       # 检索器
└── chat_engine.py     # 对话引擎

rag_chat.py            # 交互式对话入口
```

## 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 嵌入模型 (自动下载，约 1.3GB)
# 首次运行时会自动下载 BAAI/bge-large-zh-v1.5
```

### 2. 初始化知识库

```bash
# 同步 outlines 和 transcripts 到 knowledge/
python scripts/knowledge_sync.py

# 构建向量索引
python scripts/knowledge_sync.py --index
```

### 3. 启动对话

```bash
# 交互式对话
python rag_chat.py

# 单次查询
python rag_chat.py -q "什么是六经辨证？"

# 指定课程范围
python rag_chat.py -q "肺经的循行路线" -c "实用经络针灸学"
```

## 使用指南

### 交互命令

在对话中可用以下命令：

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/courses` | 列出可用课程 |
| `/search <关键词>` | 仅搜索文档 |
| `/course <课程名>` | 设置课程范围 |
| `/clear` | 清空对话历史 |
| `/quit` | 退出 |

### 示例对话

```
💬 什么是五行相生相克？

📝 回答：
五行相生相克是中医基础理论的核心内容...

📚 参考资料：
  [1] 中医辨证学 - 167_0112中医辨证学-五行辨证.md (相关度: 0.92)
  [2] 中医初级入门 - 096_013五行-五行相生相克.md (相关度: 0.89)
```

### 课程范围查询

```
[course: 实用经络针灸学] 💬 手太阴肺经的原穴是什么？
```

## 技术细节

### 嵌入模型

- **模型**: BAAI/bge-large-zh-v1.5 (专为中文优化)
- **维度**: 1024
- **距离度量**: 余弦相似度

### 分块策略

- **块大小**: 512 tokens
- **重叠**: 128 tokens
- **边界**: 优先在段落或句子边界切分

### 检索策略

- **基础检索**: 向量相似度搜索
- **MMR**: 最大边际相关性，增加结果多样性
- **混合搜索**: 语义 + 关键词匹配

## 与现有流程集成

处理完视频后，知识库会自动更新：

```bash
# 1. 转录
python transcribe.py

# 2. 术语纠错 (自动同步到 knowledge/)
python fix_terminology.py

# 3. 生成大纲 (自动同步到 knowledge/)
python generate_outline.py

# 4. 手动同步 (如需立即更新索引)
python scripts/knowledge_sync.py --index
```

## 性能优化

- **首次运行**: 会下载嵌入模型 (约 1.3GB)
- **索引构建**: 对 400+ 文档约需 2-3 分钟
- **查询速度**: 本地检索 < 100ms
- **GPU 加速**: 如有 CUDA，嵌入生成可加速 5-10 倍

## 故障排除

### 模型下载失败

```python
# 手动下载嵌入模型
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
model.save("./models/bge-large-zh-v1.5")
```

### 索引损坏

```bash
# 删除重建
rm -rf vector_db/
python scripts/knowledge_sync.py --index
```

### 内存不足

```python
# rag/config.py 中减小批量大小
CHUNK_SIZE = 256  # 默认 512
EMBEDDING_DEVICE = "cpu"  # 使用 CPU 而非 GPU
```
