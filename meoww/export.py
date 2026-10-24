"""Render the dashboard to static HTML for GitHub Pages.

    python -m meoww.export                 # writes to docs/
    python -m meoww.export --out site/

GitHub Pages serves files, not Python, so the live Flask app cannot run there.
This writes the same dashboard the app renders, as a snapshot, plus a landing
page that explains the project to someone arriving cold.

The exported page is read-only by nature: it cannot receive webhooks, and it
shows whatever was in the store when the export ran.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from .landing import landing_page
from .store import CallStore
from .webhook import create_app


def export(out_dir: Path, store_path: Path | None = None) -> dict:
    """Write the static site. Returns the stats it rendered."""
    store = CallStore(store_path) if store_path else CallStore()
    app = create_app(store=store)
    out_dir.mkdir(parents=True, exist_ok=True)

    with app.test_request_context():
        dashboard_html = app.view_functions["dashboard"]()

    generated = datetime.now(timezone.utc).strftime("%d %B %Y")
    stats = store.stats()

    (out_dir / "calls.html").write_text(
        _as_static(dashboard_html, generated), encoding="utf-8"
    )
    (out_dir / "index.html").write_text(
        landing_page(stats), encoding="utf-8"
    )
    (out_dir / "privacy.html").write_text(_legal_page("privacy", generated), encoding="utf-8")
    (out_dir / "terms.html").write_text(_legal_page("terms", generated), encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return stats


def _as_static(html: str, generated: str) -> str:
    """Strip the behaviour that only makes sense on the live app."""
    html = html.replace(
        "<span class=\"refresh\">auto-refreshes every 15s</span>",
        f"<a class=\"refresh\" href=\"index.html\">about this project</a>",
    )
    start = html.find("<script>")
    if start != -1:
        end = html.find("</script>", start)
        html = html[:start] + html[end + len("</script>"):]
    return html.replace(
        "</main>",
        f'<p class="generated">Snapshot generated {generated}. '
        f'The live app receives calls by webhook; this page is a static copy.</p>'
        "</main>"
        "<style>.generated{max-width:1080px;margin:0 auto;padding:0 20px 40px;"
        "font-size:13px;color:#6b7689}</style>",
    )


LEGAL_STYLE = """
  :root { --navy:#10213d; --ink:#1a2330; --body:#4a5568; --muted:#6b7689;
          --bg:#f4f2ed; --card:#fff; --line:#ddd8cc; --amber:#a8742a; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:16px/1.65 -apple-system,"Segoe UI",system-ui,sans-serif; }
  .wrap { max-width:720px; margin:0 auto; padding:0 24px; }
  header { background:var(--navy); color:#f4f2ed; padding:40px 0; }
  header a { color:#e8a33d; text-decoration:none; font-size:15px; font-weight:600; }
  h1 { font-size:30px; margin:16px 0 6px; font-weight:600; }
  header p { margin:0; color:#9fb0c8; font-size:14px; }
  main { padding:44px 0 56px; }
  h2 { font-size:18px; margin:32px 0 10px; font-weight:600; }
  h2:first-child { margin-top:0; }
  p, li { color:var(--body); margin:0 0 14px; }
  ul { padding-left:22px; }
  a { color:var(--amber); }
  footer { border-top:1px solid var(--line); padding:24px 0 48px;
           font-size:14px; color:var(--muted); }
"""

PRIVACY_BODY = """
<h2>What this site is</h2>
<p>This is a static project page for Meoww, a buildathon project. It is a
snapshot of a dashboard. It runs no analytics, sets no cookies, and has no
accounts, logins or forms.</p>

<h2>What it collects</h2>
<p>Nothing. The pages are plain HTML files served by GitHub Pages. GitHub may
log standard request information such as IP addresses when it serves them;
that is covered by
<a href="https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement">GitHub's privacy statement</a>,
not by this project.</p>

<h2>The conversations shown here</h2>
<p>The records on the conversations page were produced from written transcripts
authored for testing. They are not recordings of real people and contain no
personal data. No phone calls have been made by this project.</p>

<h2>If the software is run against real calls</h2>
<p>The source code, if deployed and connected to telephony, would process call
transcripts and store them. Anyone running it that way is the data controller
for those recordings and is responsible for consent, retention and lawful
basis. The project ships no hosted service and holds no data on anyone's
behalf.</p>

<h2>Contact</h2>
<p>Questions about this page can be raised as an issue on the
<a href="https://github.com/beeebom/S2S-VoiceBot-Ai">source repository</a>.</p>
"""

TERMS_BODY = """
<h2>What you are looking at</h2>
<p>Meoww is a project built for the Symphony Buildathon 2026. This site exists
to show what it does. It is not a commercial product, there is nothing to buy,
and no service is being offered or sold.</p>

<h2>No warranty</h2>
<p>The project and this page are provided as they are, without warranty of any
kind. Nothing here is a guarantee that the software will work for any
particular purpose.</p>

<h2>The source code</h2>
<p>The code is published on
<a href="https://github.com/beeebom/S2S-VoiceBot-Ai">GitHub</a>. Anyone running
it is responsible for how they use it, including obtaining consent before
calling anyone and complying with the telecoms and data protection rules that
apply to them.</p>

<h2>Figures on this site</h2>
<p>The counts shown come from running written transcripts through the
extraction pipeline. They describe that exercise and nothing else. They are not
customer results and should not be read as performance claims.</p>

<h2>Third parties</h2>
<p>The project is built on <a href="https://bolna.ai">Bolna</a>. Their terms
govern their platform. This project is not affiliated with or endorsed by
Bolna.</p>
"""


def _legal_page(kind: str, generated: str) -> str:
    """Render the privacy policy or the terms page."""
    title, body = {
        "privacy": ("Privacy", PRIVACY_BODY),
        "terms": ("Terms", TERMS_BODY),
    }[kind]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Meoww</title>
<style>{LEGAL_STYLE}</style>
</head>
<body>
<header><div class="wrap">
  <a href="index.html">Meoww</a>
  <h1>{title}</h1>
  <p>Last updated {generated}</p>
</div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">
  <a href="index.html">Home</a> &middot;
  <a href="calls.html">Conversations</a> &middot;
  <a href="privacy.html">Privacy</a> &middot;
  <a href="terms.html">Terms</a>
</div></footer>
</body>
</html>
"""


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("docs"),
                        help="Output directory, default docs/ for GitHub Pages")
    parser.add_argument("--store", type=Path, help="Read calls from this file")
    args = parser.parse_args()

    stats = export(args.out, args.store)
    print(f"Wrote {args.out}/index.html and {args.out}/calls.html")
    print(f"{stats['calls']} conversations, {stats['actionable']} actionable, "
          f"{stats['save_opportunities']} named a way back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
