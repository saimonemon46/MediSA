# ============================================================
# MediAI — LangGraph Workflow
# Orchestrates the multi-step AI triage pipeline
# ============================================================

import uuid
import json
from datetime import datetime
from typing import TypedDict, List, Annotated, Optional
import operator

try:
    
    from langgraph.graph import StateGraph,END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline.rag_engine import retrieve, format_context
from fastapi_ai.models.llm_client import chat_json, chat
from fastapi_ai.prompts.templates import (
    FOLLOWUP_QUESTIONS_SYSTEM, FOLLOWUP_QUESTIONS_USER,
    TRIAGE_ANALYSIS_SYSTEM, TRIAGE_ANALYSIS_USER,
    EXPLANATION_SYSTEM, EXPLANATION_USER,
    INTENT_DETECTION_SYSTEM, INTENT_DETECTION_USER,
    INPUT_ANALYSIS_SYSTEM, DYNAMIC_REASONING_SYSTEM,
    CONVERSATIONAL_TURN_SYSTEM,
    )


# ---- State schema ----

class TriageState(TypedDict):
    session_id: str
    user_id: int
    primary_symptom: str
    followup_questions: List[str]
    user_answers: List[str]
    image_analysis: Optional[dict]
    retrieved_context: str
    triage_result: dict
    explanation: str
    report: dict
    error: Optional[str]
    is_medical: bool
    intent_message: str
    user_concern: str
    acknowledgment: str
    chat_history: List[dict]  # list of {"role": "user/ai", "content": "..."}
    internal_reasoning: str
    current_question: str
    is_complete: bool
    validation_error: Optional[str]


# ---- Node functions ----

def node_input_analysis(state: TriageState) -> TriageState:
    """V2: Analyze the user's input for intent and validity."""
    latest_user_msg = state["chat_history"][-1]["content"] if state["chat_history"] else state["primary_symptom"]
    
    context = f"Last Question Asked: {state.get('current_question', 'N/A')}\nUser Message: {latest_user_msg}"
    prompt_user = f"Context:\n{context}"
    
    try:
        result = chat_json(INPUT_ANALYSIS_SYSTEM, prompt_user)
        state["is_medical"] = result.get("is_medical", True)
        state["validation_error"] = result.get("validation_error") if not result.get("is_valid") else None
        
        # If it's a new medical concern, update the primary symptom
        if result.get("intent") == "MEDICAL_CONCERN":
            state["primary_symptom"] = result.get("primary_symptom", latest_user_msg)
            
        # Update state with extracted tone/intent if needed
    except Exception as e:
        print(f"Error in input analysis: {e}")
        state["is_medical"] = True
        state["validation_error"] = None
    return state


def node_dynamic_reasoning(state: TriageState) -> TriageState:
    """V2: Update internal understanding and decide next steps."""
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in state["chat_history"]])
    rag_context = state.get("retrieved_context", "")
    
    prompt_user = f"Conversation History:\n{history_text}\n\nMedical Context:\n{rag_context}"
    
    try:
        result = chat_json(DYNAMIC_REASONING_SYSTEM, prompt_user)
        state["internal_reasoning"] = result.get("internal_reasoning", "")
        state["is_complete"] = result.get("is_complete", False)
        # We can store next_best_question_focus for the next node
        state["current_question"] = result.get("next_best_question_focus", "") 
    except Exception as e:
        print(f"Error in dynamic reasoning: {e}")
        state["is_complete"] = len(state.get("user_answers", [])) >= 6
    return state


