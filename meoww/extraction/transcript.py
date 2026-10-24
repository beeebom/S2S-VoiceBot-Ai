"""Call transcripts, in the shape the extractor expects.

Bolna and other voice platforms hand back transcripts in slightly different
shapes. Everything is normalised to a list of `Turn`s here so the extractor
never has to care where a call came from.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List

from pydantic import BaseModel


class Speaker(str, Enum):
    AGENT = "agent"
    USER = "user"


class Turn(BaseModel):
    speaker: Speaker
    text: str


class Transcript(BaseModel):
    call_id: str
    turns: List[Turn]

    @property
    def user_word_count(self) -> int:
        return sum(len(t.text.split()) for t in self.turns if t.speaker is Speaker.USER)

    def render(self) -> str:
        """Plain-text form for the model, one turn per line."""
        return "\n".join(f"{t.speaker.value.upper()}: {t.text}" for t in self.turns)


_LINE = re.compile(r"^\s*(agent|assistant|bot|ai|user|human|caller|customer)\s*[:\-]\s*(.*)$", re.I)
_AGENT_LABELS = {"agent", "assistant", "bot", "ai"}


def parse_plain(call_id: str, text: str) -> Transcript:
    """Parse a 'Speaker: words' transcript.

    Lines without a speaker label are treated as a continuation of the previous
    turn, which is how most platforms wrap long utterances.
    """
    turns: List[Turn] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = _LINE.match(raw)
        if m:
            label, words = m.group(1).lower(), m.group(2).strip()
            speaker = Speaker.AGENT if label in _AGENT_LABELS else Speaker.USER
            turns.append(Turn(speaker=speaker, text=words))
        elif turns:
            turns[-1] = Turn(speaker=turns[-1].speaker, text=f"{turns[-1].text} {raw.strip()}")
    return Transcript(call_id=call_id, turns=turns)
