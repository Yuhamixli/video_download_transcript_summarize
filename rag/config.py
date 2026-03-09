"""RAG Configuration"""

import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")

# Collections
COLLECTION_OUTLINES = "outlines"
COLLECTION_TRANSCRIPTS = "transcripts"
COLLECTION_ALL = "all"

# Embedding settings
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"  # Faster first-run on Windows
EMBEDDING_DEVICE = "auto"  # auto, cpu, cuda
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128

# Retrieval settings
TOP_K = 5
MMR_DIVERSITY = 0.3

# LLM settings (for RAG)
RAG_LLM_MODEL = "moonshotai/kimi-k2.5"
RAG_MAX_TOKENS = 2000
RAG_TEMPERATURE = 0.3
