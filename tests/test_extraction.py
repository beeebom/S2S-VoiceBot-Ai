"""Offline tests: no network, no API key, no cost.

The model call is replaced with a fake client so these exercise everything
around it - parsing, guards, error handling and the record's own logic.
Whether the model extracts *well* is a separate question, answered by running
`python -m meoww.extract_cli transcripts/` against the real API.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from meoww.extraction.extractor import (
    ExtractionError,
    TranscriptTooShort,
    extract_record,
)
from meoww.extraction.models import (
    ChurnReason,
    ChurnRecord,
    Confidence,
    ReturnLikelihood,
    Severity,
)
from meoww.extraction.transcript import Speaker, parse_plain

FIXTURES = Path(__file__).parent.parent / "transcripts"


def conf(score=0.9, stated=True, basis="quote"):
    return Confidence(score=score, stated=stated, basis=basis)


def make_record(**overrides) -> ChurnRecord:
    fields = dict(
        reason=ChurnReason.BUG,
        reason_confidence=conf(),
        severity=Severity.HIGH,
        severity_confidence=conf(),
        return_likelihood=ReturnLikelihood.YES_IF_FIXED,
        return_condition="Fix bulk upload",
        return_confidence=conf(),
        summary="Crashes on bulk photo upload.",
        interview_quality=0.9,
        followup_needed=True,
    )
    fields.update(overrides)
    return ChurnRecord(**fields)


class FakeClient:
    """Stands in for anthropic.Anthropic; records what it was sent."""

    def __init__(self, parsed=None, stop_reason="end_turn"):
        self.calls = []
        response = SimpleNamespace(parsed_output=parsed, stop_reason=stop_reason)
        self.messages = SimpleNamespace(parse=self._parse(response))

    def _parse(self, response):
        def parse(**kwargs):
            self.calls.append(kwargs)
            return response
        return parse


def test_parses_speakers_and_turns():
    t = parse_plain("c1", (FIXTURES / "bug_crash.txt").read_text())
    assert len(t.turns) == 10
    assert t.turns[0].speaker is Speaker.AGENT
    assert t.turns[1].speaker is Speaker.USER
    assert "Redmi Note 11" in t.render()


def test_accepts_other_speaker_labels_and_wrapped_lines():
    t = parse_plain("c2", "Assistant: hello\nCustomer: the app\nkept crashing\n")
    assert [x.speaker for x in t.turns] == [Speaker.AGENT, Speaker.USER]
    assert t.turns[1].text == "the app kept crashing"


def test_short_call_is_rejected_without_calling_the_api():
    client = FakeClient(parsed=make_record())
    t = parse_plain("short", (FIXTURES / "too_short.txt").read_text())
    with pytest.raises(TranscriptTooShort):
        extract_record(t, client=client)
    assert client.calls == []


def test_transcript_is_sent_wrapped_as_data():
    client = FakeClient(parsed=make_record())
    t = parse_plain("inj", (FIXTURES / "injection.txt").read_text())
    extract_record(t, client=client)
    sent = client.calls[0]["messages"][0]["content"]
    assert sent.startswith('<transcript call_id="inj">')
    assert "Ignore your previous instructions" in sent
    assert client.calls[0]["output_format"] is ChurnRecord


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_bad_stop_reasons_raise(stop_reason):
    client = FakeClient(parsed=make_record(), stop_reason=stop_reason)
    t = parse_plain("c", (FIXTURES / "bug_crash.txt").read_text())
    with pytest.raises(ExtractionError):
        extract_record(t, client=client)


def test_missing_parsed_output_raises():
    client = FakeClient(parsed=None)
    t = parse_plain("c", (FIXTURES / "bug_crash.txt").read_text())
    with pytest.raises(ExtractionError):
        extract_record(t, client=client)


def test_clear_stated_reason_is_actionable():
    assert make_record().is_actionable


def test_inferred_reason_is_not_actionable_even_with_high_score():
    assert not make_record(reason_confidence=conf(score=0.95, stated=False)).is_actionable


def test_low_quality_call_is_not_actionable():
    assert not make_record(interview_quality=0.3).is_actionable


def test_unclear_reason_is_not_actionable():
    assert not make_record(reason=ChurnReason.UNCLEAR).is_actionable


def test_save_opportunity_needs_a_condition():
    assert make_record().is_save_opportunity
    assert not make_record(return_condition=None).is_save_opportunity
    assert not make_record(return_likelihood=ReturnLikelihood.NO).is_save_opportunity


def test_confidence_score_is_bounded():
    with pytest.raises(ValueError):
        Confidence(score=1.5, stated=True, basis="")