def node_conversational_turn(state: TriageState) -> TriageState:
    """V2: Generate the empathetic conversational response."""
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in state["chat_history"]])
    
    # If there was a validation error, we need to ask for clarification
    if state.get("validation_error"):
        prompt_user = f"History:\n{history_text}\n\nValidation Error: {state['validation_error']}\n\nTask: Politely ask for clarification regarding the error."
    else:
        prompt_user = f"History:\n{history_text}\n\nInternal Reasoning: {state.get('internal_reasoning', '')}\n\nFocus: {state.get('current_question', '')}"
    
    try:
        result = chat_json(CONVERSATIONAL_TURN_SYSTEM, prompt_user)
        state["intent_message"] = result.get("message", "")
        state["current_question"] = result.get("current_question", "")
        
        # Add to history
        state["chat_history"].append({"role": "ai", "content": state["intent_message"]})
    except Exception as e:
        print(f"Error in conversational turn: {e}")
        state["intent_message"] = "I'm sorry, I'm having trouble processing that. Could you tell me more about your symptoms?"
    return state



def node_rag_retrieval(state: TriageState) -> TriageState:
    """Retrieve relevant medical knowledge from vector store."""
    query = state["primary_symptom"]
    if state.get("user_answers"):
        query += " " + " ".join(state["user_answers"])
    docs = retrieve(query, top_k=6)
    state["retrieved_context"] = format_context(docs)
    return state


def node_generate_questions(state: TriageState) -> TriageState:
    """Generate follow-up questions using LLM + RAG context."""
    image_hint = (
        "\n\nIf this may involve a visible rash, cut, wound, burn, swelling, pus, skin infection, or injury, "
        "include one question asking the user to upload a clear photo of the affected area if they feel comfortable."
    )
    prompt_user = FOLLOWUP_QUESTIONS_USER.format(
        concern=state.get("user_concern", ""),
        symptom=state["primary_symptom"] + image_hint,
        context=state["retrieved_context"]
    )
    try:
        result = chat_json(FOLLOWUP_QUESTIONS_SYSTEM, prompt_user)
        questions = result.get("questions", [])
    except Exception as e:
        print(f"Error generating AI questions: {e}")
        questions = []
    
    if not questions:
        # Check if the symptom suggests a visible issue
        visible_keywords = ["infection", "rash", "wound", "cut", "burn", "swelling", "pus", "eye", "skin", "injury"]
        is_visible = any(kw in state["primary_symptom"].lower() for kw in visible_keywords)
        
        questions = [
            f"How long have you been experiencing {state['primary_symptom']}?",
            "On a scale of 1 to 10, how severe is the discomfort?"
        ]
        
        if is_visible:
            questions.append("Could you please upload a clear photo of the affected area if you haven't already?")
            questions.append("Is there any discharge, pus, or spreading redness?")
        else:
            questions.append("Did this start suddenly or gradually?")
            questions.append("Do you have any known allergies related to these symptoms?")
            
        questions.extend([
            "Do you have any other symptoms such as fever, nausea, or fatigue?",
            "Are you currently taking any medications for this or other conditions?"
        ])
    
    state["followup_questions"] = questions[:6]  # Ensure exactly 6
    return state


def node_process_answers(state: TriageState) -> TriageState:
    """Re-retrieve context enriched by user answers and conversation history."""
    query = state["primary_symptom"]
    if state.get("chat_history"):
        query += " " + " ".join([m["content"] for m in state["chat_history"] if m["role"] == "user"])
    elif state.get("user_answers"):
        query += " " + " ".join(state["user_answers"])
    
    docs = retrieve(query, top_k=8)
    state["retrieved_context"] = format_context(docs)
    return state


