# Meoww

A voice agent that calls users who have just churned, asks why, and turns the
conversation into a record somebody can act on.


## The problem

A user leaves. All you ever learn is two stars and six words: *"App keeps
crashing. Uninstalled."* No screen, no device, no steps. The engineer cannot
reproduce it, the manager cannot price a win-back, and the user is gone.

Surveys reach the 5% who already complain. Proper interviews cost 45 minutes
each, so teams run twenty, not two hundred. Neither arrives in time to save the
customer.

## What Meoww does

| Step | What happens |
|------|--------------|
| 1. Detect | A churn signal arrives: a low-star review, a cancelled plan, an account gone quiet |
| 2. Converse | A voice agent calls and interviews them, following up on whatever they actually say |
| 3. Structure | The call becomes a typed record: reason, severity, device, the price they would have stayed at |
| 4. Score | Every field is marked as either stated by the user or inferred by the model |

Step 4 is the point. Anyone can summarise a call. Knowing which parts of that
summary the user actually said, and which the model guessed, is what makes the
data safe to act on.

## The interview is the product

A weak agent asks three questions and hangs up. This one digs:

> **Agent:** What made you stop using it?
> **User:** It was too expensive.
> **Agent:** What were you paying, and what would you have stayed at?
> **User:** 599 a month. I would have stayed at 249.

"Too expensive" is useless. "I would have stayed at 249" is a pricing decision.
The follow-up logic lives in the agent prompt ([docs/AGENT_SETUP.md](docs/AGENT_SETUP.md)).

## Honest data

Three design choices keep the numbers trustworthy:

- **Stated vs inferred.** A reason only counts as actionable if the user said it
  themselves. Agreeing with a suggestion ("yeah, sure") does not count, because
  you can never tell whether they meant it or were being agreeable.
- **Failed calls stay in the denominator.** Unanswered and too-short calls are
  stored, not dropped. "14 of 25 named a way back" is only honest if the 25
  includes the failures.
- **Interview quality is scored separately.** A smooth-sounding extraction from
  a call that surfaced nothing is kept out of the aggregate.

## Architecture

```
churn signal -> triage -> Bolna voice agent -> extraction -> record -> dashboard
                                  |                              |
                           telephony, speech,            18 questions,
                           adaptive interview          confidence-scored
```

| Module | Responsibility |
|--------|----------------|
| `meoww/bolna/dispositions.py` | The 18 post-call extraction questions, versioned in code |
| `meoww/bolna/client.py` | Bolna API: dispositions, test runs, executions |
| `meoww/bolna/mapping.py` | Bolna's answers to a typed record, tolerant of malformed input |
| `meoww/bolna/payload.py` | Reads the post-call webhook |
| `meoww/extraction/models.py` | The record schema and the actionable / win-back rules |
| `meoww/store.py` | Append-only JSONL store |
| `meoww/webhook.py` | Flask app: webhook receiver, JSON API, dashboard |
| `meoww/simulate.py` | Runs transcripts through the real pipeline without telephony |

## Running it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env          # add BOLNA_API_KEY and BOLNA_AGENT_ID
```

Create the extraction questions on your Bolna agent:

```bash
python -m meoww.bolna_cli setup      # create them
python -m meoww.bolna_cli sync       # push edits to an existing agent
```

Run the pipeline over transcripts, no phone calls involved:

```bash
python -m meoww.simulate transcripts/ --clear
```

Start the webhook receiver and dashboard:

```bash
python -m meoww.webhook               # http://localhost:8000
```

Point your Bolna agent's webhook at `/webhook/bolna`. Locally, expose it with a
tunnel (`ngrok http 8000`) and use the public URL.

### Endpoints

| Route | Purpose |
|-------|---------|
| `GET /` | Dashboard |
| `POST /webhook/bolna` | Bolna posts here when a call ends |
| `GET /calls` | Every stored call as JSON |
| `GET /calls/<id>` | One call |
| `GET /stats` | Aggregate numbers |
| `GET /healthz` | Liveness |

## Current state

The extraction pipeline runs against the live Bolna API. The 25 records in the
dashboard were produced by sending real transcripts to a configured Bolna agent
and mapping the answers back through the same code a phone call uses.

**Telephony is not connected.** Buying an Indian phone number requires KYC
verification, which was not something to complete for a prototype. Attaching a
number is configuration, not new code: the webhook receiver, the mapper and the
dashboard all treat a real call and a simulated one identically, and every
simulated row is marked as such in the UI and in the stored data.

## Tests

```bash
python -m pytest -q      # 71 tests, no network, no API key required
```

The suite covers transcript parsing, the extraction guards, the mapper's
tolerance of malformed payloads, webhook handling, store integrity and the
dashboard's labelling of simulated data.

## Configuration

| Variable | Purpose |
|----------|---------|
| `BOLNA_API_KEY` | Bolna API key, from Developers in the dashboard |
| `BOLNA_AGENT_ID` | The agent the extractions attach to |
| `MEOWW_STORE` | Path to the JSONL store, default `data/calls.jsonl` |
| `MEOWW_WEBHOOK_SECRET` | Shared secret for the webhook URL query string |
| `ANTHROPIC_API_KEY` | Optional, for the alternative Claude extractor |

Set `MEOWW_WEBHOOK_SECRET` before exposing the server publicly. Bolna does not
document a signature header, so the endpoint checks a secret in the query
string instead; without one, anyone who learns the URL can write to the store.
