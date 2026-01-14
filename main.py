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

# In-memory session store
SESSIONS = {}

# ==================================================
# Capture stdout from graph execution
# ==================================================

def run_graph_with_capture(state: dict):
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer

    try:
        new_state = app.invoke(state)
    finally:
        sys.stdout = old_stdout

    output = buffer.getvalue().strip()
    return new_state, output if output else None


# ==================================================
# Models
# ==================================================

class StartResponse(BaseModel):
    session_id: str
    agent_message: str | None


class UserInput(BaseModel):
    session_id: str
    message: str


class AgentResponse(BaseModel):
    agent_message: str | None
    done: bool


# ==================================================
# Endpoints
# ==================================================

@api.post("/start", response_model=StartResponse)
def start_session():
    session_id = str(uuid.uuid4())

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

    # Inject user input
    state["__user_input__"] = data.message

    new_state, output = run_graph_with_capture(state)
    SESSIONS[data.session_id] = new_state

    # Conversation is done ONLY when graph reaches terminal state
    is_done = new_state.get("stage") == "end"

    return AgentResponse(
        agent_message=output,
        done=is_done
    )
