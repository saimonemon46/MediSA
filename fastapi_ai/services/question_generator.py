from config.groq_config import get_llm

# Load prompt template
with open("prompts/followup_prompt.txt", "r", encoding="utf-8") as f:
    FOLLOWUP_PROMPT = f.read()

llm = get_llm()


def generate_followup(intent: str, state: dict) -> str:
    """
    intent: one of
    - duration
    - progression
    - severity
    - red_flags
    - associated_symptoms

    The LLM ONLY phrases the question.
    The system controls WHAT is being asked.
    """

    prompt = FOLLOWUP_PROMPT.format(
        intent=intent,
        collected_symptoms=state.get("collected_symptoms", []),
        conversation_history=state.get("conversation_history", [])
    )

    response = llm.invoke(prompt).content.strip()
    return response
