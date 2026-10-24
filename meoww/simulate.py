"""Run transcripts through the real pipeline, without a phone call.

    python -m meoww.simulate transcripts/            # one file or a folder
    python -m meoww.simulate transcripts/ --clear    # replace earlier simulated rows

Every row this writes is marked `simulated: true` and the dashboard says so on
screen. The extraction is genuine - the transcript goes to Bolna's live
extraction endpoint and comes back through the same mapper a real call uses.
What is missing is only the telephony: nobody dialled, nobody spoke.

Never present these rows as real calls.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from .bolna.client import BolnaClient, BolnaError
from .bolna.mapping import record_from_extracted
from .bolna_cli import _agent_id
from .extraction.extractor import MIN_USER_WORDS
from .extraction.transcript import Speaker, parse_plain
from .store import CallStore

WORDS_PER_SECOND = 2.5
GREETING_SECONDS = 8


def _estimated_duration(transcript_text: str) -> float:
    words = len(transcript_text.split())
    return round(GREETING_SECONDS + words / WORDS_PER_SECOND, 1)


def simulate_file(
    path: Path,
    client: BolnaClient,
    store: CallStore,
    agent_id: str,
) -> Optional[dict]:
    """Put one transcript through extraction and store the result."""
    text = path.read_text(encoding="utf-8")
    transcript = parse_plain(path.stem, text)
    execution_id = f"sim-{path.stem}"

    if not transcript.turns:
        print(f"-- {path.stem}: no speaker turns found, skipped")
        return None

    common = dict(
        transcript=transcript.render(),
        duration_seconds=_estimated_duration(text),
        status="completed",
        simulated=True,
    )

    if transcript.user_word_count < MIN_USER_WORDS:
        row = store.add(
            execution_id, None,
            note=f"user said too little ({transcript.user_word_count} words)",
            **common,
        )
        print(f"-- {path.stem}: stored without a record, user barely spoke")
        return row

    try:
        extracted = client.test_dispositions(agent_id, text)
    except (BolnaError, httpx.HTTPError) as e:
        print(f"!! {path.stem}: {type(e).__name__}: {e}", file=sys.stderr)
        return None

    record = record_from_extracted(extracted) if extracted else None
    row = store.add(
        execution_id, record,
        note=None if record else "no extracted_data from Bolna",
        raw_extracted=extracted or None,
        **common,
    )

    flags = [
        name for name, on in (
            ("ACTIONABLE", record.is_actionable if record else False),
            ("SAVE", record.is_save_opportunity if record else False),
            ("FOLLOW-UP", record.followup_needed if record else False),
        ) if on
    ]
    reason = record.reason.value if record else "no record"
    print(f"   {path.stem}: {reason} [{' '.join(flags) or 'context only'}]")
    return row


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="A .txt transcript or a folder of them")
    parser.add_argument("--clear", action="store_true",
                        help="Remove previously simulated rows first")
    parser.add_argument("--resume", action="store_true",
                        help="Skip transcripts already stored, for retrying a failed run")
    args = parser.parse_args()

    files = sorted(args.path.glob("*.txt")) if args.path.is_dir() else [args.path]
    if not files:
        print(f"No .txt transcripts in {args.path}", file=sys.stderr)
        return 1

    store = CallStore()
    if args.clear:
        removed = store.drop_simulated()
        print(f"Removed {removed} simulated row(s).")

    try:
        client, agent_id = BolnaClient(), _agent_id()
    except BolnaError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.resume:
        before = len(files)
        files = [f for f in files if not store.has(f"sim-{f.stem}")]
        skipped = before - len(files)
        if skipped:
            print(f"Skipping {skipped} already stored.")
        if not files:
            print("Nothing left to simulate.")
            return 0

    print(f"Simulating {len(files)} call(s) through the live extraction:")
    stored = sum(
        1 for f in files
        if simulate_file(f, client, store, agent_id) is not None
    )

    print(f"\nStored {stored} simulated call(s) in {store.path}.")
    print("The dashboard marks these as simulated. Do not present them as real calls.")
    return 0 if stored else 1


if __name__ == "__main__":
    sys.exit(main())
