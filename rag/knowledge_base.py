"""
Knowledge Base Manager

Handles syncing and indexing documents from outlines/ and transcripts_corrected/
"""

import os
import glob
import hashlib
from typing import List, Dict, Tuple
from pathlib import Path

from .config import (
    KNOWLEDGE_DIR,
    VECTOR_DB_DIR,
    COLLECTION_OUTLINES,
    COLLECTION_TRANSCRIPTS,
    COLLECTION_ALL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


class Document:
    """Represents a knowledge document"""
    
    def __init__(self, source: str, content: str, metadata: Dict = None):
        self.source = source  # File path
        self.content = content
        self.metadata = metadata or {}
        self.doc_id = self._generate_id()
        
    def _generate_id(self) -> str:
        """Generate unique ID from source + content hash"""
        key = f"{self.source}:{self.content[:100]}"
        return hashlib.md5(key.encode()).hexdigest()


class KnowledgeBase:
    """Manages the knowledge base with documents from outlines and transcripts"""
    
    def __init__(self):
        self.outlines_dir = os.path.join(KNOWLEDGE_DIR, "outlines")
        self.transcripts_dir = os.path.join(KNOWLEDGE_DIR, "transcripts")
        os.makedirs(self.outlines_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)
        os.makedirs(VECTOR_DB_DIR, exist_ok=True)
        
    def sync_from_outlines(self, outlines_dir: str = None) -> int:
        """Sync documents from outlines/ folder"""
        if outlines_dir is None:
            outlines_dir = os.path.join(os.path.dirname(KNOWLEDGE_DIR), "outlines")
        
        count = 0
        # Copy all .md files maintaining subdirectory structure
        for md_file in glob.glob(os.path.join(outlines_dir, "**", "*.md"), recursive=True):
            rel_path = os.path.relpath(md_file, outlines_dir)
            dest_path = os.path.join(self.outlines_dir, rel_path)
            
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1
            
        return count
    
    def sync_from_transcripts(self, transcripts_dir: str = None) -> int:
        """Sync documents from transcripts_corrected/ folder"""
        if transcripts_dir is None:
            transcripts_dir = os.path.join(
                os.path.dirname(KNOWLEDGE_DIR), "transcripts_corrected"
            )
        
        count = 0
        # Copy all .txt files maintaining subdirectory structure
        for txt_file in glob.glob(os.path.join(transcripts_dir, "**", "*.txt"), recursive=True):
            rel_path = os.path.relpath(txt_file, transcripts_dir)
            dest_path = os.path.join(self.transcripts_dir, rel_path)
            
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1
            
        return count
    
    def sync_all(self, outlines_dir: str = None, transcripts_dir: str = None) -> Dict[str, int]:
        """Sync both outlines and transcripts"""
        outlines_count = self.sync_from_outlines(outlines_dir)
        transcripts_count = self.sync_from_transcripts(transcripts_dir)
        return {
            "outlines": outlines_count,
            "transcripts": transcripts_count,
            "total": outlines_count + transcripts_count
        }
    
    def load_documents(self, collection: str = COLLECTION_ALL) -> List[Document]:
        """Load all documents from knowledge base"""
        documents = []
        
        if collection in (COLLECTION_OUTLINES, COLLECTION_ALL):
            for md_file in glob.glob(os.path.join(self.outlines_dir, "**", "*.md"), recursive=True):
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                rel_path = os.path.relpath(md_file, KNOWLEDGE_DIR)
                course = self._extract_course(rel_path)
                
                metadata = {
                    "type": "outline",
                    "course": course,
                    "filename": os.path.basename(md_file),
                    "path": rel_path,
                }
                
                documents.append(Document(source=rel_path, content=content, metadata=metadata))
        
        if collection in (COLLECTION_TRANSCRIPTS, COLLECTION_ALL):
            for txt_file in glob.glob(os.path.join(self.transcripts_dir, "**", "*.txt"), recursive=True):
                with open(txt_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                rel_path = os.path.relpath(txt_file, KNOWLEDGE_DIR)
                course = self._extract_course(rel_path)
                
                metadata = {
                    "type": "transcript",
                    "course": course,
                    "filename": os.path.basename(txt_file),
                    "path": rel_path,
                }
                
                documents.append(Document(source=rel_path, content=content, metadata=metadata))
        
        return documents
    
    def _extract_course(self, path: str) -> str:
        """Extract course name from path"""
        parts = Path(path).parts
        if len(parts) > 1:
            return parts[1]  # e.g., knowledge/outlines/中医辨证学/file.md
        return "其他"
    
    def chunk_document(self, doc: Document) -> List[Document]:
        """Split document into chunks"""
        content = doc.content
        chunks = []
        
        # Simple sliding window chunking
        start = 0
        chunk_id = 0
        while start < len(content):
            end = start + CHUNK_SIZE
            chunk_text = content[start:end]
            
            # Try to end at sentence or paragraph boundary
            if end < len(content):
                # Look for sentence endings
                for sep in ["\n\n", "。", "；", "\n"]:
                    pos = chunk_text.rfind(sep)
                    if pos > CHUNK_SIZE * 0.7:  # Only if we have enough content
                        end = start + pos + len(sep)
                        chunk_text = content[start:end]
                        break
            
            chunk_meta = {
                **doc.metadata,
                "chunk_id": chunk_id,
                "chunk_start": start,
                "chunk_end": end,
            }
            
            chunk_doc = Document(
                source=f"{doc.source}#{chunk_id}",
                content=chunk_text,
                metadata=chunk_meta
            )
            chunks.append(chunk_doc)
            
            chunk_id += 1
            start = end - CHUNK_OVERLAP if end < len(content) else end
        
        return chunks
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        outline_count = len(glob.glob(os.path.join(self.outlines_dir, "**", "*.md"), recursive=True))
        transcript_count = len(glob.glob(os.path.join(self.transcripts_dir, "**", "*.txt"), recursive=True))
        
        return {
            "outlines": outline_count,
            "transcripts": transcript_count,
            "total": outline_count + transcript_count,
        }
