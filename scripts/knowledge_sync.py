#!/usr/bin/env python3
"""
Sync knowledge base from outlines and transcripts

Usage:
    python scripts/knowledge_sync.py
    python scripts/knowledge_sync.py --index  # Also rebuild index
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import KnowledgeBase
from rag.retriever import Retriever


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync TCM knowledge base")
    parser.add_argument("--index", action="store_true", help="Rebuild vector index after sync")
    args = parser.parse_args()
    
    print("=" * 60)
    print(" 知识库同步工具")
    print("=" * 60)
    print()
    
    # Sync
    kb = KnowledgeBase()
    stats = kb.sync_all()
    
    print(f"[OK] 大纲同步完成: {stats['outlines']} 个文件")
    print(f"[OK] 转录文本同步完成: {stats['transcripts']} 个文件")
    print(f"[OK] 总计: {stats['total']} 个文件")
    print()
    
    # Index if requested
    if args.index:
        print("正在构建向量索引...")
        retriever = Retriever()
        count = retriever.index_knowledge_base(chunk=True)
        print(f"\n[OK] 索引完成! 共 {count} 个文档块")
    else:
        print("提示: 使用 --index 参数可立即构建向量索引")
        print("      python scripts/knowledge_sync.py --index")
    
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
