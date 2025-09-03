from __future__ import annotations
import json
from typing import List, Dict, Any, Optional, Tuple

from lilith.plan_engine import LLMPlanGenerator
from lilith.llm_clients import get_client
from lilith.config import get_settings

# --------- Robust JSON array extractor (balanced bracket parser) -------------
def extract_first_json_array(text: str) -> str:
    """
    Finds the first top-level JSON array in text using a small state machine.
    Tolerates leading/trailing chatter from LLMs.
    """
    i = 0
    n = len(text)
    # Find first '['
    while i < n and text[i] != "[":
        i += 1
    if i >= n:
        raise ValueError("No '[' found in LLM output")

    depth = 0
    in_str = False
    esc = False
    j = i
    while j < n:
        ch = text[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    # include this closing bracket
                    return text[i : j + 1]
        j += 1
    raise ValueError("Unbalanced JSON array in LLM output")

# ------------------------- Schema + validation -------------------------------
def validate_steps_obj(data: Any, *, max_steps: int) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of steps")
    if not data:
        raise ValueError("Steps array is empty")
    if len(data) > max_steps:
        data = data[:max_steps]

    out: List[Dict[str, Any]] = []
    seen_titles = set()
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Step {idx} is not an object")
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Step {idx} missing or invalid 'title'")
        required = bool(item.get("required", False))
        title_norm = title.strip()
        if title_norm.lower() in seen_titles:
            # de-dupe quietly
            continue
        seen_titles.add(title_norm.lower())
        out.append({"title": title_norm, "required": required})
    return out

def robust_json_parser(raw_text: str, *, max_steps: int) -> List[Dict[str, Any]]:
    snippet = extract_first_json_array(raw_text)
    try:
        data = json.loads(snippet)
    except Exception as e:
        raise ValueError(f"Invalid JSON parse: {e}")
    return validate_steps_obj(data, max_steps=max_steps)

# ----------------------------- LLM call wiring -------------------------------
SYSTEM_PROMPT = (
    "You are a senior software project planner. "
    "Given a Title and Goal, output ONLY a JSON array of step objects. "
    "Each step has: title (string), required (boolean). "
    "Keep steps concise, actionable, and limited in number. "
    "Do not include any text before or after the JSON."
)

def make_user_prompt(title: str, goal: str, max_steps: int) -> str:
    return (
        f"Title: {title}\n"
        f"Goal: {goal}\n\n"
        f"Return a JSON array with at most {max_steps} steps. Example:\n"
        f'[{{"title":"Create README","required":true}},{{"title":"Add LICENSE (MIT)","required":false}}]'
    )

def _call_llm(title: str, goal: str, context: Optional[Dict[str, Any]] = None) -> str:
    s = get_settings()
    client = get_client()
    user = make_user_prompt(title, goal, s.max_steps)
    return client.generate(system=SYSTEM_PROMPT, user=user)

def _parse_llm(raw_text: str) -> List[Dict[str, Any]]:
    s = get_settings()
    return robust_json_parser(raw_text, max_steps=s.max_steps)

llm_generator = LLMPlanGenerator(llm_call=_call_llm, parser=_parse_llm)
