"""Offline tests for the dashboard page."""

import pytest

from meoww.store import CallStore
from meoww.webhook import _mmss, _when, create_app
from tests.test_bolna import bug_call
from tests.test_webhook import TRANSCRIPT, webhook_body


@pytest.fixture
def client(tmp_path):
    app = create_app(store=CallStore(tmp_path / "calls.jsonl"))
    app.config.update(TESTING=True, SECRET=None)
    return app.test_client()


def page(client) -> str:
    resp = client.get("/")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_empty_dashboard_explains_what_to_do(client):
    html = page(client)
    assert "No calls yet" in html
    assert "/webhook/bolna" in html


def test_call_appears_with_its_record_and_flags(client):
    client.post("/webhook/bolna", json=webhook_body())
    html = page(client)
    assert "Redmi Note 11" in html
    assert "actionable" in html and "save" in html
    assert "user stated" in html
    assert "It crashed every" in html
    assert "Which phone?" in html


def test_price_call_shows_the_price_fields(client):
    data = bug_call()
    data["Meoww"]["reason"] = {"objective": "price", "subjective": "Too dear.",
                                "confidence": 0.9, "reasoning_objective": "Cost."}
    data["Meoww"]["current_price"] = {"subjective": "599"}
    data["Meoww"]["acceptable_price"] = {"subjective": "249"}
    client.post("/webhook/bolna", json=webhook_body(extracted_data=data))
    html = page(client)
    assert "Would pay" in html and "249" in html


def test_unanswered_call_is_shown_as_a_failure_not_hidden(client):
    client.post("/webhook/bolna", json=webhook_body(
        status="no-answer", transcript="", extracted_data={}))
    html = page(client)
    assert "no record" in html
    assert "not answered" in html


def test_inferred_reason_is_marked_as_such(client):
    data = bug_call()
    data["Meoww"]["reason_stated"] = {"objective": "no", "confidence": 0.9}
    client.post("/webhook/bolna", json=webhook_body(extracted_data=data))
    html = page(client)
    assert "inferred" in html
    assert ">actionable<" not in html


def test_themes_chart_counts_actionable_calls_only(client):
    client.post("/webhook/bolna", json=webhook_body())
    data = bug_call()
    data["Meoww"]["reason_stated"] = {"objective": "no", "confidence": 0.9}
    client.post("/webhook/bolna", json=webhook_body(execution_id="e2", extracted_data=data))
    html = page(client)
    assert "What is driving churn" in html
    assert html.count("<span class=\"n\">1</span>") == 1


def test_a_record_from_an_older_schema_still_renders(client, tmp_path):
    app = create_app(store=CallStore(tmp_path / "old.jsonl"))
    app.config.update(TESTING=True, SECRET=None)
    app.config["STORE"].path.write_text(
        '{"execution_id":"old-1","received_at":"2026-10-20T10:00:00+00:00",'
        '"status":"completed","record":{"reason":"bug"},"transcript":"x"}\n',
        encoding="utf-8",
    )
    resp = app.test_client().get("/")
    assert resp.status_code == 200


@pytest.mark.parametrize("seconds,expected", [
    (None, "--"), (0, "--"), (9, "0:09"), (96, "1:36"), (600, "10:00"),
])
def test_mmss(seconds, expected):
    assert _mmss(seconds) == expected


def test_when_formats_and_falls_back():
    assert _when("2026-10-20T14:32:00+00:00") == "14:32 20 Oct"
    assert _when("not a date") == "not a date"
    assert _when(None) == ""


def test_simulated_rows_are_announced(client):
    client.application.config["STORE"].add(
        "sim-1", None, note="x", simulated=True, duration_seconds=60)
    html = page(client)
    assert "Telephony is not connected" in html
    assert "What did not happen is" in html
    assert "all simulated" in html
    assert "flag simulated" in html


def test_mixed_real_and_simulated_says_how_many(client):
    store = client.application.config["STORE"]
    store.add("real-1", None, note="x", duration_seconds=60)
    store.add("sim-1", None, note="x", simulated=True, duration_seconds=60)
    html = page(client)
    assert "Contains simulated calls" in html
    assert "1 real call" in html and "1 simulated" in html


def test_no_banner_when_every_call_is_real(client):
    client.post("/webhook/bolna", json=webhook_body())
    html = page(client)
    assert "Telephony is not connected" not in html
    assert "flag simulated" not in html


def test_strongest_calls_are_listed_first(client):
    """A save opportunity should outrank a weak call and a failed one."""
    store = client.application.config["STORE"]
    store.add("weak", None, note="nobody answered")
    client.post("/webhook/bolna", json=webhook_body(execution_id="strong"))

    order = [r["execution_id"] for r in store.all()]
    assert order.index("strong") < order.index("weak")


def test_webhook_calls_are_never_marked_simulated(client):
    client.post("/webhook/bolna", json=webhook_body())
    assert client.application.config["STORE"].get("exec-1")["simulated"] is False


def test_drop_simulated_keeps_real_calls(tmp_path):
    from meoww.store import CallStore
    store = CallStore(tmp_path / "c.jsonl")
    store.add("real-1", None, note="keep")
    store.add("sim-1", None, note="go", simulated=True)
    store.add("real-2", None, note="keep")
    assert store.drop_simulated() == 1
    assert sorted(r["execution_id"] for r in store.all()) == ["real-1", "real-2"]
    assert store.drop_simulated() == 0


def test_no_em_dashes_in_the_dashboard():
    """A standing instruction from the user: no em dashes anywhere in the UI."""
    from pathlib import Path
    html = Path("meoww/templates/dashboard.html").read_text(encoding="utf-8")
    assert "\u2014" not in html and "&mdash;" not in html
