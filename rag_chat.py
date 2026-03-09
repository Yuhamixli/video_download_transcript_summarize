#!/usr/bin/env python3
"""
TCM RAG Chat - Interactive CLI for Chinese Medicine Knowledge QA

Usage:
    python rag_chat.py              # Start interactive chat
    python rag_chat.py --index    # Build/rebuild vector index
    python rag_chat.py --sync     # Sync knowledge base first
"""

import os
import sys
import argparse

# Load .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from rag import KnowledgeBase, Retriever, ChatEngine


def print_banner():
    print("=" * 60)
    print("  中医知识助手 (TCM Knowledge Assistant)")
    print("  基于 RAG 技术的智能问答系统")
    print("=" * 60)
    print()


def print_help():
    print("可用命令：")
    print("  /help      - 显示帮助")
    print("  /courses   - 列出可用课程")
    print("  /search <q> - 仅搜索，不生成回答")
    print("  /course <name> - 指定课程范围")
    print("  /clear     - 清空对话历史")
    print("  /quit      - 退出")
    print()


def build_index():
    """Build vector index from knowledge base"""
    print("正在构建向量索引...")
    
    retriever = Retriever()
    count = retriever.index_knowledge_base(chunk=True)
    
    print(f"\n索引完成！共索引 {count} 个文档块")
    return count


def sync_knowledge():
    """Sync knowledge from outlines and transcripts"""
    print("正在同步知识库...")
    
    kb = KnowledgeBase()
    stats = kb.sync_all()
    
    print(f"  大纲同步: {stats['outlines']} 个文件")
    print(f"  转录文本同步: {stats['transcripts']} 个文件")
    print(f"  总计: {stats['total']} 个文件")
    
    return stats['total']


def format_sources(sources):
    """Format source citations"""
    if not sources:
        return ""
    
    parts = ["\n参考资料："]
    for src in sources:
        parts.append(f"  [{src['rank']}] {src['source']} (相关度: {src['score']:.2f})")
    
    return "\n".join(parts)


def interactive_chat():
    """Main interactive chat loop"""
    print_banner()
    
    # Initialize
    try:
        chat_engine = ChatEngine()
        retriever = Retriever()
    except Exception as e:
        print(f"初始化失败: {e}")
        return 1
    
    # Check if index exists
    stats = retriever.vector_store.get_stats()
    if stats.get("count", 0) == 0:
        print("[WARN] 向量索引为空，请先运行: python rag_chat.py --index\n")
        print("或者继续，但搜索功能将不可用。")
        print()
    else:
        print(f"[OK] 向量索引已加载 ({stats['count']} 个文档块)\n")
    
    print_help()
    
    current_course = None
    
    while True:
        try:
            # Get user input
            prompt = f"[{current_course}] " if current_course else ""
            user_input = input(f"{prompt}> ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input[1:].split()[0].lower()
                args = user_input[len(cmd)+2:].strip()
                
                if cmd in ("quit", "exit", "q"):
                    print("再见!")
                    break
                
                elif cmd == "help":
                    print_help()
                
                elif cmd == "clear":
                    chat_engine.clear_history()
                    print("对话历史已清空。\n")
                
                elif cmd == "courses":
                    kb = KnowledgeBase()
                    stats = kb.get_stats()
                    print(f"\n可用课程:")
                    print(f"  - 中医辨证学")
                    print(f"  - 实用经络针灸学")
                    print(f"  - 方剂学")
                    print(f"  - 中医初级入门")
                    print(f"\n知识库统计:")
                    print(f"  大纲: {stats['outlines']} 个")
                    print(f"  转录文本: {stats['transcripts']} 个")
                    print()
                
                elif cmd == "course":
                    if args:
                        current_course = args
                        print(f"已设置课程范围: {current_course}\n")
                    else:
                        current_course = None
                        print("已清除课程范围限制\n")
                
                elif cmd == "search":
                    if not args:
                        print("用法: /search <查询内容>\n")
                        continue
                    
                    results = chat_engine.quick_search(args)
                    print(f"\n搜索: {args}")
                    print(f"找到 {len(results)} 个相关结果:\n")
                    
                    for i, r in enumerate(results[:5], 1):
                        meta = r['metadata']
                        print(f"[{i}] {meta.get('course', 'Unknown')} - {meta.get('filename', 'Unknown')}")
                        print(f"    相关度: {r['score']:.3f}")
                        preview = r['content'][:150].replace('\n', ' ')
                        print(f"    {preview}...\n")
                
                else:
                    print(f"未知命令: /{cmd}")
                    print_help()
                
                continue
            
            # Regular chat
            print("思考中...", end="\r")
            
            response = chat_engine.chat(
                question=user_input,
                course=current_course,
            )
            
            # Clear thinking message
            print(" " * 20, end="\r")
            
            # Print answer
            print(f"\n回答:")
            print(response["answer"])
            
            # Print sources
            if response["sources"]:
                print(format_sources(response["sources"]))
            
            print()
        
        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"\n错误: {e}\n")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="TCM RAG Chat")
    parser.add_argument("--index", action="store_true", help="Build vector index")
    parser.add_argument("--sync", action="store_true", help="Sync knowledge base")
    parser.add_argument("--query", "-q", help="Single query mode")
    parser.add_argument("--course", "-c", help="Specify course scope")
    
    args = parser.parse_args()
    
    if args.sync:
        sync_knowledge()
        print()
    
    if args.index:
        build_index()
        return 0
    
    if args.query:
        # Single query mode
        chat_engine = ChatEngine()
        response = chat_engine.chat(
            question=args.query,
            course=args.course,
        )
        print(response["answer"])
        if response["sources"]:
            print(format_sources(response["sources"]))
        return 0
    
    # Interactive mode
    return interactive_chat()


if __name__ == "__main__":
    sys.exit(main())
