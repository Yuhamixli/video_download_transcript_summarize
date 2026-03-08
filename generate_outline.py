"""
大纲生成: 使用大模型将讲义整理为结构化大纲
支持: OpenAI API / 本地模型 / 任何兼容 API
优先使用纠错后的转录文本 (transcripts_corrected/)
"""

import os
import json
import glob
from openai import OpenAI

# ============ .env 加载 ============
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

# ============ 配置 ============
CORRECTED_DIR = os.path.join(os.path.dirname(__file__), "transcripts_corrected")
TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), "transcripts")
OUTLINE_DIR = os.path.join(os.path.dirname(__file__), "outlines")
os.makedirs(OUTLINE_DIR, exist_ok=True)

API_KEY = os.environ.get("OPENAI_API_KEY", "")
API_BASE = os.environ.get("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
MODEL = os.environ.get("LLM_MODEL", "minimax/minimax-m2.5")

SYSTEM_PROMPT = """你是一位专业的中医学讲义整理专家。请根据以下视频课程的文字转录内容，整理为结构化的大纲讲义。

要求：
1. 提取核心知识点，去除口语化表达和冗余
2. 使用 Markdown 格式，层次清晰
3. 保留专业术语的准确性
4. 标注重点和难点
5. 如有涉及临床实例，单独整理

输出格式：
# 课程标题
## 一、主要概念
### 1. xxx
- 要点1
- 要点2
## 二、详细内容
...
## 三、重点总结
...
"""


def generate_outline(client, transcript_text, title):
    """使用大模型生成大纲"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"课程标题: {title}\n\n转录内容:\n{transcript_text}"},
        ],
        temperature=0.3,
        max_tokens=4000,
    )
    return response.choices[0].message.content


def generate_full_outline(client, all_transcripts):
    """生成完整课程大纲 (汇总)"""
    summary_prompt = """你是一位中医学教授。以下是一整套中医入门课程(108集)的各集讲义大纲。
请将它们整合为一份完整的课程知识体系大纲。

要求：
1. 按中医学体系重新组织（阴阳、五行、脏腑、经络、诊断等）
2. 标注各知识点对应的课程编号
3. 建立知识点间的逻辑关系
4. 输出为完整的 Markdown 文档

"""
    # 合并所有大纲
    combined = "\n\n---\n\n".join(
        f"### {name}\n{outline}"
        for name, outline in all_transcripts
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": combined[:30000]},  # 限制长度
        ],
        temperature=0.3,
        max_tokens=8000,
    )
    return response.choices[0].message.content


def _relpath_from_base(path, base):
    """Get relative path from base, used as key for dedup."""
    abs_path = os.path.abspath(path)
    base_abs = os.path.abspath(base)
    if abs_path.startswith(base_abs):
        return os.path.relpath(abs_path, base_abs)
    return path


def get_transcript_files():
    """获取转录文件列表，优先使用纠错后版本。支持子目录结构。"""
    corrected = {}
    original = {}

    for t in sorted(glob.glob(os.path.join(CORRECTED_DIR, "*.txt"))):
        rel = _relpath_from_base(t, CORRECTED_DIR)
        key = rel.replace("\\", "/")
        corrected[key] = t
    for t in sorted(glob.glob(os.path.join(CORRECTED_DIR, "*", "*.txt"))):
        rel = _relpath_from_base(t, CORRECTED_DIR)
        key = rel.replace("\\", "/")
        corrected[key] = t

    for t in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt"))):
        rel = _relpath_from_base(t, TRANSCRIPT_DIR)
        key = rel.replace("\\", "/")
        original[key] = t
    for t in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*", "*.txt"))):
        rel = _relpath_from_base(t, TRANSCRIPT_DIR)
        key = rel.replace("\\", "/")
        original[key] = t

    result = []
    all_keys = sorted(set(list(corrected.keys()) + list(original.keys())))
    corrected_count = 0
    for key in all_keys:
        if key in corrected:
            result.append((key, corrected[key]))
            corrected_count += 1
        elif key in original:
            result.append((key, original[key]))

    return result, corrected_count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="大模型大纲生成")
    parser.add_argument("--force", action="store_true", help="强制重新生成已存在的大纲")
    parser.add_argument("--file", help="只处理指定文件 (文件名关键字)")
    parser.add_argument("--no-summary", action="store_true", help="不生成完整课程汇总大纲")
    args = parser.parse_args()

    if not API_KEY:
        print("错误: 请设置 OPENAI_API_KEY (在 .env 文件中)")
        return

    print("=" * 60)
    print(" 大模型大纲生成")
    print(f" 模型: {MODEL}")
    print(f" API: {API_BASE}")
    print("=" * 60)

    client = OpenAI(api_key=API_KEY, base_url=API_BASE, timeout=120.0, max_retries=5)

    transcripts, corrected_count = get_transcript_files()
    if args.file:
        transcripts = [(n, p) for n, p in transcripts if args.file in n]

    if not transcripts:
        print(f"\n没有找到转录文件")
        print("请先运行 transcribe.py 和 fix_terminology.py")
        return

    print(f"\n共 {len(transcripts)} 个转录文件 (其中 {corrected_count} 个为纠错版)")

    all_outlines = []
    success = 0
    errors = 0
    failed_files = []

    for i, (key, txt_path) in enumerate(transcripts):
        name = os.path.splitext(os.path.basename(key))[0]
        outline_path = os.path.join(OUTLINE_DIR, os.path.splitext(key)[0] + ".md")
        os.makedirs(os.path.dirname(outline_path), exist_ok=True)

        if not args.force and os.path.exists(outline_path) and os.path.getsize(outline_path) > 10:
            print(f"[{i+1}/{len(transcripts)}] 跳过: {key}")
            with open(outline_path, "r", encoding="utf-8") as f:
                all_outlines.append((key, f.read()))
            continue

        print(f"[{i+1}/{len(transcripts)}] 生成大纲: {key}")

        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip() or len(text) < 20:
            print(f"  [SKIP] 内容过短")
            continue

        try:
            outline = generate_outline(client, text, name)
            with open(outline_path, "w", encoding="utf-8") as f:
                f.write(outline)
            all_outlines.append((key, outline))
            success += 1
            print(f"  [OK] {len(outline)} 字")
        except Exception as e:
            print(f"  [ERROR] {e}")
            errors += 1
            failed_files.append(key)

    # 生成完整课程大纲
    if not args.no_summary and all_outlines and len(all_outlines) >= 5:
        print(f"\n生成完整课程知识体系大纲...")
        try:
            full_outline = generate_full_outline(client, all_outlines)
            full_path = os.path.join(OUTLINE_DIR, "00_完整课程大纲.md")
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(full_outline)
            print(f"  [OK] 保存到: {full_path}")
        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\n{'=' * 60}")
    print(f" 大纲生成完成!")
    print(f"   成功: {success}")
    print(f"   失败: {errors}")
    if failed_files:
        print(f"   失败列表: {', '.join(failed_files[:10])}")
    print(f"   输出: {OUTLINE_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
