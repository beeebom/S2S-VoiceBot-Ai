"""Catches finished calls from Bolna and turns each into a record.

    python -m meoww.webhook                 # listen on :8000
    python -m meoww.webhook --raw           # also log each payload in full

Point your Bolna agent's webhook at http://<public-host>/webhook/bolna.
Locally, expose it with a tunnel (ngrok, cloudflared) and use that URL.

Endpoints:
    POST /webhook/bolna     Bolna posts here when a call ends
    GET  /calls             Every stored call, newest first
    GET  /calls/<id>        One call
    GET  /stats             The aggregate numbers
    GET  /healthz           Liveness
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError

from .bolna import payload as P
from .bolna.client import BolnaClient, BolnaError
from .bolna.mapping import record_from_extracted
from .extraction.extractor import MIN_USER_WORDS
from .extraction.models import ChurnRecord
from .extraction.transcript import parse_plain
from .store import CallStore

log = logging.getLogger("meoww.webhook")


def create_app(store: Optional[CallStore] = None, log_raw: bool = False) -> Flask:
    """Build the Flask app.

    Called directly by gunicorn in deployment, so the environment is loaded
    here rather than only in main().
    """
    load_dotenv()
    app = Flask(__name__)
    app.config["STORE"] = store or CallStore()
    app.config["LOG_RAW"] = log_raw
    app.config["SECRET"] = os.environ.get("MEOWW_WEBHOOK_SECRET")

    @app.get("/")
    def dashboard():
        store: CallStore = app.config["STORE"]
        return render_template(
            "dashboard.html",
            calls=[_for_display(row) for row in store.all()],
            stats=store.stats(),
            median=_mmss(store.stats()["median_duration_seconds"]),
        )

    @app.get("/healthz")
    def healthz():
        return jsonify(ok=True, calls=len(app.config["STORE"].all()))

    @app.post("/webhook/bolna")
    def bolna_webhook():
        secret = app.config["SECRET"]
        if secret and request.args.get("secret") != secret:
            log.warning("rejected webhook with bad or missing secret")
            return jsonify(error="forbidden"), 403

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="expected a JSON object"), 400

        if app.config["LOG_RAW"]:
            log.info("payload: %s", json.dumps(data, ensure_ascii=False)[:4000])
        log.info("call: %s", " ".join(P.summarise(data)))

        execution_id = P.execution_id(data)
        if not execution_id:
            return jsonify(error="no execution id in payload"), 400

        if not P.is_terminal(data):
            return jsonify(ok=True, skipped="not a terminal status",
                           status=P.status(data)), 200

        store: CallStore = app.config["STORE"]
        if store.has(execution_id):
            return jsonify(ok=True, skipped="already stored", execution_id=execution_id), 200

        row = _process(store, data, execution_id)
        return jsonify(
            ok=True,
            execution_id=execution_id,
            stored=True,
            has_record=row.get("record") is not None,
            note=row.get("note"),
        ), 200

    @app.get("/calls")
    def calls():
        return jsonify(app.config["STORE"].all())

    @app.get("/calls/<execution_id>")
    def call(execution_id: str):
        row = app.config["STORE"].get(execution_id)
        return (jsonify(row), 200) if row else (jsonify(error="not found"), 404)

    @app.get("/stats")
    def stats():
        return jsonify(app.config["STORE"].stats())

    return app


def _process(store: CallStore, data: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
    """Turn one terminal webhook into a stored row.

    A call is always stored, with or without a record: the denominator matters
    for any claim about save rates.
    """
    extracted = P.extracted_data(data)
    transcript_text = P.transcript(data)

    if not extracted or not transcript_text:
        fetched = _fetch_execution(execution_id)
        if fetched:
            extracted = extracted or P.extracted_data(fetched)
            transcript_text = transcript_text or P.transcript(fetched)
            data = {**fetched, **data}

    common = dict(
        transcript=transcript_text,
        recording_url=P.recording_url(data),
        phone_number=P.phone_number(data),
        duration_seconds=P.duration_seconds(data),
        status=P.status(data),
        raw_extracted=extracted or None,
    )

    record, note = _build_record(data, extracted, transcript_text)
    row = store.add(execution_id, record, note=note, **common)
    log.info("stored %s (record=%s, note=%s)", execution_id, record is not None, note)
    return row


def _build_record(
    data: Dict[str, Any], extracted: Dict[str, Any], transcript_text: str
) -> Tuple[Optional[Any], Optional[str]]:
    """The record for this call, or None with a reason why there is none."""
    if not P.was_answered(data):
        return None, f"not answered ({P.status(data)})"

    words = parse_plain("x", transcript_text).user_word_count if transcript_text else 0
    if words < MIN_USER_WORDS:
        return None, f"user said too little ({words} words)"

    if not extracted:
        return None, "no extracted_data from Bolna"

    try:
        return record_from_extracted(extracted), None
    except Exception as e:
        log.exception("mapping failed")
        return None, f"mapping failed: {type(e).__name__}: {e}"


def _for_display(row: Dict[str, Any]) -> Dict[str, Any]:
    """One stored call, with the bits the dashboard needs precomputed.

    The actionable/save rules live on ChurnRecord, so they are read from there
    rather than reimplemented in the template - the dashboard and the pitch
    numbers must never disagree about what counts.
    """
    flags = {"actionable": False, "save": False}
    record_data = row.get("record")

    if record_data:
        try:
            record = ChurnRecord(**record_data)
            flags = {
                "actionable": record.is_actionable,
                "save": record.is_save_opportunity,
            }
            record_data = record.model_dump(mode="json")
        except ValidationError:
            log.warning("unreadable record for %s", row.get("execution_id"))
            record_data = None
            row = {**row, "note": row.get("note") or "record not readable"}

    return {
        **row,
        "record": record_data,
        "flags": flags,
        "when": _when(row.get("received_at")),
    }


def _when(timestamp: Optional[str]) -> str:
    """'14:32 20 Oct', or the raw value if it will not parse."""
    if not timestamp:
        return ""
    try:
        from datetime import datetime

        return datetime.fromisoformat(timestamp).strftime("%H:%M %d %b")
    except ValueError:
        return timestamp


def _mmss(seconds: Optional[float]) -> str:
    if not seconds:
        return "--"
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _fetch_execution(execution_id: str) -> Optional[Dict[str, Any]]:
    try:
        return BolnaClient().get_execution(execution_id)
    except BolnaError as e:
        log.warning("could not fetch execution %s: %s", execution_id, e)
        return None


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--raw", action="store_true", help="Log each payload in full")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    app = create_app(log_raw=args.raw)
    if not app.config["SECRET"]:
        log.warning("MEOWW_WEBHOOK_SECRET is not set - the endpoint is unauthenticated")

    log.info("listening on %s:%s - webhook path /webhook/bolna", args.host, args.port)
    app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
