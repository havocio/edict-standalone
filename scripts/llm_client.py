"""
LLM 客户端 — 统一封装 OpenAI / Anthropic / DeepSeek / Ollama
根据 .env 中的 LLM_PROVIDER 自动路由
"""
import os
from pathlib import Path
from typing import Optional

# 加载 .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)

PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
MODEL    = os.getenv("LLM_MODEL", "gpt-4o")
API_KEY  = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "")

# 使用统一日志模块
from logger import logger
logger.debug(f"✓ LLM 客户端初始化: provider={PROVIDER}, model={MODEL}")


def chat(system_prompt: str, messages: list[dict],
         max_tokens: int = 4096, temperature: float = 0.3) -> tuple[str, int]:
    """
    发送对话请求，返回 (content, total_tokens)
    messages 格式: [{"role": "user"|"assistant", "content": "..."}]
    """
    logger.debug(f"[LLM] chat() 被调用: provider={PROVIDER}, model={MODEL}")
    logger.debug(f"[LLM] chat() 输入: system_prompt_len={len(system_prompt)}, messages_count={len(messages)}")

    try:
        if PROVIDER in ("openai", "deepseek"):
            result = _openai_chat(system_prompt, messages, max_tokens, temperature)
        elif PROVIDER == "anthropic":
            result = _anthropic_chat(system_prompt, messages, max_tokens, temperature)
        elif PROVIDER == "ollama":
            result = _ollama_chat(system_prompt, messages, max_tokens, temperature)
        else:
            raise ValueError(f"不支持的 LLM_PROVIDER: {PROVIDER}")

        logger.debug(f"[LLM] chat() 返回: content_len={len(result[0])}, tokens={result[1]}")
        return result
    except Exception as e:
        logger.error(f"[LLM] chat() 异常: {type(e).__name__}: {e}")
        raise


# ── OpenAI / DeepSeek / 兼容接口 ─────────────────────────────────────────────
def _openai_chat(system_prompt, messages, max_tokens, temperature):
    from openai import OpenAI
    kwargs = {"api_key": API_KEY or "ollama"}
    if BASE_URL:
        kwargs["base_url"] = BASE_URL
    elif PROVIDER == "deepseek":
        kwargs["base_url"] = "https://api.deepseek.com"

    client = OpenAI(**kwargs)
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    # Debug 级别打印请求详情
    logger.debug(f"[LLM OpenAI 请求] model={MODEL}, base_url={BASE_URL or '(default)'}")
    logger.debug(f"[LLM OpenAI 请求] system_prompt: {system_prompt[:200]}...")
    logger.debug(f"[LLM OpenAI 请求] messages: {messages}")

    resp = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = resp.choices[0].message.content or ""
    tokens  = resp.usage.total_tokens if resp.usage else 0

    logger.debug(f"[LLM OpenAI 响应] tokens={tokens}, content_len={len(content)}, content: {content[:200]}...")
    return content, tokens


# ── Anthropic ────────────────────────────────────────────────────────────────
def _anthropic_chat(system_prompt, messages, max_tokens, temperature):
    import anthropic

    logger.debug(f"[LLM Anthropic 请求] model={MODEL}")
    logger.debug(f"[LLM Anthropic 请求] system_prompt: {system_prompt[:200]}...")
    logger.debug(f"[LLM Anthropic 请求] messages: {messages}")

    client = anthropic.Anthropic(api_key=API_KEY)
    resp = client.messages.create(
        model=MODEL,
        system=system_prompt,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    content = resp.content[0].text if resp.content else ""
    tokens  = (resp.usage.input_tokens or 0) + (resp.usage.output_tokens or 0)

    logger.debug(f"[LLM Anthropic 响应] tokens={tokens}, content_len={len(content)}, content: {content[:200]}...")
    return content, tokens


# ── Ollama（本地，无需 API Key）──────────────────────────────────────────────
def _ollama_chat(system_prompt, messages, max_tokens, temperature):
    import httpx, json
    base = BASE_URL or "http://localhost:11434"
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    payload = {
        "model": MODEL,
        "messages": full_messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }

    logger.debug(f"[LLM Ollama 请求] model={MODEL}, base={base}")
    logger.debug(f"[LLM Ollama 请求] system_prompt: {system_prompt[:200]}...")
    logger.debug(f"[LLM Ollama 请求] messages: {messages}")

    r = httpx.post(f"{base}/api/chat", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    content = data.get("message", {}).get("content", "")
    tokens  = data.get("eval_count", 0)

    logger.debug(f"[LLM Ollama 响应] tokens={tokens}, content_len={len(content)}, content: {content[:200]}...")
    return content, tokens
