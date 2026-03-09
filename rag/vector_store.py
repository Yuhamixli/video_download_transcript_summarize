"""
Vector store using ChromaDB for local storage.
"""

import os
from typing import List, Dict, Optional

import numpy as np

try:
    import chromadb
except ImportError:
    chromadb = None

from .config import VECTOR_DB_DIR, TOP_K
from .embeddings import EmbeddingProvider
from .knowledge_base import Document


class VectorStore:
    """ChromaDB-based vector store for document retrieval"""
    
    def __init__(self, collection_name: str = "tcm_knowledge"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embedding_provider = EmbeddingProvider()
        
        if chromadb is not None:
            self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB client"""
        os.makedirs(VECTOR_DB_DIR, exist_ok=True)

        # Chroma 0.5+ uses PersistentClient with a sqlite-backed local store.
        self.client = chromadb.PersistentClient(path=VECTOR_DB_DIR)

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    
    def add_documents(self, documents: List[Document], chunks: List[Document] = None):
        """Add documents to vector store"""
        if chromadb is None:
            print("Warning: ChromaDB not installed. Run: pip install chromadb")
            return
        
        docs_to_add = chunks if chunks else documents
        
        if not docs_to_add:
            return
        
        # Generate embeddings
        texts = [doc.content for doc in docs_to_add]
        embeddings = self.embedding_provider.embed(texts)
        
        # Prepare data for Chroma
        ids = [doc.doc_id for doc in docs_to_add]
        metadatas = [doc.metadata for doc in docs_to_add]
        
        # Upsert makes re-indexing idempotent.
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
        )
    
    def search(
        self,
        query: str,
        top_k: int = TOP_K,
        filter_dict: Optional[Dict] = None,
        use_mmr: bool = True,
    ) -> List[Dict]:
        """Search for relevant documents"""
        if chromadb is None or self.collection is None:
            return []
        
        # Embed query
        query_embedding = self.embedding_provider.embed_query(query)
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k * 2 if use_mmr else top_k,
            where=filter_dict,
            include=["documents", "metadatas", "distances"],
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results["ids"][0])):
            result = {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1.0 - results["distances"][0][i],  # Convert distance to similarity
            }
            formatted_results.append(result)
        
        if use_mmr and len(formatted_results) > top_k:
            formatted_results = self._apply_mmr(
                formatted_results, 
                query_embedding, 
                top_k
            )
        
        return formatted_results[:top_k]
    
    def _apply_mmr(self, results: List[Dict], query_embedding: np.ndarray, top_k: int) -> List[Dict]:
        """Apply Maximal Marginal Relevance for diversity"""
        from .config import MMR_DIVERSITY
        
        selected = []
        remaining = results.copy()
        
        # Get embeddings for MMR
        texts = [r["content"] for r in remaining]
        embeddings = self.embedding_provider.embed(texts)
        
        while len(selected) < top_k and remaining:
            if not selected:
                # First: pick most relevant
                best = remaining[0]
                best_idx = 0
            else:
                # MMR scoring
                selected_embeddings = [embeddings[results.index(s)] for s in selected]
                
                best_score = -float('inf')
                best = None
                best_idx = -1
                
                for i, candidate in enumerate(remaining):
                    relevance = candidate["score"]
                    
                    # Max similarity to already selected
                    cand_emb = embeddings[results.index(candidate)]
                    max_sim = max(
                        np.dot(cand_emb, sel_emb) 
                        for sel_emb in selected_embeddings
                    )
                    
                    mmr_score = MMR_DIVERSITY * relevance - (1 - MMR_DIVERSITY) * max_sim
                    
                    if mmr_score > best_score:
                        best_score = mmr_score
                        best = candidate
                        best_idx = i
            
            selected.append(best)
            remaining.pop(best_idx)
        
        return selected
    
    def delete_collection(self):
        """Delete the collection"""
        if not self.client:
            return
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        if self.collection is None:
            return {"count": 0}
        
        count = self.collection.count()
        return {"count": count}
