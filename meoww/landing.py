
from __future__ import annotations

import html
import json
from typing import Dict, List, Tuple

from .diagram import diagram_css, diagram_html

REPO = "https://github.com/beeebom/S2S-VoiceBot-Ai"

ROTATOR: List[Tuple[str, str]] = [
    ("It just got too expensive for what I was using", "price"),
    ("It crashed every time I tried uploading photos", "bug"),
    ("There was no way to search my photos. None at all.", "missing feature"),
    ("I wrote to support three times and nobody ever replied", "support"),
    ("I could never work out how to share an album", "usability"),
    ("It got really slow. Like painfully slow.", "performance"),
]

TOUR = [
    ("#problem", "The problem",
     "A user leaves and you get six words. Nothing an engineer can act on."),
    ("#how", "The pipeline",
     "A churn signal becomes a call, the call becomes a typed record."),
    ("#arch", "The pipeline",
     "Six stages, each streaming, because the round trip is a latency budget."),
    ("#interview", "The interview",
     "This is the product: the agent digs until the answer is specific."),
    ("#honest", "Honest data",
     "Three rules decide what counts, and some conversations deliberately do not."),
    ("#state", "What is built",
     "Extraction runs live. Telephony is not connected, and the page says so."),
]


def landing_page(stats: Dict) -> str:
    css = diagram_css()
    arch = diagram_html()
    rotator = json.dumps([{"q": q, "tag": t} for q, t in ROTATOR])
    tour = json.dumps([{"sel": s, "title": t, "body": b} for s, t, b in TOUR])
    reasons = stats.get("reasons_ranked") or []
    top = reasons[0][1] if reasons else 1

    bars = "\n".join(
        f'''      <div class="bar-row" style="--i:{i}">
        <span class="bar-name">{html.escape(name.replace("_", " "))}</span>
        <span class="bar-track"><span class="bar-fill" style="--w:{round(count / top * 100)}%"></span></span>
        <span class="bar-n">{count}</span>
      </div>'''
        for i, (name, count) in enumerate(reasons)
    )

    rejected = stats["calls"] - stats["actionable"]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Meoww</title>
<meta name="description" content="A voice agent that calls churned users, asks why, and turns the conversation into a record someone can act on.">
<meta property="og:title" content="Meoww">
<meta property="og:description" content="A voice agent that calls churned users and turns the conversation into a record someone can act on.">
<meta name="theme-color" content="#10213d">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 76 76'><rect width='76' height='76' rx='18' fill='%23E8A33D'/><path d='M20 30h26a9 9 0 0 1 0 18H30' fill='none' stroke='%2310213D' stroke-width='5.5' stroke-linecap='round'/><path d='M36 40l-7 8 7 8' fill='none' stroke='%2310213D' stroke-width='5.5' stroke-linecap='round' stroke-linejoin='round'/></svg>">
<style>
:root {{
  --navy:#10213d; --navy-2:#17294a; --line-navy:#2c4169;
  --ink:#1a2330; --body:#4a5568; --muted:#6b7689;
  --bg:#f4f2ed; --card:#fff; --line:#ddd8cc;
  --amber:#a8742a; --amber-br:#e8a33d; --amber-bg:#fbf3e4;
  --green:#1e6b4f;
  --step:clamp(14px, 1.1vw, 16px);
  --h1:clamp(32px, 6.2vw, 58px);
  --h2:clamp(22px, 3.4vw, 30px);
  --gut:clamp(20px, 5vw, 32px);
  --sect:clamp(48px, 8vw, 86px);
  --ease:cubic-bezier(.22,.61,.36,1);
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; -webkit-text-size-adjust:100%; }}
body {{
  margin:0; background:var(--bg); color:var(--ink);
  font:var(--step)/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased; overflow-x:hidden;
}}
.wrap {{ max-width:1100px; margin:0 auto; padding:0 var(--gut); }}

