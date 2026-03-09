#!/usr/bin/env python3
"""
Show knowledge-base and vector-store statistics.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import KnowledgeBase
from rag.retriever import Retriever


def main() -> int:
    kb = KnowledgeBase()
    stats = kb.get_stats()
    print("知识库统计:")
    print(f"  大纲: {stats['outlines']} 个")
    print(f"  转录: {stats['transcripts']} 个")
    print(f"  总计: {stats['total']} 个")

    retriever = Retriever()
    vs_stats = retriever.vector_store.get_stats()
    print(f"  向量: {vs_stats.get('count', 0)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
