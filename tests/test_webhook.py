"""Offline tests for the webhook and store: no network, no Bolna account.

Bolna does not publish the webhook's field names, so the payloads here are
built from the documented execution shape plus plausible variants. When a real
webhook arrives, paste it in as a test case before narrowing `payload.py`.
"""

import json

import pytest

from meoww.bolna import payload as P
from meoww.store import CallStore
from meoww.webhook import create_app
from tests.test_bolna import bug_call

TRANSCRIPT = (
    "Agent: What made you stop using it?\n"
    "User: It crashed every single time I tried to upload my photos in bulk.\n"
    "Agent: Which phone?\n"
    "User: Redmi Note 11, on Android.\n"
)


@pytest.fixture
def store(tmp_path):
    return CallStore(tmp_path / "calls.jsonl")


@pytest.fixture
def client(store):
    app = create_app(store=store)
    app.config.update(TESTING=True, SECRET=None)
    return app.test_client()


def webhook_body(**overrides):
    body = {
        "execution_id": "exec-1",
        "status": "completed",
        "transcript": TRANSCRIPT,
        "extracted_data": bug_call(),
        "recording_url": "https://example.com/r.mp3",
        "to_number": "+919000000000",
        "conversation_duration": 96.0,
    }
    body.update(overrides)
    return body


def test_reads_the_documented_shape():
    body = webhook_body()
    assert P.execution_id(body) == "exec-1"
    assert P.status(body) == "completed"
    assert P.is_terminal(body) and P.was_answered(body)
    assert P.duration_seconds(body) == 96.0
    assert "Redmi" in P.transcript(body)


def test_reads_alternative_field_names():
    body = {"id": "exec-9", "call_status": "ENDED", "transcription": TRANSCRIPT,
            "extractedData": bug_call(), "duration": "42"}
    assert P.execution_id(body) == "exec-9"
    assert P.was_answered(body)
    assert P.duration_seconds(body) == 42.0
    assert P.extracted_data(body)


def test_reads_nested_payload():
    body = {"event": "call.ended", "data": webhook_body()}
    assert P.execution_id(body) == "exec-1"
    assert P.extracted_data(body)


def test_turn_list_transcript_is_flattened():
    body = webhook_body(transcript=[
        {"role": "assistant", "text": "Why did you stop?"},
        {"role": "user", "text": "It kept crashing."},
    ])
    assert P.transcript(body) == "AGENT: Why did you stop?\nUSER: It kept crashing."


def test_unanswered_statuses_are_terminal_but_not_answered():
    for status in ("no-answer", "busy", "failed"):
        body = webhook_body(status=status)
        assert P.is_terminal(body) and not P.was_answered(body)


def test_completed_call_is_stored_with_a_record(client, store):
    resp = client.post("/webhook/bolna", json=webhook_body())
    assert resp.status_code == 200 and resp.json["has_record"]
    row = store.get("exec-1")
    assert row["record"]["reason"] == "bug"
    assert row["record"]["bug"]["device"] == "Redmi Note 11"
    assert row["duration_seconds"] == 96.0
    assert row["recording_url"].endswith("r.mp3")


def test_non_terminal_status_is_ignored(client, store):
    resp = client.post("/webhook/bolna", json=webhook_body(status="in-progress"))
    assert resp.status_code == 200 and resp.json["skipped"]
    assert store.all() == []


def test_duplicate_webhook_is_not_stored_twice(client, store):
    client.post("/webhook/bolna", json=webhook_body())
    resp = client.post("/webhook/bolna", json=webhook_body())
    assert resp.json["skipped"] == "already stored"
    assert len(store.all()) == 1


def test_unanswered_call_is_stored_without_a_record(client, store):
    resp = client.post("/webhook/bolna", json=webhook_body(
        status="no-answer", transcript="", extracted_data={}))
    assert resp.status_code == 200 and not resp.json["has_record"]
    row = store.get("exec-1")
    assert row["record"] is None and "not answered" in row["note"]


def test_short_call_is_stored_without_a_record(client, store):
    resp = client.post("/webhook/bolna", json=webhook_body(
        transcript="Agent: Hi?\nUser: No thanks.\n", extracted_data={}))
    assert not resp.json["has_record"]
    assert "too little" in store.get("exec-1")["note"]


def test_malformed_extraction_does_not_drop_the_call(client, store):
    resp = client.post("/webhook/bolna", json=webhook_body(
        extracted_data={"Meoww": {"reason": "not-an-object"}}))
    assert resp.status_code == 200
    row = store.get("exec-1")
    assert row is not None


def test_payload_without_an_id_is_rejected(client, store):
    resp = client.post("/webhook/bolna", json={"status": "completed"})
    assert resp.status_code == 400
    assert store.all() == []


def test_non_json_body_is_rejected(client):
    assert client.post("/webhook/bolna", data="hello").status_code == 400


def test_secret_is_enforced_when_set(store):
    app = create_app(store=store)
    app.config.update(TESTING=True, SECRET="s3cret")
    c = app.test_client()
    assert c.post("/webhook/bolna", json=webhook_body()).status_code == 403
    assert c.post("/webhook/bolna?secret=s3cret", json=webhook_body()).status_code == 200


def test_calls_and_stats_endpoints(client):
    client.post("/webhook/bolna", json=webhook_body())
    client.post("/webhook/bolna", json=webhook_body(
        execution_id="exec-2", status="no-answer", transcript="", extracted_data={}))

    assert len(client.get("/calls").json) == 2
    assert client.get("/calls/exec-1").json["execution_id"] == "exec-1"
    assert client.get("/calls/nope").status_code == 404

    stats = client.get("/stats").json
    assert stats["calls"] == 2
    assert stats["with_record"] == 1
    assert stats["actionable"] == 1
    assert stats["save_opportunities"] == 1
    assert stats["reasons_ranked"] == [["bug", 1]]


def test_healthz(client):
    assert client.get("/healthz").json["ok"] is True


def test_store_survives_a_corrupt_line(store):
    store.add("ok-1", None, note="fine")
    with store.path.open("a", encoding="utf-8") as f:
        f.write("{not json\n")
    assert [r["execution_id"] for r in store.all()] == ["ok-1"]


def test_resent_webhook_overwrites_the_earlier_row(store):
    store.add("exec-1", None, note="first")
    store.add("exec-1", None, note="second")
    rows = store.all()
    assert len(rows) == 1 and rows[0]["note"] == "second"


def test_median_duration(store):
    for i, seconds in enumerate([60, 90, 120]):
        store.add(f"e{i}", None, duration_seconds=seconds)
    assert store.stats()["median_duration_seconds"] == 90


def test_stats_on_an_empty_store(store):
    s = store.stats()
    assert s["calls"] == 0 and s["median_duration_seconds"] is None


def test_store_path_follows_the_environment_at_call_time(tmp_path, monkeypatch):
    """MEOWW_STORE must apply even when set after import, as under gunicorn."""
    target = tmp_path / "deployed.jsonl"
    monkeypatch.setenv("MEOWW_STORE", str(target))
    assert CallStore().path == target
