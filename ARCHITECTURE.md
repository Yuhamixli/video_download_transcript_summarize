# TCM RAG System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG Knowledge System                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   outlines/     │    │ transcripts/    │    │  transcripts │  │
│  │   (Markdown)    │    │ _corrected/    │    │ _corrected/  │  │
│  │                 │    │   (Text)        │    │              │  │
│  │ • 结构化大纲    │    │ • 纠错后转录    │    │   (Source)   │  │
│  │ • 课程知识点    │    │ • 完整讲座内容  │    │              │  │
│  │ • 表格对比      │    │ • 台湾口音优化  │    │              │  │
│  └────────┬────────┘    └────────┬────────┘    └──────┬───────┘  │
│           │                      │                     │          │
│           └──────────────────────┼─────────────────────┘          │
│                                  │                                │
│                          ┌───────▼────────┐                      │
│                          │   knowledge/    │                      │
│                          │  (Unified KB)   │                      │
│                          │                 │                      │
│                          │ • outlines/     │                      │
│                          │ • transcripts/  │                      │
│                          └───────┬────────┘                      │
│                                  │                                │
│                    ┌───────────────┼───────────────┐               │
│                    │               │               │               │
│           ┌────────▼─────┐ ┌──────▼──────┐ ┌─────▼──────┐       │
│           │   Sync Tool   │ │  Chunking   │ │  Metadata   │       │
│           │               │ │             │ │  Extraction │       │
│           │ • File copy   │ │ • 512 tokens│ │ • Course    │       │
│           │ • Dedup       │ │ • Overlap   │ │ • Type      │       │
│           │ • Incremental │ │ • Boundary  │ │ • Filename  │       │
│           └───────┬───────┘ └──────┬──────┘ └──────┬─────┘       │
│                   │                │              │              │
│                   └────────────────┼──────────────┘              │
│                                    │                              │
│                           ┌────────▼────────┐                    │
│                           │  BGE Embeddings   │                    │
│                           │                 │                    │
│                           │ Model: bge-large│                    │
│                           │ -zh-v1.5        │                    │
│                           │                 │                    │
│                           │ • 1024 dims     │                    │
│                           │ • Cosine sim    │                    │
│                           │ • Query prompt  │                    │
│                           └────────┬────────┘                    │
│                                    │                              │
│                           ┌────────▼────────┐                    │
│                           │   Vector Store    │                    │
│                           │                 │                    │
│                           │ ChromaDB +      │                    │
│                           │ HNSW index      │                    │
│                           │                 │                    │
│                           │ • Persistent    │                    │
│                           │ • Cosine space  │                    │
│                           │ • MMR retrieval │                    │
│                           └────────┬────────┘                    │
│                                    │                              │
│  ┌─────────────────────────────────▼──────────────────────────┐  │
│  │                     RAG Chat Engine                          │  │
│  │                                                              │  │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐     │  │
│  │  │   User       │   │  Retriever   │   │    LLM       │     │  │
│  │  │   Query      │──▶│              │──▶│  (Kimi/      │     │  │
│  │  │              │   │ • Semantic   │   │   MiniMax)   │     │  │
│  │  └──────────────┘   │ • Keyword  │   │              │     │  │
│  │                     │ • MMR      │   └──────────────┘     │  │
│  │                     │ • Filter   │           │            │  │
│  │                     └──────────────┘           ▼            │  │
│  │                                     ┌──────────────┐       │  │
│  │                                     │   Response   │       │  │
│  │                                     │   + Sources  │       │  │
│  │                                     └──────────────┘       │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. Video Processing Pipeline
   ==========================
   downloads/*.mp4
        ↓
   transcribe.py (faster-whisper)
        ↓
   transcripts/{course}/*.txt
        ↓
   build_transcript_manifest.py (--date or --source-dir)
        ↓
   fix_terminology.py (LLM correction)
        ↓
   transcripts_corrected/{course}/*.txt ─────┐
        ↓                                     │
   generate_outline.py (LLM outline)         │
        ↓                                     │
   outlines/{course}/*.md ─────────────────┤
                                            │
                                            ▼
                                    knowledge_sync.py
                                            │
   ┌────────────────────────────────────────┘
   ▼
2. Knowledge Ingestion
   ====================
   knowledge/
   ├── outlines/{course}/*.md
   └── transcripts/{course}/*.txt
        ↓
   KnowledgeBase.load_documents()
        ↓
   Document chunking (512/128 overlap)
        ↓
   BGE embedding generation
        ↓
   ChromaDB vector store
        ↓
3. Query & Retrieval
   ==================
   User query
        ↓
   Query embedding (with prompt)
        ↓
   Vector similarity search (top-k=5)
        ↓
   MMR re-ranking (diversity)
        ↓
   Context assembly
        ↓
   LLM generation
        ↓
   Answer + Source citations
```

## Components

### 1. Knowledge Base (`rag/knowledge_base.py`)

- **Purpose**: Manage document ingestion and synchronization
- **Key Classes**:
  - `Document`: Represents a document with metadata
  - `KnowledgeBase`: Sync, load, and chunk documents
- **Features**:
  - Incremental sync from outlines/transcripts
  - Automatic chunking with boundary detection
  - Course metadata extraction

### 2. Embeddings (`rag/embeddings.py`)

- **Purpose**: Generate vector representations
- **Model**: BAAI/bge-large-zh-v1.5 (Chinese optimized)
- **Features**:
  - Singleton pattern (single model load)
  - Query prompt templates for asymmetric search
  - Local caching

### 3. Vector Store (`rag/vector_store.py`)

- **Purpose**: Store and retrieve vectors
- **Backend**: ChromaDB with DuckDB + Parquet
- **Features**:
  - Persistent storage
  - Cosine similarity
  - MMR (Maximal Marginal Relevance) for diversity

### 4. Retriever (`rag/retriever.py`)

- **Purpose**: Search and retrieve relevant documents
- **Features**:
  - Semantic search
  - Hybrid search (semantic + keyword)
  - Course/type filtering
  - Context assembly for LLM

### 5. Chat Engine (`rag/chat_engine.py`)

- **Purpose**: RAG-based question answering
- **Features**:
  - System prompt for TCM expert persona
  - Conversation history
  - Course-aware retrieval
  - Source citations

## Configuration

See `rag/config.py`:

```python
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
TOP_K = 5
MMR_DIVERSITY = 0.3
VECTOR_DB_DIR = "vector_db/"
```

## Usage Patterns

### Pattern 1: Full Knowledge Sync
```bash
python scripts/knowledge_sync.py --index
```

### Pattern 2: Interactive Q&A
```bash
python rag_chat.py
```

### Pattern 3: Programmatic Access
```python
from rag import ChatEngine, KnowledgeBase

# Initialize
chat = ChatEngine()

# Query
response = chat.chat("什么是六经辨证？")
print(response["answer"])
print(response["sources"])
```

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Embedding dim | 1024 |
| Chunk size | 512 tokens |
| Index time | ~2 min for 400 docs |
| Query latency | < 100ms |
| Model size | ~1.3 GB |
| Disk usage | ~500 MB (vectors) |

## Future Extensions

1. **Multi-modal**: Add video timestamp links
2. **Fine-tuning**: Domain-specific embedding fine-tuning
3. **Web UI**: Streamlit/Gradio interface
4. **API Server**: FastAPI for remote access
5. **Citation Highlight**: Show exact text spans