def node_triage_engine(state: TriageState) -> TriageState:
    """Run triage analysis using LLM + enriched RAG context + conversation history."""
    if state.get("chat_history"):
        answers_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in state["chat_history"]])
    else:
        answers_text = "\n".join(
            f"Q{i+1}: {q}\nA: {a}"
            for i, (q, a) in enumerate(zip(
                state.get("followup_questions", []),
                state.get("user_answers", [])
            ))
        ) or "No follow-up answers provided."
    
    # Include image analysis data if available
    image_context = ""
    if state.get("image_analysis"):
        image_data = state["image_analysis"]
        image_context = f"""
Image Analysis Results (for contextual support):
- Image Type: {image_data.get('image_type', 'Unknown')}
- Visible Observations: {', '.join(image_data.get('visible_observations', []))}
- Possible Relevance: {image_data.get('possible_relevance', 'N/A')}
- Red Flags Noted: {', '.join(image_data.get('red_flags', [])) if image_data.get('red_flags') else 'None'}
- Image Quality: {image_data.get('image_quality', 'Unknown')}
- Confidence: {image_data.get('confidence', 'Low')}
- Disclaimer: Image analysis is supportive only and cannot diagnose a condition. Professional medical evaluation required.
"""
        answers_text += image_context
    
    if state.get("user_answers"):
        image_answers = [a for a in state["user_answers"] if "Uploaded image observations:" in a]
        if image_answers:
            answers_text += (
                "\n\nAdditional user-provided image context:\n" + "\n".join(image_answers)
            )

    prompt_user = TRIAGE_ANALYSIS_USER.format(
        symptom=state["primary_symptom"],
        answers=answers_text,
        context=state["retrieved_context"]
    )

    try:
        result = chat_json(TRIAGE_ANALYSIS_SYSTEM, prompt_user, max_tokens=1024)
        if not result.get("possible_condition"):
            raise ValueError("Empty triage result")
    except Exception:
        result = {
            "possible_condition": "Undetermined — insufficient information",
            "urgency": "medium",
            "recommended_specialist": "General Physician",
            "reasoning": "Based on the symptoms described and retrieved medical knowledge, a definitive assessment could not be determined. Professional evaluation is recommended.",
            "guidance": "Please consult a General Physician for a thorough in-person examination.",
            "symptoms_listed": [state["primary_symptom"]]
        }

    state["triage_result"] = result
    return state


def node_generate_explanation(state: TriageState) -> TriageState:
    """Generate a patient-friendly explanation."""
    try:
        explanation = chat(
            EXPLANATION_SYSTEM,
            EXPLANATION_USER.format(
                triage_result=json.dumps(state["triage_result"]),
                context=state["retrieved_context"][:800]
            ),
            max_tokens=300
        )
    except Exception:
        r = state["triage_result"]
        explanation = (
            f"Based on your symptoms, the assessment suggests {r.get('possible_condition', 'an unspecified condition')}. "
            f"The urgency level is {r.get('urgency', 'medium')}. "
            f"It is recommended you consult a {r.get('recommended_specialist', 'General Physician')}."
        )
    state["explanation"] = explanation
    return state


def node_generate_report(state: TriageState) -> TriageState:
    """Compile the final structured report."""
    r = state["triage_result"]
    reasoning = r.get("reasoning", "")
    
    # Enrich reasoning with image assessment if available
    if state.get("image_analysis"):
        img = state["image_analysis"]
        obs = ", ".join(img.get("visible_observations", []))
        img_summary = f"\n\nIMAGE ASSESSMENT: The uploaded {img.get('image_type', 'image')} showed {obs or 'no specific findings'}. Relevance: {img.get('possible_relevance', 'N/A')}."
        reasoning += img_summary

    state["report"] = {
        "session_id":            state["session_id"],
        "user_id":               state["user_id"],
        "possible_condition":    r.get("possible_condition", "Unknown"),
        "urgency":               r.get("urgency", "medium"),
        "recommended_specialist":r.get("recommended_specialist", "General Physician"),
        "reasoning":             reasoning,
        "guidance":              r.get("guidance", ""),
        "symptoms_listed":       r.get("symptoms_listed", [state["primary_symptom"]]),
        "explanation":           state.get("explanation", ""),
        "image_analysis":        state.get("image_analysis"),
        "generated_at":          datetime.utcnow().isoformat() + "Z",
    }
    return state


# ---- Graph construction ----

