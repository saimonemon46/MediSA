# MediAI — LLM Client
# Wraps Groq and Gemini APIs for LLM calls

import os
import json
import re
try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env
except ImportError:
    load_dotenv = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "openai/gpt-oss-120b"   # Groq's fast 70B model
GEMINI_MODEL = "gemini-1.5-flash"

_groq_client = None
_gemini_client = None


def get_groq_client():
    global _groq_client
    if Groq is None:
        raise RuntimeError("The 'groq' package is not installed. Install with: pip install groq")
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def get_gemini_client():
    global _gemini_client
    if genai is None:
        raise RuntimeError("The 'google-generativeai' package is not installed. Install with: pip install google-generativeai")
    if _gemini_client is None:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_client = genai.GenerativeModel(GEMINI_MODEL)
    return _gemini_client


def chat(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Single-turn chat with LLM. Tries Groq (primary + fallback models), then Gemini."""
    try:
        client = get_groq_client()
        # Primary attempt with configured model
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        content = (response.choices[0].message.content or "").strip()
        if content:
            return content

        # If primary returned empty content (e.g. reasoning model token exhaustion), try qwen on Groq
        response2 = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        content2 = (response2.choices[0].message.content or "").strip()
        if content2:
            return content2
    except Exception as e:
        print(f"Groq API Error: {e}")
        # Try qwen fallback on Groq if first model failed with exception
        try:
            client = get_groq_client()
            res_alt = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            content_alt = (res_alt.choices[0].message.content or "").strip()
            if content_alt:
                return content_alt
        except Exception:
            pass

        if GEMINI_API_KEY:
            try:
                client = get_gemini_client()
                prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
                response = client.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens, temperature=0.3))
                return response.text.strip()
            except Exception as e2:
                print(f"Gemini API Error: {e2}")

        return "I understand your reported symptoms. Based on clinical triage guidelines, please monitor your symptoms closely, ensure adequate hydration and rest, and consult a qualified medical professional if symptoms persist or worsen."


def chat_json(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> dict:
    """Chat and parse JSON response. Falls back to empty dict on parse failure."""
    raw = chat(system_prompt, user_prompt + "\n\nRespond ONLY with valid JSON. No markdown, no backticks.", max_tokens)
    # Strip possible ```json fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract the first JSON object/array
        match = re.search(r'(\{.*\}|\[.*\])', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return {}
