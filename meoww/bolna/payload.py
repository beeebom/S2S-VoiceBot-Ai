"""Reading Bolna's post-call webhook.

Bolna's docs describe the webhook ("the POST sent once each execution
finishes") but do not publish its field names, so this module reads each value
from any of several plausible keys rather than one guessed shape. When the body
turns out to be thin, `webhook.py` falls back to fetching the execution by id
through the API, whose shape is known.

Once a real webhook has arrived, print it with `--raw` and narrow these.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

TERMINAL = {"completed", "complete", "ended", "no-answer", "no_answer", "busy",
            "failed", "canceled", "cancelled", "call-disconnected"}

ANSWERED = {"completed", "complete", "ended", "call-disconnected"}


def _first(data: Dict[str, Any], *keys: str) -> Any:
    """First present, non-empty value among these keys, searched one level deep."""
    for key in keys:
        if key in data and data[key] not in (None, "", [], {}):
            return data[key]
    for value in data.values():
        if isinstance(value, dict):
            for key in keys:
                if key in value and value[key] not in (None, "", [], {}):
                    return value[key]
    return None


def execution_id(data: Dict[str, Any]) -> Optional[str]:
    value = _first(data, "execution_id", "id", "executionId", "call_id", "callId")
    return str(value) if value else None


def status(data: Dict[str, Any]) -> str:
    value = _first(data, "status", "call_status", "execution_status", "state")
    return str(value).lower() if value else "unknown"


def is_terminal(data: Dict[str, Any]) -> bool:
    return status(data) in TERMINAL


def was_answered(data: Dict[str, Any]) -> bool:
    return status(data) in ANSWERED


def extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    value = _first(data, "extracted_data", "extractedData", "extractions", "dispositions")
    return value if isinstance(value, dict) else {}


def recording_url(data: Dict[str, Any]) -> Optional[str]:
    value = _first(data, "recording_url", "recordingUrl", "recording", "telephony_data_recording_url")
    return str(value) if value else None


def phone_number(data: Dict[str, Any]) -> Optional[str]:
    value = _first(data, "to_number", "to_phone_number", "recipient_phone_number",
                   "customer_number", "to", "phone_number")
    return str(value) if value else None


def duration_seconds(data: Dict[str, Any]) -> Optional[float]:
    value = _first(data, "conversation_duration", "duration", "call_duration",
                   "duration_seconds", "total_duration")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def transcript(data: Dict[str, Any]) -> str:
    """The call transcript as text.

    Bolna may send a string or a list of turn objects; both appear in voice
    platforms. A list is flattened to the "SPEAKER: words" form the rest of
    the codebase already parses.
    """
    value = _first(data, "transcript", "transcription", "conversation", "messages", "turns")
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_turn_line(t) for t in value if _turn_line(t))
    return ""


def _turn_line(turn: Any) -> str:
    if isinstance(turn, str):
        return turn.strip()
    if not isinstance(turn, dict):
        return ""
    text = turn.get("text") or turn.get("content") or turn.get("message") or ""
    if not str(text).strip():
        return ""
    role = str(turn.get("role") or turn.get("speaker") or turn.get("from") or "user").lower()
    label = "AGENT" if role in {"assistant", "agent", "bot", "ai", "system"} else "USER"
    return f"{label}: {str(text).strip()}"


def summarise(data: Dict[str, Any]) -> List[str]:
    """One-line-per-field view, for logging an unfamiliar payload."""
    return [
        f"execution_id={execution_id(data)}",
        f"status={status(data)}",
        f"answered={was_answered(data)}",
        f"extracted_keys={list(extracted_data(data).keys())}",
        f"transcript_chars={len(transcript(data))}",
        f"duration={duration_seconds(data)}",
        f"recording={'yes' if recording_url(data) else 'no'}",
    ]
