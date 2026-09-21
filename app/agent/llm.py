"""
Provider-agnostic LLM call layer: Groq primary, Gemini fallback, with
retry/backoff on transient errors.
"""
import time
from app.config import config


def _call_groq(messages: list[dict], system_prompt: str) -> str:
    from groq import Groq

    config.require_runtime("groq_api_key")
    # max_retries=0: our own call_llm loop already retries/falls back, so we
    # don't want the SDK's built-in retry-after-429 backoff (which can wait
    # tens of seconds per attempt) stacking on top of ours.
    client = Groq(api_key=config.groq_api_key, max_retries=0)
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    resp = client.chat.completions.create(
        model=config.primary_model,
        messages=full_messages,
        temperature=0.2,
    )
    return resp.choices[0].message.content


def _call_gemini(messages: list[dict], system_prompt: str) -> str:
    import google.generativeai as genai

    config.require_runtime("gemini_api_key")
    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel(config.fallback_model, system_instruction=system_prompt)

    # Gemini wants a flat conversation; fold role history into simple text turns.
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages[:-1])
    last_user = messages[-1]["content"] if messages else ""
    prompt = f"{history_text}\nuser: {last_user}" if history_text else last_user

    resp = model.generate_content(prompt)
    return resp.text


def _is_rate_limit_error(e: Exception) -> bool:
    return "429" in str(e) or "rate" in str(e).lower() or "quota" in str(e).lower()


def call_llm(messages: list[dict], system_prompt: str, max_retries: int = 2) -> str:
    """
    messages: list of {"role": "user"|"assistant", "content": str}
    Tries Groq first; falls back to Gemini on any error. Retries each
    provider with exponential backoff before giving up on it — except on a
    rate-limit error, where retrying the same provider is futile, so we jump
    straight to the fallback provider instead.
    """
    last_error = None

    for provider_fn, provider_name in [(_call_groq, "groq"), (_call_gemini, "gemini")]:
        for attempt in range(max_retries + 1):
            try:
                return provider_fn(messages, system_prompt)
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e):
                    break  # don't retry a rate-limited provider, fall back immediately
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    break  # move on to next provider

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
