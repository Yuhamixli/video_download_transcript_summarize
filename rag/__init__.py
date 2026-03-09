"""
Local RAG System for TCM Knowledge Base

Combines outlines and corrected transcripts for semantic search and QA.
"""

from .knowledge_base import KnowledgeBase
from .retriever import Retriever
from .chat_engine import ChatEngine

__version__ = "1.0.0"
__all__ = ["KnowledgeBase", "Retriever", "ChatEngine"]
