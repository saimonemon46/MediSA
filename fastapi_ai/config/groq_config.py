from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="openai/gpt-oss-120b",
        temperature=0.3
    )
