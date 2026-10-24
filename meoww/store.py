"""Where finished calls are kept.

A JSONL file, one call per line, appended in order. Not a database: for a
buildathon the whole point is that the data is readable with `cat` and
survives a crash without a migration. Swapping this for Postgres later means
replacing one module.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from .extraction.models import ChurnRecord

FALLBACK_PATH = "data/calls.jsonl"


def default_path() -> Path:
    """Where calls are stored.

    Read per call rather than at import, so MEOWW_STORE still applies when
    the environment is loaded after this module (gunicorn, tests).
    """
    return Path(os.environ.get("MEOWW_STORE", FALLBACK_PATH))


class CallStore:
    """Append-only store of calls, keyed by execution id.

    Writes are serialised with a lock and each append is flushed, so a reader
    in another process never sees half a line.
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def add(
        self,
        execution_id: str,
        record: Optional[ChurnRecord],
        *,
        transcript: str = "",
        recording_url: Optional[str] = None,
        phone_number: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        status: str = "completed",
        note: Optional[str] = None,
        raw_extracted: Optional[Dict[str, Any]] = None,
        simulated: bool = False,
    ) -> Dict[str, Any]:
        """Append one call. A call with no record is still stored.

        A call that produced no usable record (too short, nobody answered) is
        kept deliberately: the denominator matters. "12 of 50 users named a
        return condition" is only honest if the 50 includes the failures.
        """
        row = {
            "execution_id": execution_id,
            "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "simulated": simulated,
            "status": status,
            "phone_number": phone_number,
            "duration_seconds": duration_seconds,
            "recording_url": recording_url,
            "transcript": transcript,
            "note": note,
            "record": record.model_dump(mode="json") if record else None,
            "raw_extracted": raw_extracted,
        }
        line = json.dumps(row, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        return row

    def all(self) -> List[Dict[str, Any]]:
        """Every call, newest first. A corrupt line is skipped, not fatal."""
        if not self.path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        deduped: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            deduped[row.get("execution_id") or id(row)] = row
        def rank(row: Dict[str, Any]) -> tuple:
            record = _as_record(row)
            if record is None:
                return (0, 0, 0.0, row.get("received_at") or "")
            return (
                1,
                2 if record.is_save_opportunity else 1 if record.is_actionable else 0,
                record.interview_quality,
                row.get("received_at") or "",
            )

        return sorted(deduped.values(), key=rank, reverse=True)

    def get(self, execution_id: str) -> Optional[Dict[str, Any]]:
        for row in self.all():
            if row.get("execution_id") == execution_id:
                return row
        return None

    def has(self, execution_id: str) -> bool:
        return self.get(execution_id) is not None

    def drop_simulated(self) -> int:
        """Remove every simulated row, keeping real calls. Returns how many went.

        Rewrites the file through a temporary one so an interrupted run cannot
        leave the store half-written.
        """
        rows = self.all()
        keep = [r for r in rows if not r.get("simulated")]
        removed = len(rows) - len(keep)
        if not removed:
            return 0

        keep.sort(key=lambda r: r.get("received_at") or "")
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                for row in keep:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
            tmp.replace(self.path)
        return removed

    def stats(self) -> Dict[str, Any]:
        """The numbers the pitch deck needs, computed from real calls only."""
        rows = self.all()
        records = [r for r in (_as_record(row) for row in rows) if r is not None]

        actionable = [r for r in records if r.is_actionable]
        saves = [r for r in records if r.is_save_opportunity]
        durations = [r["duration_seconds"] for r in rows if r.get("duration_seconds")]

        reasons: Dict[str, int] = {}
        for r in actionable:
            reasons[r.reason.value] = reasons.get(r.reason.value, 0) + 1

        simulated = sum(1 for r in rows if r.get("simulated"))
        return {
            "calls": len(rows),
            "simulated": simulated,
            "real": len(rows) - simulated,
            "any_simulated": simulated > 0,
            "all_simulated": simulated == len(rows) and simulated > 0,
            "with_record": len(records),
            "actionable": len(actionable),
            "save_opportunities": len(saves),
            "followup_needed": sum(1 for r in records if r.followup_needed),
            "median_duration_seconds": _median(durations),
            "reasons_ranked": sorted(reasons.items(), key=lambda kv: kv[1], reverse=True),
        }


def _as_record(row: Dict[str, Any]) -> Optional[ChurnRecord]:
    """A row's record, or None if there is none or it no longer validates.

    A row written by an earlier version of the schema must not break the
    aggregate: a single bad line would otherwise take the dashboard down.
    """
    data = row.get("record")
    if not data:
        return None
    try:
        return ChurnRecord(**data)
    except ValidationError:
        return None


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
