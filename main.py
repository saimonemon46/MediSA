# ==================================================
# FastAPI wrapper for LangGraph medical triage agent
# ==================================================

from fastapi import FastAPI
from pydantic import BaseModel
import uuid
import io
import sys

from agents.triage_graph import app

api = FastAPI()

SESSIONS = {}

# ==================================================
# Capture stdout
# ==================================================

def run_graph_with_capture(state: dict):
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer

    try:
        new_state = app.invoke(state)
    finally:
        sys.stdout = old_stdout

    return new_state, buffer.getvalue().strip()

# ==================================================
# Models
# ==================================================

class StartResponse(BaseModel):
    session_id: str
    agent_message: str

class UserInput(BaseModel):
    session_id: str
    message: str

class AgentResponse(BaseModel):
    agent_message: str
    done: bool

# ==================================================
# Endpoints
# ==================================================

@api.post("/start", response_model=StartResponse)
def start_session():
    session_id = str(uuid.uuid4())

    # no dummy input needed anymore
    state = {}

    new_state, output = run_graph_with_capture(state)
    SESSIONS[session_id] = new_state

    return StartResponse(
        session_id=session_id,
        agent_message=output
    )

@api.post("/continue", response_model=AgentResponse)
def continue_session(data: UserInput):
    if data.session_id not in SESSIONS:
        return AgentResponse(
            agent_message="Invalid session.",
            done=True
        )

    state = SESSIONS[data.session_id]
    state["__user_input__"] = data.message

    new_state, output = run_graph_with_capture(state)
    SESSIONS[data.session_id] = new_state

    return AgentResponse(
        agent_message=output,
        done=bool(new_state.get("stop_flag", False))
    )
