"""The architecture diagram for the landing page.

Hand-written SVG rather than a rendered image, so it scales cleanly, takes the
page palette and stays legible on a phone.

Every label is a real value read from the deployed Bolna agent: Deepgram
Nova-3 at 16 kHz with 200 ms endpointing, streaming ElevenLabs synthesis,
GPT-5.4-mini on Azure, Vobiz carrier legs, and a two-word barge-in threshold.
Nothing here is invented for effect.
"""

from __future__ import annotations

STAGES = [
    {
        "key": "carrier",
        "tone": "sky",
        "step": "01",
        "title": "Carrier leg",
        "sub": "Vobiz PSTN",
        "lines": ["Inbound SIP, bidirectional", "PCM at 16 kHz, linear16"],
    },
    {
        "key": "asr",
        "tone": "cyan",
        "step": "02",
        "title": "Speech to text",
        "sub": "Deepgram Nova-3",
        "lines": ["Streaming partials, 200 ms endpointing", "Barge-in after two words"],
    },
    {
        "key": "llm",
        "tone": "amber",
        "step": "03",
        "title": "Dialogue policy",
        "sub": "GPT-5.4-mini on Azure",
        "lines": ["Turn-taking over full history", "Follow-ups chosen from the answer"],
    },
    {
        "key": "tts",
        "tone": "violet",
        "step": "04",
        "title": "Text to speech",
        "sub": "ElevenLabs streaming",
        "lines": ["First chunk plays before the sentence ends", "Interruptible mid-utterance"],
    },
    {
        "key": "extract",
        "tone": "green",
        "step": "05",
        "title": "Post-call extraction",
        "sub": "18 dispositions, one LLM pass",
        "lines": ["Objective option and free text", "Per-field confidence returned"],
    },
    {
        "key": "record",
        "tone": "navy",
        "step": "06",
        "title": "Typed record",
        "sub": "Validated, then scored",
        "lines": ["Stated or inferred, per field", "Actionable only if stated"],
    },
]

TONES = {
    "sky": "#2f6f9f",
    "cyan": "#1f7a8c",
    "amber": "#8f6220",
    "violet": "#6b4a86",
    "green": "#1e6b4f",
    "navy": "#10213d",
}


def diagram_css() -> str:
    tones = "\n".join(
        f"  .st-{k} {{ --tone:{v}; }}" for k, v in TONES.items()
    )
    return f"""
/* architecture diagram */
.arch {{ display:grid; gap:12px; grid-template-columns:repeat(3,1fr); }}
@media (max-width:900px) {{ .arch {{ grid-template-columns:repeat(2,1fr); }} }}
@media (max-width:560px) {{ .arch {{ grid-template-columns:1fr; }} }}
{tones}
.stage {{
  position:relative; background:var(--card); border:1px solid var(--line);
  border-top:3px solid var(--tone); border-radius:10px; padding:16px 17px 15px;
  transition:transform .18s var(--ease), border-color .18s var(--ease);
}}
.stage:hover {{ transform:translateY(-2px); border-color:var(--tone); }}
.stage .step {{
  font-size:11px; font-weight:700; letter-spacing:1.3px; color:var(--tone);
  font-variant-numeric:tabular-nums;
}}
.stage h3 {{ font-size:16.5px; margin:5px 0 2px; font-weight:600; letter-spacing:-.01em; }}
.stage .sub {{
  display:inline-block; font-size:12px; font-weight:600; color:var(--tone);
  background:color-mix(in srgb, var(--tone) 9%, transparent);
  border:1px solid color-mix(in srgb, var(--tone) 26%, transparent);
  border-radius:5px; padding:2px 7px; margin-bottom:9px;
}}
.stage ul {{ margin:0; padding:0; list-style:none; }}
.stage li {{
  font-size:13px; line-height:1.5; color:var(--body); padding-left:13px;
  position:relative;
}}
.stage li::before {{
  content:""; position:absolute; left:0; top:8px; width:5px; height:5px;
  border-radius:50%; background:var(--tone); opacity:.55;
}}
.arch-legend {{
  display:flex; gap:16px; flex-wrap:wrap; margin-top:14px;
  font-size:12.5px; color:var(--muted);
}}
.arch-legend span {{ display:flex; align-items:center; gap:6px; }}
.arch-legend i {{ width:9px; height:9px; border-radius:2px; display:inline-block; }}
.latency {{
  margin-top:16px; background:var(--navy); color:#c8d4e6; border-radius:10px;
  padding:15px 18px; font-size:13.5px; line-height:1.6;
}}
.latency b {{ color:#f4f2ed; }}
.latency .budget {{
  display:flex; gap:7px; flex-wrap:wrap; margin-top:10px;
  font-variant-numeric:tabular-nums;
}}
.latency .budget span {{
  background:var(--navy-2); border:1px solid var(--line-navy); border-radius:6px;
  padding:4px 9px; font-size:12.5px; color:#9fb0c8;
}}
.latency .budget b {{ color:#e8a33d; font-weight:700; }}
"""


def diagram_html() -> str:
    cards = []
    for i, s in enumerate(STAGES):
        lines = "".join(f"<li>{l}</li>" for l in s["lines"])
        delay = f" d{min(i, 4)}" if i else ""
        cards.append(
            f'''    <div class="stage st-{s['tone']} rise{delay}">
      <div class="step">{s['step']}</div>
      <h3>{s['title']}</h3>
      <span class="sub">{s['sub']}</span>
      <ul>{lines}</ul>
    </div>'''
        )
    stages = "\n".join(cards)

    legend = "".join(
        f'<span><i style="background:{TONES[t]}"></i>{label}</span>'
        for t, label in (
            ("cyan", "Audio in"),
            ("amber", "Reasoning"),
            ("violet", "Audio out"),
            ("green", "Extraction"),
        )
    )

    return f"""  <div class="arch">
{stages}
  </div>
  <div class="arch-legend rise">{legend}</div>
  <div class="latency rise d1">
    <b>The round trip is a latency budget.</b> Every stage between the caller
    finishing a word and hearing a reply competes for the same window. Past
    roughly a second the pause reads as a dropped call, so transcription,
    generation and synthesis all stream rather than wait for a complete result.
    <div class="budget">
      <span>endpointing <b>200 ms</b></span>
      <span>partials <b>streamed</b></span>
      <span>first TTS chunk <b>before the sentence ends</b></span>
      <span>barge-in <b>2 words</b></span>
    </div>
  </div>"""
