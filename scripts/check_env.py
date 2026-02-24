"""检查 LLM API 环境变量配置"""
import os

key = os.environ.get("OPENAI_API_KEY", "")
base = os.environ.get("OPENAI_API_BASE", "")
model = os.environ.get("LLM_MODEL", "")

if key and key != "your-api-key-here":
    print(f"OPENAI_API_KEY: set ({key[:8]}...)")
else:
    print("OPENAI_API_KEY: NOT SET")

print(f"OPENAI_API_BASE: {base or 'NOT SET (default: openai)'}")
print(f"LLM_MODEL: {model or 'NOT SET (default: gpt-4o-mini)'}")
