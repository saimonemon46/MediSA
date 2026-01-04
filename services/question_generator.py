from config.groq_config import get_llm

# Load prompt from file (correct way)
with open("prompts/followup_prompt.txt", "r", encoding="utf-8") as f:
    FOLLOWUP_PROMPT = f.read()

llm = get_llm()


def generate_followup(state: dict) -> str:
    prompt = FOLLOWUP_PROMPT.format(
        collected_symptoms=state.get("collected_symptoms", []),
        conversation_history=state.get("conversation_history", [])
    )

    response = llm.invoke(prompt).content.strip()
    return response