/* ---- header ---- */
header {{ background:var(--navy); color:#f4f2ed; padding:clamp(40px,7vw,76px) 0 clamp(44px,7vw,72px); }}
.mark {{ display:flex; align-items:center; gap:12px; margin-bottom:clamp(26px,4vw,40px); }}
.mark span {{ font-size:18px; font-weight:700; letter-spacing:.4px; }}
h1 {{ font-size:var(--h1); line-height:1.1; margin:0 0 18px; font-weight:600; letter-spacing:-.02em; max-width:17ch; }}
/* hero mark: speech bubble with a voice trace, drawn rather than bitmapped
   so it stays crisp at any size and can take the palette. */
.hero-art {{ position:relative; display:flex; justify-content:center; align-items:center; }}
.hero-art svg {{ width:min(100%, 300px); height:auto; overflow:visible; }}
.bubble {{ fill:none; stroke:var(--amber-br); stroke-width:3.4; stroke-linecap:round; stroke-linejoin:round; }}
.wave {{ fill:none; stroke:#f4f2ed; stroke-width:3.4; stroke-linecap:round; stroke-linejoin:round; }}
.bubble, .wave {{ stroke-dasharray:var(--len); stroke-dashoffset:var(--len); }}
.drawn .bubble {{ animation:draw 1.1s var(--ease) forwards; }}
.drawn .wave {{ animation:draw .9s var(--ease) .45s forwards; }}
@keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
@media (prefers-reduced-motion:reduce) {{
  .bubble, .wave {{ stroke-dashoffset:0; animation:none; }}
}}
@media (max-width:999px) {{ .hero-art {{ display:none; }} }}

.hero {{ display:grid; gap:clamp(28px,4vw,56px); align-items:end; }}
@media (min-width:1000px) {{ .hero {{ grid-template-columns:1.15fr .62fr .72fr; align-items:center; }} }}
.hero-aside {{ display:flex; flex-direction:column; gap:12px; }}
.aside-card {{ background:var(--navy-2); border:1px solid var(--line-navy); border-radius:10px; padding:16px 18px; }}
.aside-card .k {{ font-size:11.5px; letter-spacing:1.4px; text-transform:uppercase; color:var(--amber-br); font-weight:700; }}
.aside-card .v {{ font-size:27px; font-weight:600; line-height:1.15; margin-top:5px; letter-spacing:-.02em; }}
.aside-card .d {{ font-size:13px; color:#9fb0c8; margin-top:3px; line-height:1.45; }}
.sub {{ font-size:clamp(16px,2.1vw,20px); line-height:1.5; color:#c8d4e6; margin:0; max-width:56ch; }}

/* rotator */
.rot {{ margin:clamp(22px,3.4vw,32px) 0 0; display:flex; flex-direction:column; gap:8px; }}
.rot-label {{ font-size:12px; letter-spacing:1.6px; text-transform:uppercase; color:var(--amber-br); font-weight:700; }}
.rot-line {{
  display:flex; align-items:baseline; gap:12px; flex-wrap:wrap;
  min-height:clamp(30px,4.6vw,42px);
}}
.rot-q {{
  font-size:clamp(17px,2.5vw,25px); line-height:1.35; color:#f4f2ed;
  font-weight:500; max-width:40ch;
}}
.rot-tag {{
  font-size:12px; font-weight:700; letter-spacing:.8px; text-transform:uppercase;
  color:var(--amber-br); background:rgba(232,163,61,.12);
  border:1px solid rgba(232,163,61,.3); border-radius:5px; padding:3px 8px; white-space:nowrap;
}}
.cta {{ display:flex; gap:12px; margin-top:clamp(26px,4vw,38px); flex-wrap:wrap; }}
.cta a, .cta button {{
  font:inherit; display:inline-block; padding:12px 22px; border-radius:7px;
  text-decoration:none; font-size:15px; font-weight:600; cursor:pointer;
  border:1px solid transparent; transition:transform .16s var(--ease), background .16s var(--ease);
}}
.cta .primary {{ background:var(--amber-br); color:#231705; }}
.cta .secondary {{ background:transparent; color:#f4f2ed; border-color:var(--line-navy); }}
.cta a:hover, .cta button:hover {{ transform:translateY(-1px); }}
.cta .secondary:hover {{ background:var(--navy-2); }}

/* ---- sections ---- */
section {{ position:relative; padding:var(--sect) 0; border-bottom:1px solid var(--line); }}

/* A faint woven texture stops the flat fills reading as a template.
   Two offset repeating gradients, both under 3% opacity: at normal viewing
   distance it is felt rather than seen. */
body::before {{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0; opacity:.035;
  background-image:
    repeating-linear-gradient(0deg, #10213d 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, #10213d 0 1px, transparent 1px 3px);
}}
header, section, footer {{ position:relative; z-index:1; }}

/* Dark sections break the cream run so the page has a pulse. */
section.dark {{
  background:var(--navy); color:#e7ecf4; border-bottom-color:var(--line-navy);
}}
section.dark h2 {{ color:var(--amber-br); }}
section.dark .sect-h {{ color:#f4f2ed; }}
section.dark p {{ color:#c8d4e6; }}
section.dark .lede {{ color:#f4f2ed; }}
section.dark .box {{ background:var(--navy-2); border-color:var(--line-navy); }}
section.dark .box h3 {{ color:#f4f2ed; }}
section.dark .box p {{ color:#aebdd4; }}
section.dark .box:hover {{ border-color:#44618f; }}
section.dark .num {{ background:var(--amber-br); color:#231705; }}
section.dark .convo {{ background:var(--navy-2); border-color:var(--line-navy); }}
section.dark .who {{ color:var(--amber-br); }}
section.dark .turn {{ color:#dce5f1; }}
section.dark .turn.key .what {{
  background:rgba(232,163,61,.14); box-shadow:0 0 0 4px rgba(232,163,61,.14); color:#f4f2ed;
}}
section.dark .note {{
  background:var(--navy-2); border-color:var(--line-navy);
  border-left-color:var(--amber-br); color:#c8d4e6;
}}
section.dark .note b {{ color:#f4f2ed; }}
section.dark pre {{ background:#0b182d; border:1px solid var(--line-navy); }}

/* Section numbering gives the page an index rather than a scroll. */
.sect-no {{
  position:absolute; top:calc(var(--sect) - 8px); right:var(--gut);
  font-size:13px; font-weight:700; letter-spacing:2px; color:var(--line);
  font-variant-numeric:tabular-nums;
}}
section.dark .sect-no {{ color:var(--line-navy); }}
@media (max-width:760px) {{ .sect-no {{ display:none; }} }}
section:last-of-type {{ border-bottom:none; }}
h2 {{ font-size:12px; letter-spacing:1.7px; text-transform:uppercase; color:var(--amber); margin:0 0 18px; font-weight:700; }}
h3 {{ font-size:18px; margin:0 0 7px; font-weight:600; letter-spacing:-.01em; }}
p {{ color:var(--body); margin:0 0 15px; }}
p:last-child {{ margin-bottom:0; }}
.lede {{ font-size:clamp(17px,2.2vw,21px); line-height:1.5; color:var(--ink); max-width:46ch; letter-spacing:-.01em; }}
.sect-h {{ font-size:var(--h2); line-height:1.25; font-weight:600; letter-spacing:-.02em; margin:0 0 16px; max-width:22ch; }}

.grid {{ display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(min(210px,100%),1fr)); }}
.grid.four {{ grid-template-columns:repeat(4,1fr); }}
.grid.three {{ grid-template-columns:repeat(3,1fr); }}
@media (max-width:820px) {{ .grid.four {{ grid-template-columns:repeat(2,1fr); }} }}
@media (max-width:620px) {{ .grid.four, .grid.three {{ grid-template-columns:1fr; }} }}

.box {{
  background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:20px; transition:border-color .18s var(--ease), transform .18s var(--ease);
}}
.box:hover {{ border-color:#c9c2b2; transform:translateY(-2px); }}
.box p {{ margin:0; font-size:14.5px; line-height:1.55; }}
.num {{
  display:inline-flex; align-items:center; justify-content:center;
  width:22px; height:22px; background:var(--navy); color:#fff;
  border-radius:6px; font-size:12px; font-weight:700; margin-bottom:10px;
}}

/* conversation */
.convo {{ background:var(--card); border:1px solid var(--line); border-left:3px solid var(--amber-br); border-radius:0 10px 10px 0; padding:clamp(16px,2.6vw,22px); }}
.turn {{ display:flex; gap:10px; margin-bottom:11px; font-size:clamp(14px,1.8vw,16px); line-height:1.5; }}
.turn:last-child {{ margin-bottom:0; }}
.who {{ font-weight:700; color:var(--navy); min-width:52px; flex-shrink:0; }}
.turn.key .what {{ background:var(--amber-bg); box-shadow:0 0 0 4px var(--amber-bg); border-radius:3px; }}

/* chart */
.chart {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:clamp(16px,2.6vw,24px); }}
.bar-row {{ display:flex; align-items:center; gap:12px; margin-bottom:9px; font-size:14px; }}
.bar-row:last-child {{ margin-bottom:0; }}
.bar-name {{ width:clamp(88px,15vw,132px); flex-shrink:0; font-weight:600; text-transform:capitalize; color:var(--ink); }}
.bar-track {{ flex:1; height:9px; background:#efece4; border-radius:5px; overflow:hidden; }}
.bar-fill {{ display:block; height:100%; width:var(--w); background:var(--amber); border-radius:5px; transform-origin:left; }}
.bar-n {{ width:22px; text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; }}

/* stats */
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:20px; }}
@media (max-width:620px) {{ .stats {{ grid-template-columns:repeat(2,1fr); }} }}
.stat {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px; }}
.stat.accent {{ background:var(--navy); border-color:var(--navy); }}
.stat .v {{ font-size:clamp(26px,4vw,32px); font-weight:600; color:var(--navy); line-height:1.1; letter-spacing:-.02em; }}
.stat.accent .v {{ color:#fff; }}
.stat .l {{ font-size:12.5px; color:var(--muted); margin-top:4px; line-height:1.4; }}
.stat.accent .l {{ color:#9fb0c8; }}

.note {{ background:#fff5e0; border:1px solid #e2b86a; border-left:4px solid var(--amber); border-radius:9px; padding:17px 19px; font-size:14.5px; line-height:1.6; color:#5c4414; }}
.note b {{ color:#4a3208; }}
pre {{ background:var(--navy); color:#e4ecf7; padding:16px 18px; border-radius:9px; overflow-x:auto; font-size:13.5px; line-height:1.7; margin:0; }}
code {{ font-family:ui-monospace,Menlo,Consolas,monospace; }}

footer {{ padding:34px 0 clamp(40px,8vw,64px); font-size:13.5px; color:var(--muted); }}
footer a {{ color:var(--amber); }}
footer .links {{ margin-top:7px; }}

{css}

/* ---- motion ---- */
.rise {{ opacity:0; transform:translateY(14px); transition:opacity .5s var(--ease), transform .5s var(--ease); }}
.rise.in {{ opacity:1; transform:none; }}
.rise.d1 {{ transition-delay:.06s; }} .rise.d2 {{ transition-delay:.12s; }}
.rise.d3 {{ transition-delay:.18s; }} .rise.d4 {{ transition-delay:.24s; }}
.bar-fill {{ transform:scaleX(0); transition:transform .6s var(--ease); transition-delay:calc(var(--i) * 60ms); }}
.chart.in .bar-fill {{ transform:scaleX(1); }}
.rot-q, .rot-tag {{ transition:opacity .28s var(--ease), transform .28s var(--ease); }}
.rot.out .rot-q, .rot.out .rot-tag {{ opacity:0; transform:translateY(-5px); }}

/* ---- tour ---- */
.tour-card {{
  position:fixed; z-index:60; left:50%; bottom:22px; transform:translateX(-50%);
  width:min(420px, calc(100vw - 32px));
  background:var(--navy); color:#f4f2ed; border:1px solid var(--line-navy);
  border-radius:11px; padding:17px 19px; box-shadow:0 12px 34px rgba(16,33,61,.3);
  opacity:0; pointer-events:none; transition:opacity .22s var(--ease), transform .22s var(--ease);
}}
.tour-card.on {{ opacity:1; pointer-events:auto; }}
.tour-step {{ font-size:11.5px; letter-spacing:1.4px; text-transform:uppercase; color:var(--amber-br); font-weight:700; }}
.tour-card h4 {{ margin:6px 0 5px; font-size:17px; font-weight:600; }}
.tour-card p {{ margin:0 0 13px; font-size:14px; line-height:1.5; color:#c8d4e6; }}
.tour-btns {{ display:flex; gap:8px; align-items:center; }}
.tour-btns button {{
  font:inherit; font-size:13.5px; font-weight:600; padding:8px 15px; border-radius:6px;
  cursor:pointer; border:1px solid var(--line-navy); background:transparent; color:#f4f2ed;
}}
.tour-btns .next {{ background:var(--amber-br); color:#231705; border-color:var(--amber-br); }}
.tour-btns .skip {{ margin-left:auto; border:none; color:#8a9bb8; padding:8px 4px; }}
.tour-focus {{ position:relative; z-index:55; }}
.tour-focus::after {{
  content:""; position:absolute; inset:-10px 4px; border-radius:12px;
  border:2px solid var(--amber-br); background:rgba(232,163,61,.06);
  pointer-events:none;
}}
body.touring {{ scroll-padding-bottom:220px; }}
body.touring {{ overflow:hidden; }}
body.touring .scrim {{ opacity:1; pointer-events:auto; }}
.scrim {{
  position:fixed; inset:0; background:rgba(16,33,61,.42); z-index:50;
  opacity:0; pointer-events:none; transition:opacity .25s var(--ease);
}}

@media (prefers-reduced-motion:reduce) {{
  html {{ scroll-behavior:auto; }}
  *, *::before, *::after {{ animation:none !important; transition:none !important; }}
  .rise {{ opacity:1; transform:none; }}
  .bar-fill {{ transform:scaleX(1); }}
}}
</style>
</head>
<body>

<div class="scrim" hidden></div>

<header>
  <div class="wrap">
    <div class="mark rise in">
      <svg width="32" height="32" viewBox="0 0 76 76" aria-label="Meoww"><rect width="76" height="76" rx="18" fill="#E8A33D"/><path d="M20 30h26a9 9 0 0 1 0 18H30" fill="none" stroke="#10213D" stroke-width="5.5" stroke-linecap="round"/><path d="M36 40l-7 8 7 8" fill="none" stroke="#10213D" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>Meoww</span>
    </div>
    <div class="hero">
    <div>
    <h1 class="rise d1">Your users tell you nothing when they leave.</h1>
    <p class="sub rise d2">Meoww phones them, asks why, and turns the conversation
    into a record an engineer or a manager can act on.</p>

    <div class="rot rise d3" id="rot">
      <span class="rot-label">What they actually said</span>
      <span class="rot-line">
        <span class="rot-q" id="rotQ">{html.escape(ROTATOR[0][0])}</span>
        <span class="rot-tag" id="rotT">{html.escape(ROTATOR[0][1])}</span>
      </span>
    </div>

    <div class="cta rise d4">
      <a class="primary" href="calls.html">See {stats['calls']} conversations</a>
      <button class="secondary" id="tourBtn" type="button">Take the tour</button>
      <a class="secondary" href="{REPO}">Source</a>
    </div>
    </div>

    <div class="hero-art rise d2" aria-hidden="true">
      <svg viewBox="0 0 215 155" role="presentation">
        <path class="bubble" style="--len:470"
              d="M92 14 C 52 14, 20 38, 20 70 C 20 88, 30 103, 47 112 C 45 124, 38 133, 26 140 C 45 139, 62 132, 74 120 C 80 122, 86 123, 92 123"/>
        <path class="wave" style="--len:620"
              d="M104 74 L112 56 L120 92 L128 30 L136 110 L144 18 L152 118 L160 40 L168 96 L176 60 L184 84 L192 68 L200 76"/>
      </svg>
    </div>
    <div class="hero-aside rise d3" aria-label="Figures from the stored conversations">
      <div class="aside-card">
        <div class="k">Conversations</div>
        <div class="v">{stats['calls']}</div>
        <div class="d">Across nine churn reasons, in English and Hindi</div>
      </div>
      <div class="aside-card">
        <div class="k">Named a way back</div>
        <div class="v">{stats['save_opportunities']}</div>
        <div class="d">Each one a condition somebody could act on</div>
      </div>
      <div class="aside-card">
        <div class="k">Rejected by the rules</div>
        <div class="v">{rejected}</div>
        <div class="d">Inferred or too thin to count</div>
      </div>
    </div>
    </div>
  </div>
</header>

<section id="problem">
  <span class="sect-no">01</span>
  <div class="wrap">
    <h2 class="rise">The problem</h2>
    <p class="lede rise d1">A user leaves. All you ever learn is two stars and
    six words: <em>"App keeps crashing. Uninstalled."</em></p>
    <p class="rise d2" style="max-width:62ch;margin-top:14px">No screen, no device,
    no steps. The engineer cannot reproduce it, the manager cannot price a
    win-back, and the user is already gone. Surveys reach the few who already
    complain. Proper interviews cost 45 minutes each, so teams run twenty, not
    two hundred.</p>
  </div>
</section>

<section id="how" class="dark">
  <span class="sect-no">02</span>
  <div class="wrap">
    <h2 class="rise">How it works</h2>
    <div class="grid four">
      <div class="box rise"><span class="num">1</span><p>A churn signal arrives: a bad review, a cancelled plan, an account gone quiet.</p></div>
      <div class="box rise d1"><span class="num">2</span><p>The voice agent calls and interviews them, following up on whatever they say.</p></div>
      <div class="box rise d2"><span class="num">3</span><p>The call becomes a typed record: reason, severity, the price they would have stayed at.</p></div>
      <div class="box rise d3"><span class="num">4</span><p>Each field is scored, and marked as either stated by the user or inferred.</p></div>
    </div>
  </div>
</section>

<section id="arch">
  <span class="sect-no">03</span>
  <div class="wrap">
    <h2 class="rise">The voice pipeline</h2>
    <p class="sect-h rise d1">Six stages between a ringing phone and a typed record.</p>
{arch}
  </div>
</section>

<section id="interview" class="dark">
  <span class="sect-no">04</span>
  <div class="wrap">
    <h2 class="rise">The interview is the product</h2>
    <p class="sect-h rise d1">A weak agent asks three questions and hangs up.</p>
    <div class="convo rise d2">
      <div class="turn"><span class="who">Agent</span><span class="what">What made you stop using it?</span></div>
      <div class="turn"><span class="who">User</span><span class="what">It was too expensive.</span></div>
      <div class="turn key"><span class="who">Agent</span><span class="what">What were you paying, and what would you have stayed at?</span></div>
      <div class="turn"><span class="who">User</span><span class="what">599 a month. I would have stayed at 249.</span></div>
    </div>
    <p class="rise d3" style="margin-top:16px;max-width:60ch">"Too expensive" is
    useless. "I would have stayed at 249" is a pricing decision. That one
    follow-up is the difference between a survey and a conversation.</p>
  </div>
</section>

<section id="honest">
  <span class="sect-no">05</span>
  <div class="wrap">
    <h2 class="rise">Honest data</h2>
    <p class="sect-h rise d1">Some conversations are deliberately not counted.</p>
    <div class="grid three">
      <div class="box rise d1"><h3>Stated, not guessed</h3><p>A reason only counts if the user said it themselves. Agreeing with a suggestion does not count.</p></div>
      <div class="box rise d2"><h3>Failures stay counted</h3><p>Unanswered and too-short calls stay in the denominator, so the save rate is not flattered.</p></div>
      <div class="box rise d3"><h3>Weak calls are flagged</h3><p>A smooth summary of a call that surfaced nothing is kept out of the aggregate.</p></div>
    </div>
    <div class="stats">
      <div class="stat rise"><div class="v">{stats['calls']}</div><div class="l">conversations</div></div>
      <div class="stat rise d1"><div class="v">{stats['actionable']}</div><div class="l">actionable</div></div>
      <div class="stat rise d2"><div class="v">{rejected}</div><div class="l">rejected by the rules</div></div>
      <div class="stat accent rise d3"><div class="v">{stats['save_opportunities']}</div><div class="l">named a way back</div></div>
    </div>
    <h2 class="rise" style="margin-top:38px">What is driving churn</h2>
    <div class="chart rise" id="chart">
{bars}
    </div>
  </div>
</section>

<section id="state" class="dark">
  <span class="sect-no">06</span>
  <div class="wrap">
    <h2 class="rise">What is built, and what is not</h2>
    <div class="note rise d1">
      <b>Extraction is live. Telephony is not connected.</b>
      Every record below came out of the real pipeline. What did not happen is
      the dial.
    </div>
    <p class="rise d2" style="margin:20px 0 13px">Run the whole pipeline yourself:</p>
    <pre class="rise d3"><code>git clone {REPO}
pip install -r requirements.txt
python -m meoww.simulate transcripts/
python -m meoww.webhook</code></pre>
  </div>
</section>

<footer>
  <div class="wrap">
    <div class="links">
      <a href="{REPO}">Source</a> &middot;
      <a href="calls.html">Conversations</a> &middot;
      <a href="privacy.html">Privacy</a> &middot;
      <a href="terms.html">Terms</a>
    </div>
  </div>
</footer>

<div class="tour-card" id="tourCard" role="dialog" aria-live="polite" aria-label="Guided tour">
  <span class="tour-step" id="tourStep"></span>
  <h4 id="tourTitle"></h4>
  <p id="tourBody"></p>
  <div class="tour-btns">
    <button class="next" id="tourNext" type="button">Next</button>
    <button id="tourPrev" type="button">Back</button>
    <button class="skip" id="tourSkip" type="button">Close</button>
  </div>
</div>

<script>
(function () {{
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Draw the hero mark once the page has settled.
  var art = document.querySelector('.hero-art');
  if (art && !calm) requestAnimationFrame(function () {{ art.classList.add('drawn'); }});

  // Reveal on scroll. Without IntersectionObserver everything is simply shown.
  var rise = [].slice.call(document.querySelectorAll('.rise:not(.in)'));
  var chart = document.getElementById('chart');
  if (calm || !('IntersectionObserver' in window)) {{
    rise.forEach(function (el) {{ el.classList.add('in'); }});
    if (chart) chart.classList.add('in');
  }} else {{
    var io = new IntersectionObserver(function (entries) {{
      entries.forEach(function (e) {{
        if (e.isIntersecting) {{ e.target.classList.add('in'); io.unobserve(e.target); }}
      }});
    }}, {{ rootMargin: '0px 0px -8% 0px', threshold: 0.05 }});
    rise.forEach(function (el) {{ io.observe(el); }});
    if (chart) io.observe(chart);
  }}

  // Rotator over real quotes from the stored conversations.
  var quotes = {rotator};
  var rot = document.getElementById('rot');
  var rq = document.getElementById('rotQ'), rt = document.getElementById('rotT');
  if (!calm && rot && quotes.length > 1) {{
    var i = 0, timer = setInterval(step, 3400);
    function step() {{
      if (document.hidden || document.body.classList.contains('touring')) return;
      rot.classList.add('out');
      setTimeout(function () {{
        i = (i + 1) % quotes.length;
        rq.textContent = quotes[i].q;
        rt.textContent = quotes[i].tag;
        rot.classList.remove('out');
      }}, 280);
    }}
    rot.addEventListener('click', function () {{ clearInterval(timer); }});
  }}

  // Guided tour: steps through the sections the visitor should read.
  var steps = {tour};
  var card = document.getElementById('tourCard');
  var scrim = document.querySelector('.scrim');
  var at = -1, focused = null;

  function show(n) {{
    if (n < 0 || n >= steps.length) return close();
    at = n;
    var s = steps[n];
    var target = document.querySelector(s.sel);
    if (focused) focused.classList.remove('tour-focus');
    if (target) {{
      focused = target;
      target.classList.add('tour-focus');
      target.scrollIntoView({{ behavior: calm ? 'auto' : 'smooth', block: 'start' }});
    }}
    document.getElementById('tourStep').textContent = 'Step ' + (n + 1) + ' of ' + steps.length;
    document.getElementById('tourTitle').textContent = s.title;
    document.getElementById('tourBody').textContent = s.body;
    document.getElementById('tourPrev').disabled = n === 0;
    document.getElementById('tourNext').textContent = n === steps.length - 1 ? 'Done' : 'Next';
  }}

  function open() {{
    scrim.hidden = false;
    document.body.classList.add('touring');
    card.classList.add('on');
    show(0);
    document.getElementById('tourNext').focus();
  }}

  function close() {{
    if (focused) focused.classList.remove('tour-focus');
    focused = null; at = -1;
    card.classList.remove('on');
    document.body.classList.remove('touring');
    scrim.hidden = true;
    document.getElementById('tourBtn').focus();
  }}

  document.getElementById('tourBtn').addEventListener('click', open);
  document.getElementById('tourNext').addEventListener('click', function () {{ show(at + 1); }});
  document.getElementById('tourPrev').addEventListener('click', function () {{ show(at - 1); }});
  document.getElementById('tourSkip').addEventListener('click', close);
  scrim.addEventListener('click', close);
  document.addEventListener('keydown', function (e) {{
    if (at < 0) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowRight') show(at + 1);
    if (e.key === 'ArrowLeft') show(at - 1);
  }});
}})();
</script>

</body>
</html>
"""
