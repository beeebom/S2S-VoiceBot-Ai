"""Offline tests for the Bolna side: no network, no API key.

The payloads below follow the result-object format in Bolna's extraction docs
(subjective, objective, confidence, reasoning_*). If a real response turns out
to differ, copy it into a test here before changing `mapping.py`.
"""

import re
from pathlib import Path

from meoww.bolna.dispositions import CATEGORY, DISPOSITIONS, payloads
from meoww.bolna.mapping import record_from_extracted
from meoww.extraction.models import ChurnReason, ReturnLikelihood, Severity

MAPPING_SOURCE = (Path(__file__).parent.parent / "meoww" / "bolna" / "mapping.py").read_text(encoding="utf-8")


def leaf(objective=None, subjective=None, confidence=0.9, reasoning=None):
    return {
        "objective": objective,
        "subjective": subjective,
        "confidence": confidence,
        "reasoning_objective": reasoning,
        "reasoning_subjective": None,
    }


def bug_call():
    return {
        CATEGORY: {
            "reason": leaf("bug", "App crashed on bulk photo upload.", 0.93, "User said it crashed every time."),
            "reason_stated": leaf("yes"),
            "severity": leaf("blocking", confidence=0.8),
            "return_likelihood": leaf("yes_if_fixed", confidence=0.88),
            "return_stated": leaf("yes"),
            "return_condition": leaf(subjective="Fix uploading more than ten photos."),
            "bug_surface": leaf(subjective="Photo upload"),
            "bug_device": leaf(subjective="Redmi Note 11"),
            "bug_platform": leaf(subjective="Android"),
            "bug_steps": leaf(subjective="Uploading about twenty photos at once"),
            "bug_frequency": leaf(subjective="Every time above ten photos"),
            "current_price": leaf(subjective=""),
            "acceptable_price": leaf(subjective="null"),
            "competitor": leaf(subjective=None),
            "summary": leaf(subjective="Left over crashes on bulk upload; would return if fixed."),
            "verbatim": leaf(subjective='"It crashed every time" | "that was the only thing wrong"'),
            "interview_quality": leaf("high"),
            "followup_needed": leaf("yes"),
        }
    }


def test_trailing_full_stop_is_stripped_from_short_answers():
    data = bug_call()
    data[CATEGORY]["bug_device"] = leaf(subjective="Redmi Note 11.")
    data[CATEGORY]["bug_platform"] = leaf(subjective="Android.")
    r = record_from_extracted(data)
    assert r.bug.device == "Redmi Note 11"
    assert r.bug.platform == "Android"


def test_real_prose_keeps_its_punctuation():
    data = bug_call()
    data[CATEGORY]["summary"] = leaf(subjective="They left over crashes. They would return if fixed.")
    assert record_from_extracted(data).summary.endswith("if fixed.")


def test_spliced_quotes_are_dropped():
    data = bug_call()
    data[CATEGORY]["verbatim"] = leaf(subjective=(
        '"It crashed every time." | '
        '"If bulk upload worked, would you come back? Yeah honestly, that was the only thing wrong." | '
        '"Agent: which phone? User: Redmi Note 11"'
    ))
    assert record_from_extracted(data).verbatim == ["It crashed every time"]


def test_a_user_question_is_still_a_valid_quote():
    data = bug_call()
    data[CATEGORY]["verbatim"] = leaf(subjective='"So why does it keep crashing?"')
    assert record_from_extracted(data).verbatim == ["So why does it keep crashing?"]


def test_empty_verbatim_markers_give_no_quotes():
    for marker in ("", "null", "none"):
        data = bug_call()
        data[CATEGORY]["verbatim"] = leaf(subjective=marker)
        assert record_from_extracted(data).verbatim == []


def test_bug_call_maps_to_actionable_save():
    r = record_from_extracted(bug_call())
    assert r.reason is ChurnReason.BUG
    assert r.reason_confidence.stated and r.reason_confidence.score == 0.93
    assert r.reason_confidence.basis == "User said it crashed every time."
    assert r.severity is Severity.BLOCKING
    assert r.bug.device == "Redmi Note 11"
    assert r.price is None
    assert r.verbatim == ["It crashed every time", "that was the only thing wrong"]
    assert r.is_actionable and r.is_save_opportunity and r.followup_needed


