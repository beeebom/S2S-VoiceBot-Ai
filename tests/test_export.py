"""Tests for the static site export."""

import re
from pathlib import Path

import pytest

from meoww.export import export
from meoww.store import CallStore
from tests.test_bolna import bug_call
from tests.test_webhook import TRANSCRIPT


@pytest.fixture
def site(tmp_path):
    store = CallStore(tmp_path / "calls.jsonl")
    from meoww.bolna.mapping import record_from_extracted
    store.add("c1", record_from_extracted(bug_call()), transcript=TRANSCRIPT,
              duration_seconds=96, simulated=True)
    store.add("c2", None, note="not answered", status="no-answer", simulated=True)
    out = tmp_path / "site"
    export(out, store_path=store.path)
    return out


def test_every_page_is_written(site):
    for name in ("index.html", "calls.html", "privacy.html", "terms.html", ".nojekyll"):
        assert (site / name).exists(), name


def test_landing_reports_the_real_figures(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert ">2<" in html          # both calls counted, including the failure
    assert "See 2 conversations" in html


def test_landing_links_resolve(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith(("http", "data:", "#")):
            continue
        assert (site / href).exists(), href


def test_calls_page_is_static(site):
    """The live app's refresh loop must not ship to a page that cannot update."""
    html = (site / "calls.html").read_text(encoding="utf-8")
    assert "location.reload" not in html
    assert "auto-refreshes" not in html
    assert "static copy" in html


def test_simulated_rows_stay_labelled_in_the_export(site):
    html = (site / "calls.html").read_text(encoding="utf-8")
    assert "Telephony is not connected" in html
    assert "flag simulated" in html


@pytest.mark.parametrize("page", ["index.html", "calls.html", "privacy.html", "terms.html"])
def test_no_em_dashes_anywhere(site, page):
    """A standing instruction from the user: no em dashes in the UI."""
    text = (site / page).read_text(encoding="utf-8")
    assert "\u2014" not in text and "&mdash;" not in text


def test_motion_is_opt_out(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in html


def test_page_is_readable_without_javascript(site):
    """Reveal-on-scroll must not hide content when scripts do not run."""
    html = (site / "index.html").read_text(encoding="utf-8")
    body = html.split("<body>", 1)[1]
    assert "Your users tell you nothing" in body
    assert "What is built, and what is not" in body
