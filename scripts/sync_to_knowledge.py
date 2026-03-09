#!/usr/bin/env python3
"""
Auto-sync processed transcripts and outlines to knowledge base
Can be called by other scripts after processing
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import KnowledgeBase
from rag.retriever import Retriever


def sync_transcript_to_knowledge(txt_path: str, corrected_text: str, course: str = None):
    """
    Sync a single processed transcript to knowledge base
    Called by fix_terminology.py after processing each file
    """
    kb = KnowledgeBase()
    
    # Determine course from path
    if not course:
        rel_path = os.path.relpath(txt_path, os.path.join(os.path.dirname(__file__), "..", "transcripts_corrected"))
        parts = rel_path.replace("\\", "/").split("/")
        course = parts[0] if len(parts) > 1 else "其他"
    
    # Build destination path
    filename = os.path.basename(txt_path)
    dest_dir = os.path.join(kb.transcripts_dir, course)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    
    # Write file
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(corrected_text)
    
    return dest_path


def sync_outline_to_knowledge(md_path: str, content: str, course: str = None):
    """
    Sync a generated outline to knowledge base
    Called by generate_outline.py after generating each outline
    """
    kb = KnowledgeBase()
    
    # Determine course from path
    if not course:
        rel_path = os.path.relpath(md_path, os.path.join(os.path.dirname(__file__), "..", "outlines"))
        parts = rel_path.replace("\\", "/").split("/")
        course = parts[0] if len(parts) > 1 else "其他"
    
    # Build destination path
    filename = os.path.basename(md_path)
    dest_dir = os.path.join(kb.outlines_dir, course)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    
    # Write file
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return dest_path


def update_vector_store(document_type: str = "all"):
    """
    Update vector store with new documents
    Called periodically or after batch processing
    """
    try:
        retriever = Retriever()
        retriever.index_knowledge_base(chunk=True)
        return True
    except Exception as e:
        print(f"Vector store update failed: {e}")
        return False


if __name__ == "__main__":
    # Direct execution - full sync
    kb = KnowledgeBase()
    stats = kb.sync_all()
    print(f"Synced {stats['total']} files to knowledge base")