def test_empty_markers_all_mean_not_said():
    data = bug_call()
    data[CATEGORY]["reason"] = leaf("price", "Too expensive.")
    r = record_from_extracted(data)
    assert r.price is None


def test_price_call_keeps_acceptable_price():
    data = bug_call()
    data[CATEGORY].update(
        reason=leaf("price", "Plan cost more than the one feature used."),
        current_price=leaf(subjective="599 a month"),
        acceptable_price=leaf(subjective="under 250"),
        competitor=leaf(subjective="Duolingo"),
    )
    r = record_from_extracted(data)
    assert r.price.acceptable_price == "under 250"
    assert r.price.competitor == "Duolingo"
    assert r.bug is None


def test_reason_not_stated_is_not_actionable():
    data = bug_call()
    data[CATEGORY]["reason_stated"] = leaf("no")
    assert not record_from_extracted(data).is_actionable


def test_unknown_option_and_bad_confidence_degrade_gracefully():
    data = bug_call()
    data[CATEGORY]["reason"] = leaf("Something Bolna Made Up", confidence="high")
    data[CATEGORY]["severity"] = leaf(None)
    r = record_from_extracted(data)
    assert r.reason is ChurnReason.UNCLEAR
    assert r.reason_confidence.score == 0.0
    assert r.severity is Severity.UNCLEAR


def test_empty_payload_gives_an_inert_record():
    r = record_from_extracted({})
    assert r.reason is ChurnReason.UNCLEAR
    assert r.return_likelihood is ReturnLikelihood.UNCLEAR
    assert r.interview_quality == 0.0
    assert not r.is_actionable and not r.is_save_opportunity


def test_renamed_category_is_still_found():
    data = {"Something Else": bug_call()[CATEGORY]}
    assert record_from_extracted(data).reason is ChurnReason.BUG


def test_option_values_are_case_insensitive():
    data = bug_call()
    data[CATEGORY]["reason"] = leaf("BUG")
    data[CATEGORY]["reason_stated"] = leaf("Yes")
    r = record_from_extracted(data)
    assert r.reason is ChurnReason.BUG and r.reason_confidence.stated


def test_names_are_unique():
    names = [d["name"] for d in DISPOSITIONS]
    assert len(names) == len(set(names))


def test_every_disposition_meets_bolna_create_rules():
    for d in payloads():
        assert d["is_subjective"] or d.get("is_objective"), d["name"]
        if d.get("is_objective"):
            assert d["objective_options"], d["name"]
            for opt in d["objective_options"]:
                assert opt["value"] and opt["condition"], d["name"]
        assert d["category"] == CATEGORY and d["model"]


def test_mapping_reads_every_disposition_and_nothing_else():
    read = set(re.findall(r'data, "([a-z_]+)"', MAPPING_SOURCE)) | {"verbatim"}
    defined = {d["name"] for d in DISPOSITIONS}
    assert read == defined


def test_sentence_fields_keep_their_punctuation():
    """Sentence-shaped answers must not go through the full-stop trimmer.

    Routing one of these through `_text` strips the final stop of a real
    sentence, which looks like a truncated string on the dashboard.
    """
    sentence_fields = {"summary", "return_condition", "bug_steps"}
    for field in sentence_fields:
        assert f'_prose(data, "{field}")' in MAPPING_SOURCE, field
        assert f'_text(data, "{field}")' not in MAPPING_SOURCE, field


def test_option_values_match_the_record_enums():
    by_name = {d["name"]: d for d in DISPOSITIONS}
    for name, enum in (
        ("reason", ChurnReason),
        ("severity", Severity),
        ("return_likelihood", ReturnLikelihood),
    ):
        values = {o["value"] for o in by_name[name]["objective_options"]}
        assert values == {e.value for e in enum}, name
