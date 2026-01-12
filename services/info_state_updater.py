from config.groq_config import get_llm

llm = get_llm()

INFO_STATE_PROMPT = """
Given the conversation so far, extract what is clearly known
about the symptom into the following fields.
Leave a field null if not clearly described.

Fields:
- onset
- duration
- progression
- sensation
- context
- associated_discomfort

Conversation:
{conversation_history}

Return ONLY valid JSON.
"""

def update_info_state(state: dict):
    prompt = INFO_STATE_PROMPT.format(
        conversation_history=state.get("conversation_history", [])
    )

    response = llm.invoke(prompt).content.strip()

    try:
        parsed = eval(response)  # simple, consistent JSON expected
        for k in state["info_state"]:
            if parsed.get(k):
                state["info_state"][k] = parsed[k]
    except Exception:
        pass
