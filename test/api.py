"""
API 连接测试脚本
"""
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
import os

# 加载 .env
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", ""),
)


def stream_chat():
    print("发送测试请求...")
    stream = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o"),
        messages=[
            {"role": "user", "content": "你是谁"}
        ],
        stream=True,
    )
    print("AI: ", end="")
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    stream_chat()
