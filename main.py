# # ==================================================
# # FastAPI API for LangGraph Triage Agent
# # ==================================================

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from typing import Optional, Dict, Any
# import uuid

# from agents.triage_graph import app as triage_graph  # your compiled graph


# api = FastAPI(title="Medical Triage API")

# # In-memory session store (swap for Redis later if needed)
# SESSIONS: Dict[str, Dict[str, Any]] = {}


# # ==================================================
# # Schemas
# # ==================================================

# class StartResponse(BaseModel):
#     session_id: str
#     messages: list


# class ChatRequest(BaseModel):
#     session_id: str
#     user_input: Optional[str] = None


# class ChatResponse(BaseModel):
#     session_id: str
#     messages: list
#     awaiting_input: bool
#     done: bool


# # ==================================================
# # Helpers
# # ==================================================
# def run_until_pause(state: dict) -> dict:
#     """
#     Step through the graph until it needs input or finishes.
#     """
#     for event in triage_graph.stream(state):
#         # event is a dict like {"node_name": state}
#         state = next(iter(event.values()))

#         if state.get("awaiting_input"):
#             break

#         if state.get("done"):
#             break

#     return state




# def pop_messages(state: dict) -> list:
#     return state.pop("ui_messages", [])


# # ==================================================
# # Endpoints
# # ==================================================

# from fastapi.responses import JSONResponse
# import traceback

# @api.post("/start")
# def start_session():
#     try:
#         session_id = str(uuid.uuid4())

#         state = {}
#         state = run_until_pause(state)
#         messages = pop_messages(state)

#         SESSIONS[session_id] = state

#         return {
#             "session_id": session_id,
#             "messages": messages,
#             "awaiting_input": state.get("awaiting_input", False)
#         }


#     except Exception as e:
#         traceback.print_exc()
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "error": str(e),
#                 "traceback": traceback.format_exc(),
#             }
#         )

# @api.post("/chat", response_model=ChatResponse)
# def chat(req: ChatRequest):
#     if req.session_id not in SESSIONS:
#         raise HTTPException(status_code=404, detail="Invalid session_id")

#     state = SESSIONS[req.session_id]

#     if req.user_input:
#         state["user_input"] = req.user_input

#     state = run_until_pause(state)
#     messages = pop_messages(state)

#     SESSIONS[req.session_id] = state

#     return {
#         "session_id": req.session_id,
#         "messages": messages,
#         "awaiting_input": state.get("awaiting_input", False),
#         "done": state.get("done", False),
#     }



# @api.get("/ping")
# def ping():
#     return {"ok": True}















from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import uuid

from services.symptom_extractor import SymptomExtractor
from services.severity_engine import SeverityEngine
from services.question_generator import generate_followup
from services.guidance_generator import generate_guidance
from services.doctor_service import DoctorService
from services.confidence_engine import ConfidenceEngine
from services.info_state_updater import update_info_state
from services.disease_specialist_mapper import DiseaseSpecialistMapper

from agents.decision_agent import decide_next, doctor_decision

from utils.coverage_updater import update_info_coverage
from utils.followup_policy import next_missing_dimension
from utils.triage_reasoning import generate_triage_reasoning
from utils.confidence_bucket import confidence_bucket


# ==================================================
# FastAPI Setup
# ==================================================

app = FastAPI(title="Medical Triage API", version="1.0.0")

# Services
extractor = SymptomExtractor()
severity_engine = SeverityEngine()
confidence_engine = ConfidenceEngine()
doctor_service = DoctorService()
mapper = DiseaseSpecialistMapper()

MAX_FOLLOWUPS = 12

# In-memory session storage (use Redis/DB for production)
sessions: Dict[str, Dict[str, Any]] = {}


# ==================================================
# Pydantic Models
# ==================================================

class StartSessionRequest(BaseModel):
    initial_symptoms: str

class StartSessionResponse(BaseModel):
    session_id: str
    question: str
    stage: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str

class AnswerResponse(BaseModel):
    stage: str
    question: Optional[str] = None
    triage_reasoning: Optional[List[str]] = None
    triage_summary: Optional[Dict[str, bool]] = None
    confidence_score: Optional[float] = None
    confidence_bucket: Optional[str] = None
    severity_level: Optional[str] = None
    guidance: Optional[str] = None
    requires_emergency: Optional[bool] = None
    session_complete: bool = False

class LocationRequest(BaseModel):
    session_id: str
    location: str

class DoctorResponse(BaseModel):
    doctors: List[Dict[str, Any]]
    specialist_type: str

class WantDoctorRequest(BaseModel):
    session_id: str
    want_doctor: bool


# ==================================================
# Helper Functions
# ==================================================

def initialize_state() -> Dict[str, Any]:
    """Initialize a new session state"""
    return {
        "conversation_history": [],
        "collected_symptoms": [],
        "asked_questions": [],
        "followup_count": 0,
        "stop_flag": False,
        "info_state": {
            "onset": None,
            "duration": None,
            "progression": None,
            "sensation": None,
            "context": None,
            "associated_discomfort": None,
        },
        "info_coverage": {
            "duration": False,
            "context": False,
            "progression": False,
            "sensation": False,
        },
        "stage": "opening",
        "severity_score": None,
        "severity_level": None,
        "confidence_score": None,
        "want_doctor": None,
        "user_location": None,
    }

