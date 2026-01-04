from agents.triage_graph import app

state = {
    "conversation_history": [],
    "collected_symptoms": [],
    "asked_questions": [],
    "severity_score": 0,
    "severity_level": None,
    "stop_flag": False,
    "followup_count": 0,
    "last_symptom_count": 0
}


print("AI Medical Triage Started. Type symptoms.\n")
app.invoke(state)

print("\nSession ended.")
