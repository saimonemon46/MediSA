from config.groq_config import get_llm

with open("prompts/guidance_prompt.txt", "r", encoding="utf-8") as f:
    GUIDANCE_PROMPT = f.read()

llm = get_llm()


def generate_guidance(state: dict) -> str:
    prompt = GUIDANCE_PROMPT.format(
        collected_symptoms=state.get("collected_symptoms", []),
        conversation_history=state.get("conversation_history", [])
    )

    response = llm.invoke(prompt).content.strip()
    return response
