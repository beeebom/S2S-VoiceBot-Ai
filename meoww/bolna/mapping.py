"""Bolna `extracted_data` -> ChurnRecord.

Bolna returns one result object per disposition, nested by category:

    {"Meoww": {"reason": {"objective": "bug", "subjective": "...",
                           "confidence": 0.91, "reasoning_objective": "..."}}}

This module is deliberately forgiving about what it reads. A missing key, an
empty string, the string "null" and JSON null all mean "not said", and an
option value Bolna invents falls back to UNCLEAR instead of raising. One odd
extraction should cost one field, never the whole record.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from ..extraction.models import (
    BugDetail,
    ChurnReason,
    ChurnRecord,
    Confidence,
    PriceDetail,
    ReturnLikelihood,
    Severity,
)
from .dispositions import CATEGORY

E = TypeVar("E", bound=Enum)

_EMPTY = {"", "null", "none", "n/a", "na", "not mentioned", "not specified", "unknown"}

_SPLICED = re.compile(
    r"\b(agent|assistant|bot|user|human|caller|customer)\s*:|\?\s+\S", re.I
)

_QUALITY = {"high": 0.9, "medium": 0.6, "low": 0.3}


def _leaf(data: Dict[str, Any], name: str) -> Dict[str, Any]:
    """The result object for one disposition.

    Looks in our category first, then any other, so a category renamed in the
    dashboard does not silently blank every field.
    """
    found = (data.get(CATEGORY) or {}).get(name)
    if found is None:
        for group in data.values():
            if isinstance(group, dict) and isinstance(group.get(name), dict):
                found = group[name]
                break
    return found if isinstance(found, dict) else {}


def _clean(value: Any) -> Optional[str]:
    """Normalise one free-text answer, or None if nothing was said."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in _EMPTY else text


def _trim_stop(text: Optional[str]) -> Optional[str]:
    """Drop a trailing full stop from a one-sentence value.

    The prompts ask for bare values, but models add a stop often enough to be
    worth handling here: these strings go onto a dashboard, where "Android."
    reads as sloppy. Only applied to short answers, never to prose fields like
    the summary, and only when there is a single stop to remove.
    """
    if text and text.endswith(".") and text.count(".") == 1:
        return text[:-1].strip() or None
    return text


def _text(data: Dict[str, Any], name: str) -> Optional[str]:
    """A free-text answer, tidied for display."""
    return _trim_stop(_clean(_leaf(data, name).get("subjective")))


def _prose(data: Dict[str, Any], name: str) -> Optional[str]:
    """A free-text answer that is a sentence, so punctuation is left alone."""
    return _clean(_leaf(data, name).get("subjective"))


def _choice(data: Dict[str, Any], name: str) -> Optional[str]:
    value = _clean(_leaf(data, name).get("objective"))
    return value.lower() if value else None


def _enum(data: Dict[str, Any], name: str, enum: Type[E], default: E) -> E:
    try:
        return enum(_choice(data, name))
    except ValueError:
        return default


def _yes(data: Dict[str, Any], name: str) -> bool:
    return _choice(data, name) == "yes"


def _confidence(data: Dict[str, Any], name: str, stated: bool) -> Confidence:
    leaf = _leaf(data, name)
    try:
        score = float(leaf.get("confidence") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    basis = (
        _clean(leaf.get("reasoning_objective"))
        or _clean(leaf.get("reasoning_subjective"))
        or _clean(leaf.get("subjective"))
        or ""
    )
    return Confidence(score=min(max(score, 0.0), 1.0), stated=stated, basis=basis)


def _quotes(data: Dict[str, Any]) -> List[str]:
    """User quotes worth showing a human.

    A quote that looks spliced is dropped rather than cleaned up: showing a
    judge a "user quote" that is half agent would be worse than showing one
    fewer quote.
    """
    raw = _leaf(data, "verbatim").get("subjective")
    if not raw or str(raw).strip().lower() in _EMPTY:
        return []

    quotes: List[str] = []
    for part in str(raw).split("|"):
        quote = part.strip().strip('"“”').strip()
        if not quote or _SPLICED.search(quote):
            continue
        quotes.append(_trim_stop(quote) or quote)
    return quotes[:3]


def record_from_extracted(data: Dict[str, Any]) -> ChurnRecord:
    reason = _enum(data, "reason", ChurnReason, ChurnReason.UNCLEAR)

    bug = None
    if reason in (ChurnReason.BUG, ChurnReason.PERFORMANCE):
        bug = BugDetail(
            surface=_text(data, "bug_surface"),
            device=_text(data, "bug_device"),
            platform=_text(data, "bug_platform"),
            steps=_prose(data, "bug_steps"),
            frequency=_text(data, "bug_frequency"),
        )
        if not any(bug.model_dump().values()):
            bug = None

    price = None
    if reason in (ChurnReason.PRICE, ChurnReason.COMPETITOR):
        price = PriceDetail(
            current_price=_text(data, "current_price"),
            acceptable_price=_text(data, "acceptable_price"),
            competitor=_text(data, "competitor"),
        )
        if not any(price.model_dump().values()):
            price = None

    return ChurnRecord(
        reason=reason,
        reason_confidence=_confidence(data, "reason", stated=_yes(data, "reason_stated")),
        severity=_enum(data, "severity", Severity, Severity.UNCLEAR),
        severity_confidence=_confidence(data, "severity", stated=False),
        return_likelihood=_enum(data, "return_likelihood", ReturnLikelihood, ReturnLikelihood.UNCLEAR),
        return_condition=_prose(data, "return_condition"),
        return_confidence=_confidence(data, "return_likelihood", stated=_yes(data, "return_stated")),
        bug=bug,
        price=price,
        summary=_prose(data, "summary") or "No summary returned.",
        verbatim=_quotes(data),
        interview_quality=_QUALITY.get(_choice(data, "interview_quality") or "", 0.0),
        followup_needed=_yes(data, "followup_needed"),
    )
