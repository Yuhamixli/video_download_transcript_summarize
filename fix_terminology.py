"""
中医术语纠错: 使用大模型对 ASR 转录文本进行术语后处理纠错
支持: OpenAI API / MiniMax / DeepSeek / 任何兼容 API
"""

import os
import sys
import json
import glob
import time
import argparse
import logging
import traceback
from datetime import datetime
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ============ 配置 ============
TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), "transcripts")
CORRECTED_DIR = os.path.join(os.path.dirname(__file__), "transcripts_corrected")
os.makedirs(CORRECTED_DIR, exist_ok=True)

# API 配置 (支持环境变量 & .env)
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

API_KEY = os.environ.get("OPENAI_API_KEY", "")
API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.minimax.io/v1")
MODEL = os.environ.get("LLM_MODEL", "MiniMax-M2.5")

MANUAL_CORRECTIONS_PATH = os.path.join(os.path.dirname(__file__), "manual_corrections.json")


def load_manual_corrections():
    """加载手动纠错学习表，构建额外的提示词片段"""
    if not os.path.exists(MANUAL_CORRECTIONS_PATH):
        return ""

    with open(MANUAL_CORRECTIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("corrections", [])
    if not items:
        return ""

    lines = []
    for item in items:
        wrong = item["wrong"]
        correct = item["correct"]
        ctx = item.get("context", "")
        note = item.get("note", "")
        entry = f"{wrong} → {correct}"
        if ctx:
            entry += f" [{ctx}]"
        if note:
            entry += f" ({note})"
        lines.append(entry)

    return "\n【已确认的纠错规则 — 来自人工审核，必须遵守】\n" + "\n".join(lines)


def save_new_corrections(all_results):
    """将本轮 LLM 发现的新纠错规则合并到手动纠错表（去重），方便人工审核"""
    if not os.path.exists(MANUAL_CORRECTIONS_PATH):
        return

    with open(MANUAL_CORRECTIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing = {(c["wrong"], c["correct"]) for c in data.get("corrections", [])}
    new_count = 0

    for r in all_results:
        if r.get("status") != "success":
            continue
        for c_line in r.get("corrections", []):
            parts = c_line.split("→", 1)
            if len(parts) != 2:
                parts = c_line.split("->", 1)
            if len(parts) != 2:
                continue
            strip_chars = '」「""\uff09\uff08\u300d\u300c'
            wrong = parts[0].strip().strip(strip_chars)
            rest = parts[1].strip()
            correct = rest.split("(")[0].split("\uff08")[0].strip().strip(strip_chars)
            if (wrong, correct) not in existing and wrong != correct and len(wrong) <= 10:
                data["corrections"].append({
                    "wrong": wrong,
                    "correct": correct,
                    "note": "LLM 自动发现，待人工审核",
                })
                existing.add((wrong, correct))
                new_count += 1

    if new_count > 0:
        with open(MANUAL_CORRECTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"已将 {new_count} 条新纠错规则合并到 manual_corrections.json (待人工审核)")


# ============ 中医术语词典 ============
TCM_DICTIONARY = """
【脏腑】心、肝、脾、肺、肾（五脏）；胆、胃、小肠、大肠、膀胱、三焦（六腑）；心包

【经络】十二经脉：手太阴肺经、手阳明大肠经、足阳明胃经、足太阴脾经、手少阴心经、手太阳小肠经、
足太阳膀胱经、足少阴肾经、手厥阴心包经、手少阳三焦经、足少阳胆经、足厥阴肝经
奇经八脉：任脉、督脉、冲脉、带脉、阴维脉、阳维脉、阴跷脉、阳跷脉

【穴位】百会、太阳、印堂、迎香、合谷、曲池、肩井、风池、大椎、命门、关元、气海、中脘、
足三里、三阴交、太冲、太溪、涌泉、内关、外关、神门、血海、阳陵泉、阴陵泉、
委中、昆仑、悬钟（绝骨）、列缺、尺泽、少商、商阳、中府、天突、膻中、期门、章门

【诊法】望诊、闻诊、问诊、切诊（望闻问切/四诊）
脉诊：寸关尺、浮沉迟数、滑涩弦紧、洪细虚实、促结代、濡弱芤革
舌诊：舌质、舌苔、舌体、舌下络脉；淡红舌、红舌、绛舌、青紫舌；
薄白苔、白腻苔、黄苔、黄腻苔、灰黑苔、剥苔、花剥苔
按诊：腹诊

【病因】六淫：风、寒、暑、湿、燥、火
七情：喜、怒、忧、思、悲、恐、惊
其他：痰饮、瘀血、食积、劳逸

【辨证体系】
八纲辨证：阴阳、表里、寒热、虚实
六经辨证：太阳病、阳明病、少阳病、太阴病、少阴病、厥阴病
卫气营血辨证：卫分证、气分证、营分证、血分证
三焦辨证：上焦、中焦、下焦
脏腑辨证：肝气郁结、肝火上炎、肝阳上亢、肝风内动、肝血虚、肝阴虚；
心气虚、心阳虚、心血虚、心阴虚、心火亢盛；
脾气虚、脾阳虚、脾不统血、脾虚湿困；
肺气虚、肺阴虚、风寒犯肺、风热犯肺、痰湿蕴肺；
肾阳虚、肾阴虚、肾精不足、肾气不固、肾不纳气

【治法】汗法、吐法、下法、和法、温法、清法、消法、补法（八法）
扶正祛邪、标本兼治、急则治标、缓则治本

【方剂】
解表剂：麻黄汤、桂枝汤、银翘散、桑菊饮、小青龙汤、九味羌活汤
泻下剂：大承气汤、小承气汤、调胃承气汤、麻子仁丸
和解剂：小柴胡汤、大柴胡汤、逍遥散、四逆散
清热剂：白虎汤、清营汤、黄连解毒汤、龙胆泻肝汤、犀角地黄汤
温里剂：四逆汤、理中汤（丸）、小建中汤、当归四逆汤、吴茱萸汤
补益剂：四君子汤、六君子汤、补中益气汤、四物汤、归脾汤、六味地黄丸、肾气丸（金匮肾气丸）
固涩剂：牡蛎散、金锁固精丸
安神剂：天王补心丹、酸枣仁汤
理气剂：半夏厚朴汤、苏子降气汤
理血剂：桃核承气汤、血府逐瘀汤、补阳还五汤
祛湿剂：平胃散、藿香正气散、茵陈蒿汤、五苓散
祛痰剂：二陈汤、温胆汤
治风剂：川芎茶调散、镇肝熄风汤

【基础理论】
阴阳：阴阳互根、阴阳消长、阴阳转化、阴阳平衡
五行：木火土金水；相生相克、相乘相侮
精气血津液：精、气、血、津液；元气、宗气、营气、卫气
气机：升降出入
气血关系：气为血之帅、血为气之母
津液：津（清稀）、液（稠厚）

【台湾口音常见同音误识 - 单字】
虚 ≠ 须/需；血 ≠ 薛/雪；穴 ≠ 学；脉 ≠ 卖/麦；
实 ≠ 室/时/识；气 ≠ 器/起；阴 ≠ 音/因；阳 ≠ 洋/样；
腑 ≠ 府/付；络 ≠ 落/洛；津 ≠ 金/精；液 ≠ 业/夜；
泻 ≠ 写/谢；痰 ≠ 谈/弹；瘀 ≠ 于/淤；郁 ≠ 玉/育

【台湾口音常见同音误识 - 多字/整词】
方剂 ≠ 方计/方记/方济；经络 ≠ 经落/精落；
寸关尺 ≠ 寸官词/寸官次；辨证 ≠ 辩证/变证；
脏腑 ≠ 藏腑/脏府；津液 ≠ 金液/精液；
狭义 ≠ 达意/下意/夏意/想；广义 ≠ 光义/管义；
辨证论治 ≠ 变证论治；扶正祛邪 ≠ 扶正去邪；
标本兼治 ≠ 标本间治
"""

SYSTEM_PROMPT = f"""你是一位资深中医学文献校对专家，精通中医基础理论、方剂学、针灸学等各科。

你的任务是校对 ASR 语音识别转录文本中的中医术语错误。这些转录来自一位台湾口音讲师的中医入门课程。

## 校对规则
1. **只修正术语错误和语音识别错误**，不要改变原文的口语风格和表达方式
2. **保留原文结构**，不要增删内容，不要重新组织语句
3. **专注中医术语**：脏腑、经络、穴位、方剂、病证、诊法、治法等
4. **同音字纠正**：台湾口音导致的同音字误识是最常见的错误类型（单字或多字）
5. **上下文推断**：ASR 可能将一个词完全识别错（如"狭义"→"达意"、"狭义"→"想"），需根据上下文语义推断正确用词
6. **语义连贯性**：如果一句话读起来不通顺或与上下文矛盾，很可能是 ASR 错误，需纠正
7. **非中医语境的普通用词**如果明显是同音误识也要纠正（如"达意"→"狭义"）
8. **存疑不改**：如果不确定是否为错误，保持原文不变

## 中医术语参考词典
{TCM_DICTIONARY}

## 输出格式
请直接输出校对后的完整文本。在文本末尾，用 "---CORRECTIONS---" 分隔，列出所有修改，格式：
原文 → 修正 (原因)

如果没有需要修改的地方，直接输出原文并在末尾注明 "---CORRECTIONS---\n无需修改"。"""


def build_system_prompt():
    """构建系统提示词，包含手动纠错学习表"""
    manual_section = load_manual_corrections()
    return SYSTEM_PROMPT + manual_section


def correct_transcript(client, text, title, model, system_prompt):
    """调用 LLM 纠错单篇转录"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"课程标题: {title}\n\n以下是 ASR 转录文本，请校对中医术语:\n\n{text}"},
        ],
        temperature=0.1,
        max_tokens=len(text) * 3 + 500,
    )
    return response.choices[0].message.content


def parse_correction_result(result):
    """解析 LLM 返回的纠错结果"""
    if "---CORRECTIONS---" in result:
        parts = result.split("---CORRECTIONS---", 1)
        corrected_text = parts[0].strip()
        corrections_text = parts[1].strip()
    else:
        corrected_text = result.strip()
        corrections_text = ""

    corrections = []
    if corrections_text and corrections_text != "无需修改":
        for line in corrections_text.strip().split("\n"):
            line = line.strip()
            if line and ("→" in line or "->" in line):
                corrections.append(line)

    return corrected_text, corrections


def process_transcript(client, txt_path, model, system_prompt, force=False):
    """处理单个转录文件"""
    name = os.path.splitext(os.path.basename(txt_path))[0]
    output_path = os.path.join(CORRECTED_DIR, f"{name}.txt")

    if not force and os.path.exists(output_path) and os.path.getsize(output_path) > 10:
        return {"file": name, "status": "skipped"}

    with open(txt_path, "r", encoding="utf-8") as f:
        original_text = f.read()

    if not original_text.strip() or len(original_text) < 20:
        return {"file": name, "status": "skipped", "reason": "too short"}

    t0 = time.time()
    raw_result = correct_transcript(client, original_text, name, model, system_prompt)
    elapsed = time.time() - t0

    corrected_text, corrections = parse_correction_result(raw_result)

    # 保存纠错后文本
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(corrected_text)

    # 更新 _detail.json（如有）
    detail_src = txt_path.replace(".txt", "_detail.json")
    if os.path.exists(detail_src):
        detail_dst = os.path.join(CORRECTED_DIR, f"{name}_detail.json")
        with open(detail_src, "r", encoding="utf-8") as f:
            detail = json.load(f)
        detail["text"] = corrected_text
        detail["corrections"] = corrections
        detail["correction_model"] = model
        with open(detail_dst, "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)

    log.info(
        f"  完成! {elapsed:.1f}秒, {len(corrections)}处修改, "
        f"{len(original_text)}→{len(corrected_text)}字"
    )

    return {
        "file": name,
        "status": "success",
        "time": round(elapsed, 1),
        "original_chars": len(original_text),
        "corrected_chars": len(corrected_text),
        "num_corrections": len(corrections),
        "corrections": corrections,
    }


def main():
    parser = argparse.ArgumentParser(description="中医术语纠错 (LLM 后处理)")
    parser.add_argument("--model", default=MODEL, help=f"LLM 模型 (默认: {MODEL})")
    parser.add_argument("--api-key", default=API_KEY, help="API Key")
    parser.add_argument("--api-base", default=API_BASE, help=f"API Base URL (默认: {API_BASE})")
    parser.add_argument("--force", action="store_true", help="强制重新处理已存在的文件")
    parser.add_argument("--file", help="只处理指定文件 (文件名关键字)")
    parser.add_argument("--limit", type=int, help="限制处理数量 (用于测试)")
    args = parser.parse_args()

    api_key = args.api_key
    if not api_key:
        print("错误: 请设置 OPENAI_API_KEY 环境变量或通过 --api-key 参数提供 API Key")
        print("  方式1: 创建 .env 文件，写入 OPENAI_API_KEY=your-key")
        print("  方式2: $env:OPENAI_API_KEY='your-key'")
        sys.exit(1)

    print("=" * 60)
    print(" 中医术语纠错 - LLM 后处理")
    print(f" 模型: {args.model}")
    print(f" API: {args.api_base}")
    print(f" 输出: {CORRECTED_DIR}")
    print("=" * 60)

    client = OpenAI(api_key=api_key, base_url=args.api_base, timeout=120.0, max_retries=5)
    system_prompt = build_system_prompt()
    manual_count = len(json.load(open(MANUAL_CORRECTIONS_PATH, encoding="utf-8")).get("corrections", [])) if os.path.exists(MANUAL_CORRECTIONS_PATH) else 0
    print(f" 已加载 {manual_count} 条手动纠错规则")

    # 获取转录文件列表
    if args.file:
        pattern = os.path.join(TRANSCRIPT_DIR, f"*{args.file}*.txt")
        transcripts = sorted(glob.glob(pattern))
    else:
        transcripts = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.txt")))

    if args.limit:
        transcripts = transcripts[:args.limit]

    if not transcripts:
        print(f"\n没有找到转录文件: {TRANSCRIPT_DIR}")
        return

    print(f"\n共 {len(transcripts)} 个转录文件待处理")

    results = []
    success = 0
    skip = 0
    errors = 0
    failed_files = []
    total_corrections = 0
    total_start = time.time()

    for i, txt_path in enumerate(transcripts):
        name = os.path.splitext(os.path.basename(txt_path))[0]
        log.info(f"[{i+1}/{len(transcripts)}] {name}")

        try:
            result = process_transcript(client, txt_path, args.model, system_prompt, args.force)
            results.append(result)
            if result["status"] == "success":
                success += 1
                total_corrections += result["num_corrections"]
            else:
                skip += 1
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            log.error(f"  失败: {err_msg}")
            log.debug(traceback.format_exc())
            errors += 1
            failed_files.append({"file": name, "error": err_msg})
            results.append({"file": name, "status": "failed", "error": err_msg})

    total_elapsed = time.time() - total_start

    # 将 LLM 发现的新纠错规则合并到手动纠错表
    save_new_corrections(results)

    # 保存纠错报告
    report_path = os.path.join(os.path.dirname(__file__), "fix_terminology_report.json")
    report = {
        "run_time": datetime.now().isoformat(),
        "model": args.model,
        "api_base": args.api_base,
        "total_files": len(transcripts),
        "success": success,
        "skipped": skip,
        "failed": errors,
        "total_corrections": total_corrections,
        "total_seconds": round(total_elapsed, 1),
        "failed_files": failed_files,
        "results": results,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f" 纠错完成! 总耗时: {total_elapsed:.0f}秒")
    print(f"   成功: {success}")
    print(f"   跳过: {skip}")
    print(f"   失败: {errors}")
    print(f"   总修改: {total_corrections} 处")
    if failed_files:
        print(f"\n   失败文件:")
        for f_item in failed_files:
            print(f"      - {f_item['file']}: {f_item['error']}")
    print(f"\n   报告: {report_path}")
    print(f"   输出: {CORRECTED_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
