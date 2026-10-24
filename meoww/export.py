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
        _landing_page(stats, generated), encoding="utf-8"
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


def _landing_page(stats: dict, generated: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meoww</title>
<meta name="description" content="A voice agent that calls churned users, asks why, and turns the conversation into a record someone can act on.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 76 76'><rect width='76' height='76' rx='18' fill='%23E8A33D'/><path d='M20 30h26a9 9 0 0 1 0 18H30' fill='none' stroke='%2310213D' stroke-width='5.5' stroke-linecap='round'/><path d='M36 40l-7 8 7 8' fill='none' stroke='%2310213D' stroke-width='5.5' stroke-linecap='round' stroke-linejoin='round'/></svg>">
<style>
  :root {{
    --navy:#10213d; --ink:#1a2330; --body:#4a5568; --muted:#6b7689;
    --bg:#f4f2ed; --card:#fff; --line:#ddd8cc; --amber:#a8742a; --green:#1e6b4f;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:16px/1.6 -apple-system,"Segoe UI",system-ui,sans-serif; }}
  .wrap {{ max-width:860px; margin:0 auto; padding:0 24px; }}
  header {{ background:var(--navy); color:#f4f2ed; padding:64px 0 56px; }}
  header .mark {{ display:flex; align-items:center; gap:14px; margin-bottom:28px; }}
  header .mark span {{ font-size:19px; font-weight:700; letter-spacing:.5px; }}
  h1 {{ font-size:40px; line-height:1.2; margin:0 0 16px; font-weight:600; }}
  header p {{ font-size:19px; line-height:1.5; color:#c8d4e6; margin:0; max-width:620px; }}
  .cta {{ display:flex; gap:12px; margin-top:32px; flex-wrap:wrap; }}
  .cta a {{ display:inline-block; padding:11px 20px; border-radius:7px;
    text-decoration:none; font-size:15px; font-weight:600; }}
  .cta .primary {{ background:#e8a33d; color:#231705; }}
  .cta .secondary {{ background:transparent; color:#f4f2ed; border:1px solid #2c4169; }}
  section {{ padding:52px 0; border-bottom:1px solid var(--line); }}
  section:last-of-type {{ border-bottom:none; }}
  h2 {{ font-size:13px; letter-spacing:1.5px; text-transform:uppercase;
    color:var(--amber); margin:0 0 20px; }}
  h3 {{ font-size:19px; margin:0 0 8px; font-weight:600; }}
  p {{ color:var(--body); margin:0 0 16px; }}
  .lede {{ font-size:18px; color:var(--ink); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; }}
  .grid.four {{ grid-template-columns:repeat(4,1fr); }}
  @media (max-width:760px) {{ .grid.four {{ grid-template-columns:repeat(2,1fr); }} }}
  .box {{ background:var(--card); border:1px solid var(--line); border-radius:9px; padding:20px; }}
  .box p {{ margin:0; font-size:15px; }}
  .num {{ display:inline-block; width:21px; height:21px; line-height:21px;
    text-align:center; background:var(--navy); color:#fff; border-radius:5px;
    font-size:12px; font-weight:700; margin-right:8px; }}
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:14px; }}
  .stat {{ background:var(--card); border:1px solid var(--line); border-radius:9px; padding:18px; }}
  .stat .v {{ font-size:30px; font-weight:600; color:var(--navy); }}
  .stat .l {{ font-size:13px; color:var(--muted); margin-top:3px; }}
  .quote {{ background:var(--card); border-left:3px solid var(--amber);
    border-radius:0 7px 7px 0; padding:18px 20px; font-size:15px; }}
  .quote b {{ color:var(--navy); }}
  code {{ background:#eae7df; padding:2px 6px; border-radius:4px; font-size:14px; }}
  pre {{ background:var(--navy); color:#e4ecf7; padding:16px 18px; border-radius:8px;
    overflow-x:auto; font-size:14px; line-height:1.6; }}
  footer {{ padding:36px 0 56px; font-size:14px; color:var(--muted); }}
  footer a {{ color:var(--amber); }}
  .note {{ background:#fff5e0; border:1px solid #e2b86a; border-left:4px solid var(--amber);
    border-radius:8px; padding:16px 18px; font-size:15px; color:#5c4414; }}
  .note b {{ color:#4a3208; }}
</style>
</head>
<body>

<header>
  <div class="wrap">
    <div class="mark">
      <svg width="34" height="34" viewBox="0 0 76 76" aria-label="Meoww"><rect width="76" height="76" rx="18" fill="#E8A33D"/><path d="M20 30h26a9 9 0 0 1 0 18H30" fill="none" stroke="#10213D" stroke-width="5.5" stroke-linecap="round"/><path d="M36 40l-7 8 7 8" fill="none" stroke="#10213D" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>Meoww</span>
    </div>
    <h1>Your users tell you nothing when they leave.</h1>
    <p>Meoww phones them, asks why, and turns the conversation into a record
    an engineer or a manager can act on.</p>
    <div class="cta">
      <a class="primary" href="calls.html">See {stats['calls']} conversations</a>
      <a class="secondary" href="https://github.com/beeebom/S2S-VoiceBot-Ai">Source on GitHub</a>
    </div>
  </div>
</header>

<section>
  <div class="wrap">
    <h2>The problem</h2>
    <p class="lede">A user leaves. All you ever learn is two stars and six words:
    <em>"App keeps crashing. Uninstalled."</em></p>
    <p>No screen, no device, no steps. The engineer cannot reproduce it, the
    manager cannot price a win-back, and the user is already gone. Surveys reach
    the few who already complain. Proper interviews cost 45 minutes each, so
    teams run twenty, not two hundred.</p>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>How it works</h2>
    <div class="grid four">
      <div class="box"><p><span class="num">1</span> A churn signal arrives: a bad review, a cancelled plan, an account gone quiet.</p></div>
      <div class="box"><p><span class="num">2</span> The voice agent calls and interviews them, following up on whatever they say.</p></div>
      <div class="box"><p><span class="num">3</span> The call becomes a typed record: reason, severity, the price they would have stayed at.</p></div>
      <div class="box"><p><span class="num">4</span> Each field is scored, and marked as either stated by the user or inferred.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>The interview is the product</h2>
    <p>A weak agent asks three questions and hangs up. This one digs until the
    answer is specific enough to act on.</p>
    <div class="quote">
      <p><b>Agent:</b> What made you stop using it?</p>
      <p><b>User:</b> It was too expensive.</p>
      <p><b>Agent:</b> What were you paying, and what would you have stayed at?</p>
      <p style="margin:0"><b>User:</b> 599 a month. I would have stayed at 249.</p>
    </div>
    <p style="margin-top:16px">"Too expensive" is useless. "I would have stayed
    at 249" is a pricing decision.</p>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Honest data</h2>
    <p>Three rules keep the numbers trustworthy, and they are the reason some
    conversations are deliberately not counted.</p>
    <div class="grid">
      <div class="box">
        <h3>Stated, not guessed</h3>
        <p>A reason only counts if the user said it themselves. Agreeing with a
        suggestion does not count.</p>
      </div>
      <div class="box">
        <h3>Failures stay counted</h3>
        <p>Unanswered and too-short calls stay in the denominator, so the save
        rate is not flattered.</p>
      </div>
      <div class="box">
        <h3>Weak calls are flagged</h3>
        <p>A smooth summary of a call that surfaced nothing is kept out of the
        aggregate.</p>
      </div>
    </div>
    <div class="stats" style="margin-top:20px">
      <div class="stat"><div class="v">{stats['calls']}</div><div class="l">conversations</div></div>
      <div class="stat"><div class="v">{stats['actionable']}</div><div class="l">actionable</div></div>
      <div class="stat"><div class="v">{stats['calls'] - stats['actionable']}</div><div class="l">rejected by the rules</div></div>
      <div class="stat"><div class="v">{stats['save_opportunities']}</div><div class="l">named a way back</div></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>What is built, and what is not</h2>
    <div class="note">
      <b>Extraction is live. Telephony is not connected.</b>
      Every record came out of the real pipeline: the transcript went to the
      Bolna agent's extraction endpoint and the answers were mapped by the same
      code a phone call uses. What did not happen is the dial, because an Indian
      number requires KYC verification. Attaching a number is configuration,
      not new code.
    </div>
    <p style="margin-top:20px">Run the whole pipeline yourself:</p>
    <pre>git clone https://github.com/beeebom/S2S-VoiceBot-Ai
pip install -r requirements.txt
python -m meoww.simulate transcripts/
python -m meoww.webhook</pre>
  </div>
</section>

<footer>
  <div class="wrap">
    Built with <a href="https://bolna.ai">Bolna</a> for the Symphony Buildathon 2026.
    Snapshot generated {generated}.
    <a href="https://github.com/beeebom/S2S-VoiceBot-Ai">Source</a> &middot;
    <a href="calls.html">Conversations</a> &middot;
    <a href="privacy.html">Privacy</a> &middot;
    <a href="terms.html">Terms</a>
  </div>
</footer>

</body>
</html>
"""


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
