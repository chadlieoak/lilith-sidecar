from __future__ import annotations
from dataclasses import dataclass
from typing import List, Protocol, Dict, Any, Optional, Callable

@dataclass
class StepSpec:
    title: str
    required: bool = False

class PlanGenerator(Protocol):
    def generate(self, *, title: str, goal: str, context: Optional[Dict[str, Any]] = None) -> List[StepSpec]:
        ...

class DeterministicPlanGenerator:
    def __init__(self, plan_fn: Callable[[str, str], List[Dict[str, Any]]]):
        self._plan_fn = plan_fn

    def generate(self, *, title: str, goal: str, context: Optional[Dict[str, Any]] = None) -> List[StepSpec]:
        raw_steps = self._plan_fn(title, goal) or []
        out: List[StepSpec] = []
        for s in raw_steps:
            t = s.get("title")
            if not isinstance(t, str) or not t.strip():
                continue
            out.append(StepSpec(title=t.strip(), required=bool(s.get("required", False))))
        return out

class LLMPlanGenerator:
    def __init__(self, llm_call: Optional[Callable[[str, str, Optional[Dict[str, Any]]], str]] = None,
                 parser: Optional[Callable[[str], List[Dict[str, Any]]]] = None):
        self._llm_call = llm_call
        self._parser = parser

    def generate(self, *, title: str, goal: str, context: Optional[Dict[str, Any]] = None) -> List[StepSpec]:
        if not self._llm_call or not self._parser:
            # Safe fallback mirroring current deterministic sample
            fallback = [
                {"title": "Create README", "required": True},
                {"title": "Scaffold minimal Tailwind page", "required": True},
                {"title": "Add hero title", "required": False},
                {"title": "Add LICENSE (MIT)", "required": False},
            ]
            return [StepSpec(**x) for x in fallback]

        raw_text = self._llm_call(title, goal, context)
        parsed = self._parser(raw_text)
        return [StepSpec(title=s["title"], required=bool(s.get("required", False))) for s in parsed]

class PlanRegistry:
    def __init__(self):
        self._by_name: Dict[str, PlanGenerator] = {}

    def register(self, name: str, gen: PlanGenerator) -> None:
        self._by_name[name] = gen

    def get(self, name: str) -> PlanGenerator:
        if name not in self._by_name:
            raise KeyError(f"Unknown plan engine '{name}'")
        return self._by_name[name]
