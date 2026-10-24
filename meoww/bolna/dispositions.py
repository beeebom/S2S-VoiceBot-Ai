"""The extraction questions Bolna asks of every finished call.

Bolna calls these "dispositions". Each one is a question an LLM answers after
the call, grouped under a category. They live here rather than only in the
dashboard so the setup is versioned and can be recreated exactly:

    python -m meoww.bolna_cli setup

The names are the keys `mapping.py` reads back, so renaming one here means
renaming it there too.
"""

from __future__ import annotations

from typing import Any, Dict, List

CATEGORY = "Meoww"

MODEL = "gpt-4.1-mini"

_NOT_SAID = (
    "Use only what the USER said. If the user did not mention it, return an "
    "empty answer. Never guess. Answer with the value only - no trailing "
    "full stop, no explanation, no restating the question."
)


def _yes_no(yes_when: str, no_when: str) -> List[Dict[str, str]]:
    return [
        {"value": "yes", "condition": yes_when},
        {"value": "no", "condition": no_when},
    ]


def _free_text(name: str, question: str) -> Dict[str, Any]:
    return {"name": name, "question": question, "is_subjective": True}


def _choice(name: str, question: str, options: List[Dict[str, str]],
            with_text: bool = False) -> Dict[str, Any]:
    return {
        "name": name,
        "question": question,
        "is_objective": True,
        "is_subjective": with_text,
        "objective_options": options,
    }


DISPOSITIONS: List[Dict[str, Any]] = [
    _choice(
        "reason",
        "What is the main reason the user stopped using the product? "
        "In the free-text answer, give one sentence explaining it.",
        [
            {"value": "bug", "condition": "Something broke: crashes, errors, data not saving."},
            {"value": "missing_feature", "condition": "The product lacked something the user needed."},
            {"value": "price", "condition": "It cost too much for the value they got."},
            {"value": "usability", "condition": "It was confusing or hard to use."},
            {"value": "performance", "condition": "It was slow, laggy or drained the battery."},
            {"value": "competitor", "condition": "They moved to another product, and price was not the main reason."},
            {"value": "no_longer_needed", "condition": "Their need went away, not the product's fault."},
            {"value": "support", "condition": "Customer support failed them."},
            {"value": "trust", "condition": "They lost trust: billing errors, privacy, security, money issues."},
            {"value": "unclear", "condition": "The user never gave a clear reason."},
        ],
        with_text=True,
    ),
    _choice(
        "reason_stated",
        "Did the USER give a specific reason for leaving, in their own words?",
        _yes_no(
            "The user named a concrete problem, need or cause themselves - "
            "something an engineer or manager could act on.",
            "Any of these: the user said they do not know, do not remember, or "
            "just stopped; the user named nothing concrete; the reason was "
            "suggested by the agent and the user only agreed; or the reason was "
            "inferred from circumstance rather than stated.",
        ),
    ),
    _choice(
        "severity",
        "How serious is the user's problem for the product?",
        [
            {"value": "blocking", "condition": "It stopped them using the core of the product at all."},
            {"value": "high", "condition": "It badly damaged a main flow, or involved money or data loss."},
            {"value": "medium", "condition": "A real annoyance they could work around."},
            {"value": "low", "condition": "A minor complaint."},
            {"value": "unclear", "condition": "Not enough information to judge."},
        ],
    ),

    _choice(
        "return_likelihood",
        "Would the user come back to the product?",
        [
            {"value": "yes_unconditional", "condition": "They said they would come back, with no conditions."},
            {"value": "yes_if_fixed", "condition": "They said they would come back if something specific changed."},
            {"value": "maybe", "condition": "They were unsure or non-committal."},
            {"value": "no", "condition": "They said they would not come back."},
            {"value": "unclear", "condition": "The topic never came up."},
        ],
    ),
    _choice(
        "return_stated",
        "Did the USER explicitly say whether they would come back?",
        _yes_no("The user answered this directly.", "The user never answered this directly."),
    ),
    _free_text(
        "return_condition",
        "What would have to change for the user to come back? One sentence. "
        + _NOT_SAID,
    ),

    _free_text("bug_surface", "Which screen, feature or flow had the problem? " + _NOT_SAID),
    _free_text("bug_device", "Which phone or device model did the user name? " + _NOT_SAID),
    _free_text("bug_platform", "Which platform: iOS, Android, web or desktop? " + _NOT_SAID),
    _free_text("bug_steps", "What was the user doing when the problem happened? " + _NOT_SAID),
    _free_text("bug_frequency", "How often did it happen: every time, sometimes, once? " + _NOT_SAID),

    _free_text(
        "current_price",
        "What was the user paying? Keep the currency the user used - if they "
        "said rupees, do not convert it to dollars. " + _NOT_SAID,
    ),
    _free_text(
        "acceptable_price",
        "What price did the user say they would have stayed at, or would come "
        "back at? Only a number or a range the user actually named. Keep the "
        "currency the user used - if they said rupees, do not convert it to "
        "dollars. " + _NOT_SAID,
    ),
    _free_text("competitor", "Which other product did the user switch to? " + _NOT_SAID),

    _free_text(
        "summary",
        "Summarise why this user left and what would bring them back, in one "
        "sentence a product manager could read in a list of fifty. Keep any "
        "amount in the currency the user used - never convert it.",
    ),
    _free_text(
        "verbatim",
        "Copy up to three short quotes that best show why the user left. "
        "Every quote must come from a USER turn only - never include any part "
        "of an AGENT turn, and never join an agent question to a user answer. "
        "Copy each one word for word, never paraphrase. Separate quotes with a "
        "vertical bar ( | ). If the user said nothing worth quoting, return an "
        "empty answer.",
    ),
    _choice(
        "interview_quality",
        "Did this call surface useful information about why the user left?",
        [
            {"value": "high", "condition": "A clear reason with specific detail."},
            {"value": "medium", "condition": "A reason, but little detail."},
            {"value": "low", "condition": "Terse, vague or cut short; nothing usable."},
        ],
    ),
    _choice(
        "followup_needed",
        "Should a human call this user back?",
        _yes_no(
            "A person could plausibly win them back, or they raised something "
            "serious such as a billing error, lost money, data loss or safety.",
            "Nothing a human call would change.",
        ),
    ),
]


def payloads() -> List[Dict[str, Any]]:
    """Each disposition with the shared category and model filled in."""
    return [{**d, "category": CATEGORY, "model": MODEL} for d in DISPOSITIONS]
