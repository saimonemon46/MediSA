from agents.triage_graph import app

state = {
    "conversation_history": [],
    "collected_symptoms": [],
    "severity_score": 0,
    "severity_level": None
}

print("AI Medical Triage Started. Type symptoms.\n")
app.invoke(state)

print("\nSession ended.")