def process_followup(state: Dict[str, Any]) -> Dict[str, Any]:
    """Process a followup question"""
    state["followup_count"] += 1

    # Hard stop
    if state["followup_count"] >= MAX_FOLLOWUPS:
        state["stop_flag"] = True
        state["stage"] = "severity"
        return state

    # Update extracted info
    update_info_state(state)

    dimension = next_missing_dimension(state["info_state"])
    if dimension is None:
        state["stop_flag"] = True
        state["stage"] = "severity"
        return state

    # Pre-lock dimension
    state["current_dimension"] = dimension
    state["info_state"][dimension] = True

    question = generate_followup(dimension, state)

    if question.strip() == "STOP" or question in state["asked_questions"]:
        state["stop_flag"] = True
        state["stage"] = "severity"
        return state

    state["asked_questions"].append(question)
    state["current_question"] = question
    state["stage"] = "followup"

    return state

def calculate_severity(state: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate severity and confidence"""
    score, level = severity_engine.calculate(state["collected_symptoms"])
    
    state["severity_score"] = score
    state["severity_level"] = level
    state["confidence_score"] = confidence_engine.calculate(state)
    
    # Determine next stage
    if level == "emergency":
        state["stage"] = "emergency"
    else:
        state["stage"] = "low_severity"
    
    return state


# ==================================================
# API Endpoints
# ==================================================

@app.post("/api/start-session", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """Start a new triage session with initial symptoms"""
    session_id = str(uuid.uuid4())
    state = initialize_state()
    
    # Process initial symptoms
    state["conversation_history"].append(request.initial_symptoms)
    state["collected_symptoms"] = extractor.extract(request.initial_symptoms)
    
    # Generate first followup question
    state = process_followup(state)
    
    sessions[session_id] = state
    
    return StartSessionResponse(
        session_id=session_id,
        question=state.get("current_question", ""),
        stage=state["stage"]
    )


@app.post("/api/answer", response_model=AnswerResponse)
async def submit_answer(request: AnswerRequest):
    """Submit an answer to the current question"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = sessions[request.session_id]
    
    # Add answer to history
    state["conversation_history"].append(request.answer)
    
    # Extract symptoms from answer
    new_symptoms = extractor.extract(request.answer)
    state["collected_symptoms"].extend(new_symptoms)
    
    # Update coverage
    update_info_coverage(state, request.answer)
    
    # Check if we should continue with followups
    if state["stage"] == "followup":
        dimension = next_missing_dimension(state["info_state"])
        if dimension is None or state["followup_count"] >= MAX_FOLLOWUPS:
            # Move to severity assessment
            state = calculate_severity(state)
        else:
            # Generate next followup
            state = process_followup(state)
    
    # Prepare response based on stage
    response_data = {
        "stage": state["stage"],
        "session_complete": False
    }
    
    if state["stage"] == "followup":
        response_data["question"] = state.get("current_question", "")
    
    elif state["stage"] in ["low_severity", "emergency"]:
        # Include triage results
        response_data["triage_reasoning"] = generate_triage_reasoning(state)
        response_data["triage_summary"] = state["info_coverage"]
        response_data["confidence_score"] = state.get("confidence_score")
        response_data["severity_level"] = state.get("severity_level")
        
        if state.get("confidence_score"):
            response_data["confidence_bucket"] = confidence_bucket(state["confidence_score"])
        
        if state["stage"] == "low_severity":
            response_data["guidance"] = generate_guidance(state)
        else:
            response_data["requires_emergency"] = True
    
    sessions[request.session_id] = state
    
    return AnswerResponse(**response_data)


@app.post("/api/want-doctor")
async def want_doctor(request: WantDoctorRequest):
    """Indicate whether user wants to see a doctor"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = sessions[request.session_id]
    state["want_doctor"] = request.want_doctor
    
    if request.want_doctor:
        state["stage"] = "ask_location"
        sessions[request.session_id] = state
        return {"stage": "ask_location", "message": "Please provide your location"}
    else:
        state["stage"] = "complete"
        sessions[request.session_id] = state
        return {"stage": "complete", "message": "Session ended"}


@app.post("/api/find-doctors", response_model=DoctorResponse)
async def find_doctors(request: LocationRequest):
    """Find doctors based on location and symptoms"""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = sessions[request.session_id]
    state["user_location"] = request.location
    
    symptoms = state.get("collected_symptoms", [])
    specialist = mapper.infer_specialist(symptoms)
    
    results = doctor_service.find(
        location=request.location,
        specialty=specialist,
        limit=3
    )
    
    # Fallback to general medicine if no specialists found
    if results.empty:
        results = doctor_service.find(request.location, specialty="Medicine", limit=3)
        specialist = "Medicine (General)"
    
    doctors = []
    if not results.empty:
        doctors = results.to_dict('records')
    
    state["stage"] = "complete"
    sessions[request.session_id] = state
    
    return DoctorResponse(
        doctors=doctors,
        specialist_type=specialist
    )


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = sessions[session_id]
    return {
        "session_id": session_id,
        "stage": state["stage"],
        "followup_count": state["followup_count"],
        "collected_symptoms": state["collected_symptoms"]
    }


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "active_sessions": len(sessions)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)