def build_graph():
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(TriageState)

    graph.add_node("input_analysis",        node_input_analysis)
    graph.add_node("rag_retrieval",         node_rag_retrieval)
    graph.add_node("dynamic_reasoning",     node_dynamic_reasoning)
    graph.add_node("conversational_turn",   node_conversational_turn)

    graph.set_entry_point("input_analysis")
    
    def route_after_input(state: TriageState):
        if not state.get("is_medical", True):
            return "conversational_turn"
        return "rag_retrieval"

    graph.add_conditional_edges(
        "input_analysis",
        route_after_input,
        {
            "conversational_turn": "conversational_turn",
            "rag_retrieval": "rag_retrieval"
        }
    )
    
    graph.add_edge("rag_retrieval",        "dynamic_reasoning")
    graph.add_edge("dynamic_reasoning",    "conversational_turn")
    graph.add_edge("conversational_turn",  END)

    return graph.compile()


def build_report_graph():
    """Separate graph for the report generation phase (after answers collected)."""
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(TriageState)

    graph.add_node("process_answers",       node_process_answers)
    graph.add_node("triage_engine",         node_triage_engine)
    graph.add_node("generate_explanation",  node_generate_explanation)
    graph.add_node("generate_report",       node_generate_report)

    graph.set_entry_point("process_answers")
    graph.add_edge("process_answers",      "triage_engine")
    graph.add_edge("triage_engine",        "generate_explanation")
    graph.add_edge("generate_explanation", "generate_report")
    graph.add_edge("generate_report",      END)

    return graph.compile()


# ---- High-level API functions ----

def run_conversational_step(
    session_id: str,
    message: str,
    user_id: int,
    chat_history: List[dict] = None
) -> dict:
    """V2: Run a single turn of the conversational triage."""
    if chat_history is None:
        chat_history = []
    
    # Add latest user message to history
    chat_history.append({"role": "user", "content": message})
    
    state: TriageState = {
        "session_id":          session_id,
        "user_id":             user_id,
        "primary_symptom":     message, # Fallback
        "chat_history":        chat_history,
        "followup_questions":  [],
        "user_answers":        [],
        "retrieved_context":   "",
        "triage_result":       {},
        "explanation":         "",
        "report":              {},
        "error":               None,
        "is_medical":          True,
        "intent_message":      "",
        "user_concern":        "",
        "acknowledgment":      "",
        "internal_reasoning":  "",
        "current_question":    "", # We might want to pass this in from the session
        "is_complete":         False,
        "validation_error":    None,
    }

    graph = build_graph()
    if graph:
        final_state = graph.invoke(state)
    else:
        # Manual execution fallback
        state = node_input_analysis(state)
        if state.get("is_medical", True):
            state = node_rag_retrieval(state)
            state = node_dynamic_reasoning(state)
        state = node_conversational_turn(state)
        final_state = state

    return {
        "session_id":     final_state["session_id"],
        "message":        final_state["intent_message"],
        "is_medical":     final_state.get("is_medical", True),
        "is_complete":    final_state.get("is_complete", False),
        "chat_history":   final_state["chat_history"],
        "internal_reasoning": final_state.get("internal_reasoning", ""),
    }


def run_question_generation(symptom: str, user_id: int, session_id: str = None) -> dict:
    """Legacy/initial step: starts the conversation."""
    return run_conversational_step(
        session_id=session_id or str(uuid.uuid4())[:8].upper(),
        message=symptom,
        user_id=user_id,
        chat_history=[]
    )


def run_report_generation(session_id: str, symptom: str, answers: list, user_id: int, image_analysis: dict = None, chat_history: list = None) -> dict:
    """Run the full triage analysis and report generation phase with optional image analysis."""
    state: TriageState = {
        "session_id":          session_id,
        "user_id":             user_id,
        "primary_symptom":     symptom,
        "followup_questions":  [],
        "user_answers":        answers,
        "chat_history":        chat_history or [],
        "image_analysis":      image_analysis,
        "retrieved_context":   "",
        "triage_result":       {},
        "explanation":         "",
        "report":              {},
        "error":               None,
    }

    graph = build_report_graph()
    if graph:
        final_state = graph.invoke(state)
    else:
        state = node_process_answers(state)
        state = node_triage_engine(state)
        state = node_generate_explanation(state)
        state = node_generate_report(state)
        final_state = state

    return {"report": final_state["report"]}
