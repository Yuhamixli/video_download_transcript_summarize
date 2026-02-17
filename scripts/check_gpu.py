"""检查 GPU 和 CUDA 环境状态"""

import sys

print("=" * 50)
print(" GPU / CUDA 环境检查")
print("=" * 50)

# PyTorch CUDA 检查
try:
    import torch
    print(f"\n[PyTorch]")
    print(f"  版本: {torch.__version__}")
    print(f"  CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA 版本: {torch.version.cuda}")
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"    VRAM: {props.total_memory / 1024**3:.1f} GB")
            print(f"    计算能力: {props.major}.{props.minor}")
except ImportError:
    print("\n[PyTorch] 未安装")

# CTranslate2 (faster-whisper 后端) CUDA 检查
try:
    import ctranslate2
    print(f"\n[CTranslate2]")
    print(f"  版本: {ctranslate2.__version__}")
    try:
        cuda_types = ctranslate2.get_supported_compute_types("cuda")
        print(f"  CUDA 计算类型: {cuda_types}")
    except Exception:
        print(f"  CUDA: 不可用")
    cpu_types = ctranslate2.get_supported_compute_types("cpu")
    print(f"  CPU 计算类型: {cpu_types}")
except ImportError:
    print("\n[CTranslate2] 未安装")

# faster-whisper 检查
try:
    import faster_whisper
    print(f"\n[faster-whisper]")
    print(f"  版本: {faster_whisper.__version__}")
except ImportError:
    print("\n[faster-whisper] 未安装")

# VRAM 使用情况
try:
    import torch
    if torch.cuda.is_available():
        print(f"\n[VRAM 使用]")
        allocated = torch.cuda.memory_allocated(0) / 1024**2
        reserved = torch.cuda.memory_reserved(0) / 1024**2
        total = torch.cuda.get_device_properties(0).total_memory / 1024**2
        print(f"  已分配: {allocated:.0f} MB")
        print(f"  已保留: {reserved:.0f} MB")
        print(f"  总容量: {total:.0f} MB")
        print(f"  可用: ~{total - reserved:.0f} MB")
except Exception:
    pass

print(f"\n{'=' * 50}")
print(" 推荐配置:")
try:
    import torch
    if torch.cuda.is_available():
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        if vram >= 8:
            print(f"  模型: large-v3, 精度: float16")
        elif vram >= 4:
            print(f"  模型: large-v3, 精度: float16 或 int8")
        elif vram >= 2:
            print(f"  模型: medium, 精度: int8")
        else:
            print(f"  模型: small, 精度: int8")
    else:
        print(f"  模型: small, 精度: float32 (CPU)")
except Exception:
    print(f"  无法检测 GPU，建议使用 CPU 模式")
print(f"{'=' * 50}")
