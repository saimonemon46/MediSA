# MediAI — LLM Client
# Wraps Groq and Gemini APIs for LLM calls

import os
import json
import re
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

load_dotenv()  # loads .env

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "openai/gpt-oss-120b"   # Groq's fast 70B model
GEMINI_MODEL = "gemini-1.5-flash"

_groq_client = None
_gemini_client = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_client = genai.GenerativeModel(GEMINI_MODEL)
    return _gemini_client


def chat(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Single-turn chat with LLM. Tries Groq first, then Gemini."""
    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API Error: {e}")
        try:
            client = get_gemini_client()
            prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
            response = client.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens, temperature=0.3))
            return response.text.strip()
        except Exception as e2:
            print(f"Gemini API Error: {e2}")
            return "I apologize, but I'm unable to generate a response at this time."


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
