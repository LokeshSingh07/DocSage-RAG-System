from langgraph.graph import StateGraph, START, END
from app.core.config import get_settings as settings
from app.core.observability import trace
from app.guardrails import check_input, check_output, GuardrailError
from app.rag.retrieval import retriever
from app.llm.factory import ask_llm

from typing import TypedDict, Optional, Literal
from rich import print
import json


NO_PASSAGES_MSG = "I couldn't find anything relevant in your documents."
NOT_ANSWERED_MSG = "I found related passages, but they don't answer your question."
MAX_HISTORY_CHARS = 2000

MIN_ANSWER_WORDS = 15

# phrases a model uses when it is really refusing
REFUSAL_HINTS = (
    "not found", "no information", "cannot find", "can't find",
    "couldn't find", "does not contain", "doesn't contain",
    "don't have enough", "not mentioned", "not provided",
)

# state
class State(TypedDict):
    question: str
    principal: object           # {tenant, groups, subject}
    passages: list[str]
    answer: str
    status: Literal["answered", "no_answer", "blocked"]
    history: list




# FLOW GRAPH
# guard
# retirieve for relevant chunks in pinecone
# IF no chunks found and no history
#   return no answer
# ELSE
#   generate answer using retrieved passages and conversation history
#       if no answer found return no answer
#       return answer


# STEP 1: guard
def guard(state):
    return { "question": check_input(state["question"]) }


# STEP 2: retrieve
def retrieve(state):
    p = state["principal"]
    passages = retriever(p.tenant, state["question"], p.groups, p.owner)
    return {"passages": passages}


# STEP 3: check chunks or conversation history found
def check_chunks_found(state):
    has_passages = bool(state.get("passages"))
    has_history = bool(state.get("history"))
    # Allow generation if relevant document chunks were found OR if conversation history is available
    return "generate" if (has_passages or has_history) else "no_answer"


# step 3.1: generate
def parse_llm_reply(text: str) -> dict:
    """Turn the model's JSON string into {"answer": ..., "found": ...}."""
    text = text.strip().replace("```json", "").replace("```", "").strip()

    answer = text
    found = False

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            answer = str(data.get("answer", "")).strip()
            flag = data.get("found")
            found = flag is True or (isinstance(flag, str) and flag.strip().lower() == "true")
    except json.JSONDecodeError:
        pass

    # fallback: long answer means an answer exists, unless it reads like a refusal
    if not found and answer:
        word_count = len(answer.split())
        looks_like_refusal = any(h in answer.lower() for h in REFUSAL_HINTS)
        if word_count >= MIN_ANSWER_WORDS and not looks_like_refusal:
            found = True

    return {"answer": answer, "found": found}


def generate(state):
    raw = ask_llm(state["question"], state["passages"], history=state["history"])
    reply = parse_llm_reply(raw)
    if not reply.get("found"):
        fallback_msg = NOT_ANSWERED_MSG if state.get("passages") else NO_PASSAGES_MSG
        return {
            "answer": fallback_msg,
            "status": "no_answer",
        }

    return {"answer": check_output(reply["answer"]), "status": "answered"}


# step 3.2: no answer
def no_answer(state):
    return {
        "answer": NO_PASSAGES_MSG,
        "status": "no_answer"
    }




# FLOW GRAPH
def make_graph():
    g = StateGraph(State)

    g.add_node("guard", guard)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("no_answer", no_answer)

    # add edges between nodes
    g.add_edge(START, "guard")
    g.add_edge("guard", "retrieve")

    # conditional flow: check if passages or history exist
    g.add_conditional_edges(
        "retrieve",
        check_chunks_found, 
        {"generate": "generate", "no_answer": "no_answer"}
    )

    g.add_edge("generate", END)
    g.add_edge("no_answer", END)

    return g.compile()



graph = make_graph()




def chat(principal, question, history=None):
    try:
        result = graph.invoke({"question": question, "principal": principal, "history": history or []})
        return {
            "answer": result["answer"],
            "sources": result["passages"],
            "status": result["status"]
        }

    except GuardrailError as e:
        return {"answer": str(e), "sources": [], "status": "blocked"}
