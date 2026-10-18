"""The plan-type question tree. The backend is the single source of truth; the UI just walks it.

Each option either points to the next question or ends the flow (next=None). Answers are validated
against this tree, so a client can't submit a combination the flow never asks.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    hint: Optional[str] = None
    next: Optional[str] = None


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    help: str
    options: Tuple[Option, ...]


START = "coverage_source"

QUESTIONS: Dict[str, Question] = {
    q.id: q
    for q in [
        Question(
            "coverage_source",
            "Where does the coverage that sent this letter come from?",
            "Think about how you got the insurance, not which doctor you saw.",
            (
                Option("job", "A job (mine or a family member’s)", "Including COBRA continuation coverage.", "employer_type"),
                Option("self_bought", "I bought it myself", "Including plans from Get Covered New Jersey.", "purchase_channel"),
                Option("medicaid", "NJ FamilyCare or Medicaid", "Including NJ FamilyCare managed care plans."),
                Option("medicare", "Medicare", "Including Medicare Advantage plans from private companies.", "medicare_kind"),
                Option("unsure", "I’m not sure"),
            ),
        ),
        Question(
            "employer_type",
            "What kind of employer offers the plan?",
            "Government and religious-organization plans follow different rules from private employer plans.",
            (
                Option("private", "A private company or nonprofit", None, "funding"),
                Option("government", "A government employer", "Federal, state, county, city, or a public school."),
                Option("religious", "A church or religious organization"),
                Option("unsure", "I’m not sure", None, "funding"),
            ),
        ),
        Question(
            "funding",
            "Is the plan self-funded or fully insured?",
            "Self-funded (also called self-insured) means the employer pays claims and an insurance company only administers the plan. "
            "Your plan documents or HR department can tell you.",
            (
                Option("self_funded", "Self-funded (self-insured)", None, "grandfathered"),
                Option("fully_insured", "Fully insured by an insurance company", None, "issued_state"),
                Option("unsure", "I’m not sure"),
            ),
        ),
        Question(
            "issued_state",
            "Was the insurance policy issued in New Jersey?",
            "Your plan documents name the state. If your employer is based in another state, the policy may have been issued there.",
            (
                Option("nj", "Yes, in New Jersey", None, "grandfathered"),
                Option("other", "No, in another state"),
                Option("unsure", "I’m not sure", None, "grandfathered"),
            ),
        ),
        Question(
            "purchase_channel",
            "Where did you buy the plan?",
            "Get Covered New Jersey is the state-run marketplace (the New Jersey version of HealthCare.gov).",
            (
                Option("get_covered_nj", "Through Get Covered New Jersey"),
                Option("insurer_nj", "Directly from an insurance company, while living in New Jersey"),
                Option("other_state", "In another state"),
                Option("unsure", "I’m not sure"),
            ),
        ),
        Question(
            "medicare_kind",
            "Which kind of Medicare is this?",
            "Medicare Advantage (Part C) plans are run by private companies and have their own plan name and card.",
            (
                Option("advantage", "A Medicare Advantage plan from a private company"),
                Option("original", "Original Medicare (the red, white, and blue card)"),
                Option("unsure", "I’m not sure"),
            ),
        ),
        Question(
            "grandfathered",
            "Do your plan documents say the plan is “grandfathered”?",
            "Grandfathered plans are older plans that some federal appeal rules don’t fully cover. Most plans today are not grandfathered.",
            (
                Option("no", "No, or it doesn’t mention it"),
                Option("yes", "Yes, it says grandfathered"),
                Option("unsure", "I’m not sure"),
            ),
        ),
    ]
}


class FlowError(ValueError):
    pass


def walk(answers: Dict[str, str]) -> List[Tuple[Question, Option]]:
    """Follows the tree from START using the answers. Raises if answers skip, invent, or leave the flow unfinished."""
    path: List[Tuple[Question, Option]] = []
    current: Optional[str] = START
    while current is not None:
        question = QUESTIONS[current]
        value = answers.get(current)
        if value is None:
            raise FlowError(f"Missing an answer for “{question.prompt}”")
        option = next((o for o in question.options if o.value == value), None)
        if option is None:
            raise FlowError(f"That isn’t a valid answer for “{question.prompt}”")
        path.append((question, option))
        current = option.next
    extra = set(answers) - {q.id for q, _ in path}
    if extra:
        raise FlowError("Some answers don’t belong to the questions on this path.")
    return path
