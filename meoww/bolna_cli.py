"""Set up and test Meoww's Bolna extractions.

    python -m meoww.bolna_cli setup                 # create the questions on your agent
    python -m meoww.bolna_cli sync                  # push edited questions to the agent
    python -m meoww.bolna_cli test transcripts/        # run them on transcripts, no calls made
    python -m meoww.bolna_cli execution <id>        # read a real finished call

Needs BOLNA_API_KEY and BOLNA_AGENT_ID in .env.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, TextIO

from dotenv import load_dotenv

from .bolna.client import BolnaClient, BolnaError
from .bolna.dispositions import payloads
from .bolna.mapping import record_from_extracted
from .extraction.extractor import MIN_USER_WORDS
from .extraction.models import ChurnRecord
from .extraction.transcript import parse_plain


def _agent_id() -> str:
    agent_id = os.environ.get("BOLNA_AGENT_ID")
    if not agent_id:
        raise BolnaError(
            "BOLNA_AGENT_ID is not set. Copy your agent's ID from the Bolna "
            "dashboard into .env."
        )
    return agent_id


def _show(call_id: str, record: ChurnRecord, out: Optional[TextIO]) -> None:
    flags = [
        name
        for name, on in (
            ("ACTIONABLE", record.is_actionable),
            ("SAVE", record.is_save_opportunity),
            ("FOLLOW-UP", record.followup_needed),
        )
        if on
    ]
    print(f"\n== {call_id}  [{' '.join(flags) or 'context only'}]")
    print(record.model_dump_json(indent=2, exclude_none=True))
    if out:
        row = {"call_id": call_id, **record.model_dump(mode="json")}
        out.write(json.dumps(row, ensure_ascii=False) + "\n")


def cmd_setup(client: BolnaClient, args: argparse.Namespace) -> int:
    agent_id = _agent_id()
    existing = {d.get("name") for d in client.list_dispositions(agent_id)}
    missing = [d for d in payloads() if d["name"] not in existing]

    if not missing:
        print(f"All {len(payloads())} extractions already exist on agent {agent_id}.")
        return 0

    ids = client.bulk_create_dispositions(agent_id, missing)
    print(f"Created {len(ids)} extractions on agent {agent_id}:")
    for d in missing:
        print(f"  + {d['name']}")
    skipped = len(payloads()) - len(missing)
    if skipped:
        print(f"Skipped {skipped} that already existed.")
    return 0


def cmd_sync(client: BolnaClient, args: argparse.Namespace) -> int:
    """Push edits in dispositions.py to the live agent.

    `setup` only creates what is missing, so a reworded question in this repo
    would otherwise never reach Bolna. This updates every disposition that
    already exists and creates any that do not.
    """
    agent_id = _agent_id()
    live = {d["name"]: d for d in client.list_dispositions(agent_id) if d.get("name")}

    updated, created, failed = [], [], []
    for payload in payloads():
        name = payload["name"]
        existing = live.get(name)
        if existing is None:
            created.append(payload)
            continue
        fields = {k: v for k, v in payload.items() if k != "category"}
        try:
            client.update_disposition(existing["id"], fields)
            updated.append(name)
        except BolnaError as e:
            failed.append((name, e))

    if created:
        client.bulk_create_dispositions(agent_id, created)

    print(f"Agent {agent_id}:")
    print(f"  updated {len(updated)}")
    if created:
        print(f"  created {len(created)}: {', '.join(d['name'] for d in created)}")
    for name, error in failed:
        print(f"  !! {name}: {error}", file=sys.stderr)
    if updated:
        print("\nRe-run the test command to see the effect.")
    return 1 if failed else 0


def cmd_test(client: BolnaClient, args: argparse.Namespace) -> int:
    agent_id = _agent_id()
    path: Path = args.path
    files = sorted(path.glob("*.txt")) if path.is_dir() else [path]
    if not files:
        print(f"No .txt transcripts in {path}", file=sys.stderr)
        return 1

    out = args.out.open("a", encoding="utf-8") if args.out else None
    failed = 0
    try:
        for f in files:
            text = f.read_text(encoding="utf-8")
            if parse_plain(f.stem, text).user_word_count < MIN_USER_WORDS:
                print(f"-- {f.stem}: skipped, user barely spoke")
                continue
            try:
                data = client.test_dispositions(agent_id, text)
            except BolnaError as e:
                print(f"!! {f.stem}: {e}", file=sys.stderr)
                failed += 1
                continue
            if args.raw:
                print(f"\n== {f.stem} (raw)")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            _show(f.stem, record_from_extracted(data), out)
    finally:
        if out:
            out.close()
    return 1 if failed else 0


def cmd_execution(client: BolnaClient, args: argparse.Namespace) -> int:
    execution = client.get_execution(args.execution_id)
    data = execution.get("extracted_data") or {}
    if not data:
        status = execution.get("status", "unknown")
        print(f"No extracted_data yet (status: {status}). Wait for 'completed'.")
        return 1
    _show(args.execution_id, record_from_extracted(data), None)
    return 0


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Create the extraction questions on your agent")
    sub.add_parser("sync", help="Push edited questions to the agent (update + create)")

    test = sub.add_parser("test", help="Run extractions on transcript files")
    test.add_argument("path", type=Path, help="A .txt transcript or a folder of them")
    test.add_argument("--out", type=Path, help="Append records to this .jsonl file")
    test.add_argument("--raw", action="store_true", help="Also print Bolna's raw output")

    execution = sub.add_parser("execution", help="Read a finished call")
    execution.add_argument("execution_id")

    args = parser.parse_args()
    commands = {
        "setup": cmd_setup,
        "sync": cmd_sync,
        "test": cmd_test,
        "execution": cmd_execution,
    }
    try:
        return commands[args.command](BolnaClient(), args)
    except BolnaError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
