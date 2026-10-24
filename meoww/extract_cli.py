"""Run the extractor over transcript files and print the records.

    python -m meoww.extract_cli transcripts/
    python -m meoww.extract_cli transcripts/bug_crash.txt --out records.jsonl

This calls the real Claude API and costs money - a few cents per transcript.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from .extraction.extractor import ExtractionError, TranscriptTooShort, extract_record
from .extraction.transcript import parse_plain


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="A .txt transcript or a folder of them")
    parser.add_argument("--out", type=Path, help="Append records to this .jsonl file")
    args = parser.parse_args()

    files = sorted(args.path.glob("*.txt")) if args.path.is_dir() else [args.path]
    if not files:
        print(f"No .txt transcripts in {args.path}", file=sys.stderr)
        return 1

    client = anthropic.Anthropic()
    out = args.out.open("a", encoding="utf-8") if args.out else None
    failed = 0

    for f in files:
        transcript = parse_plain(f.stem, f.read_text(encoding="utf-8"))
        try:
            record = extract_record(transcript, client=client)
        except TranscriptTooShort as e:
            print(f"-- {f.stem}: skipped ({e})")
            continue
        except (ExtractionError, anthropic.APIError) as e:
            print(f"!! {f.stem}: {e}", file=sys.stderr)
            failed += 1
            continue

        flags = []
        if record.is_actionable:
            flags.append("ACTIONABLE")
        if record.is_save_opportunity:
            flags.append("SAVE")
        if record.followup_needed:
            flags.append("FOLLOW-UP")
        print(f"\n== {f.stem}  [{' '.join(flags) or 'context only'}]")
        print(record.model_dump_json(indent=2, exclude_none=True))

        if out:
            row = {"call_id": transcript.call_id, **record.model_dump(mode="json")}
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    if out:
        out.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
