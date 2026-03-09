"""
Retriever for TCM knowledge base
"""

from typing import List, Dict, Optional
from .vector_store import VectorStore
from .knowledge_base import KnowledgeBase, Document
from .config import TOP_K


class Retriever:
    """Document retriever with course filtering"""
    
    def __init__(self, vector_store: VectorStore = None):
        self.vector_store = vector_store or VectorStore()
        self.knowledge_base = KnowledgeBase()
    
    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        course: Optional[str] = None,
        doc_type: Optional[str] = None,  # "outline" or "transcript"
    ) -> List[Dict]:
        """Retrieve relevant documents"""
        # Build filter
        filter_dict = {}
        if course:
            filter_dict["course"] = course
        if doc_type:
            filter_dict["type"] = doc_type
        
        filter_dict = filter_dict if filter_dict else None
        
        # Search
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            filter_dict=filter_dict,
        )
        
        return results
    
    def retrieve_with_context(
        self,
        query: str,
        top_k: int = TOP_K,
        course: Optional[str] = None,
    ) -> Dict:
        """Retrieve documents with formatted context for LLM"""
        results = self.retrieve(query, top_k=top_k, course=course)
        
        if not results:
            return {
                "results": [],
                "context": "",
                "sources": [],
            }
        
        # Format context
        context_parts = []
        sources = []
        
        for i, result in enumerate(results, 1):
            meta = result["metadata"]
            source = f"{meta.get('course', 'Unknown')} - {meta.get('filename', 'Unknown')}"
            
            context_parts.append(
                f"[参考{i}] {source}\n{result['content'][:800]}..."
            )
            sources.append({
                "rank": i,
                "source": source,
                "score": result["score"],
                "type": meta.get("type", "unknown"),
            })
        
        return {
            "results": results,
            "context": "\n\n".join(context_parts),
            "sources": sources,
        }
    
    def index_knowledge_base(self, chunk: bool = True):
        """Index all documents from knowledge base"""
        # Load documents
        print("Loading documents from knowledge base...")
        documents = self.knowledge_base.load_documents()
        print(f"Loaded {len(documents)} documents")
        
        if not documents:
            return 0
        
        # Chunk documents if requested
        if chunk:
            print("Chunking documents...")
            all_chunks = []
            for doc in documents:
                chunks = self.knowledge_base.chunk_document(doc)
                all_chunks.extend(chunks)
            print(f"Created {len(all_chunks)} chunks")
            
            # Add to vector store
            print("Indexing chunks...")
            self.vector_store.add_documents(documents, all_chunks)
        else:
            print("Indexing documents (no chunking)...")
            self.vector_store.add_documents(documents)
        
        stats = self.vector_store.get_stats()
        return stats.get("count", 0)
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = TOP_K,
        keyword_weight: float = 0.3,
    ) -> List[Dict]:
        """Hybrid search: semantic + keyword matching"""
        # Semantic search
        semantic_results = self.retrieve(query, top_k=top_k * 2)
        
        # Simple keyword scoring
        query_keywords = set(query.lower().split())
        
        for result in semantic_results:
            content = result["content"].lower()
            keyword_matches = sum(1 for kw in query_keywords if kw in content)
            keyword_score = keyword_matches / len(query_keywords) if query_keywords else 0
            
            # Combine scores
            result["score"] = (1 - keyword_weight) * result["score"] + keyword_weight * keyword_score
        
        # Re-sort by combined score
        semantic_results.sort(key=lambda x: x["score"], reverse=True)
        
        return semantic_results[:top_k]
