"""
RAG Chat Engine for TCM QA
"""

import os
from typing import List, Dict, Optional, Generator
from openai import OpenAI

from .retriever import Retriever
from .config import (
    RAG_LLM_MODEL,
    RAG_MAX_TOKENS,
    RAG_TEMPERATURE,
)


class ChatEngine:
    """RAG-based chat engine for TCM knowledge"""
    
    SYSTEM_PROMPT = """你是一位资深的中医专家助理，基于检索到的课程内容为用户提供专业的中医知识解答。

你拥有以下课程资源：
1. 中医辨证学 - 系统讲解脏腑辨证、八纲辨证、气血津液辨证等
2. 实用经络针灸学 - 详细讲解十四经络、穴位、针灸技术
3. 方剂学 - 各类经典方剂的组成、功效、应用
4. 中医初级入门 - 中医基础理论、阴阳五行、藏象学说等

回答要求：
1. 基于检索到的参考资料进行回答，标注参考来源
2. 使用专业但易懂的语言，适当解释中医术语
3. 如涉及具体方剂、穴位，请给出详细信息
4. 如资料不足以回答问题，请诚实说明
5. 不涉及医疗建议，仅作知识普及

参考格式：[参考1]、[参考2] 等标注对应检索结果。"""
    
    def __init__(self, retriever: Retriever = None, api_key: str = None, api_base: str = None):
        self.retriever = retriever or Retriever()
        
        # Load from environment if not provided
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_base = api_base or os.environ.get(
            "OPENAI_API_BASE", "https://openrouter.ai/api/v1"
        )
        self.model = os.environ.get("LLM_MODEL", RAG_LLM_MODEL)
        
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=60.0,
            )
        else:
            self.client = None
        
        # Conversation history
        self.history: List[Dict[str, str]] = []
    
    def chat(
        self,
        question: str,
        course: Optional[str] = None,
        use_context: bool = True,
        stream: bool = False,
    ) -> Dict:
        """
        Chat with RAG
        
        Returns:
            {
                "answer": str,
                "sources": List[Dict],
                "context_used": bool,
            }
        """
        # Retrieve context
        context = ""
        sources = []
        
        if use_context:
            retrieval = self.retriever.retrieve_with_context(
                query=question,
                course=course,
            )
            context = retrieval["context"]
            sources = retrieval["sources"]
        
        # Build prompt
        if context:
            user_content = f"""问题：{question}

---
参考资料：
{context}
---

请基于以上参考资料回答。如果参考资料不足，请说明。"""
        else:
            user_content = question
        
        # Call LLM
        if self.client is None:
            return {
                "answer": "错误：未配置API密钥。请在.env中设置OPENAI_API_KEY",
                "sources": [],
                "context_used": False,
            }
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *self.history[-5:],  # Keep last 5 exchanges for context
            {"role": "user", "content": user_content},
        ]
        
        try:
            if stream:
                return self._stream_response(messages, sources, context)
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=RAG_TEMPERATURE,
                    max_tokens=RAG_MAX_TOKENS,
                )
                answer = response.choices[0].message.content
                
                # Update history
                self._update_history(question, answer)
                
                return {
                    "answer": answer,
                    "sources": sources,
                    "context_used": bool(context),
                }
        
        except Exception as e:
            return {
                "answer": f"生成回答时出错: {str(e)}",
                "sources": sources,
                "context_used": bool(context),
            }
    
    def _stream_response(
        self,
        messages: List[Dict],
        sources: List[Dict],
        context: str,
    ) -> Generator[str, None, None]:
        """Stream response chunks"""
        full_answer = []
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=RAG_TEMPERATURE,
                max_tokens=RAG_MAX_TOKENS,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_answer.append(content)
                    yield content
            
            # Update history after streaming
            answer = "".join(full_answer)
            self._update_history(messages[-1]["content"], answer)
            
        except Exception as e:
            yield f"\n[错误: {str(e)}]"
    
    def _update_history(self, question: str, answer: str):
        """Update conversation history"""
        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})
        
        # Limit history size
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def clear_history(self):
        """Clear conversation history"""
        self.history = []
    
    def quick_search(self, query: str) -> List[Dict]:
        """Quick search without generating answer"""
        return self.retriever.retrieve(query)
    
    def get_relevant_courses(self, question: str) -> List[str]:
        """Determine which courses are relevant to the question"""
        keywords_to_courses = {
            "辨证": ["中医辨证学"],
            "脏腑": ["中医辨证学", "中医初级入门"],
            "八纲": ["中医辨证学"],
            "经络": ["实用经络针灸学"],
            "穴位": ["实用经络针灸学"],
            "针灸": ["实用经络针灸学"],
            "方剂": ["方剂学"],
            "汤": ["方剂学"],
            "阴阳": ["中医初级入门"],
            "五行": ["中医初级入门"],
        }
        
        relevant = set()
        for keyword, courses in keywords_to_courses.items():
            if keyword in question:
                relevant.update(courses)
        
        return list(relevant)
