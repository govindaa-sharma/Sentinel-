# Rowan 
website link: https://rowans.streamlit.app/

A natural-language-to-SQL agent that plans, writes, and self-corrects SQL against a real database —
and, for any action with real consequences (writes, deletes), pauses and requires a different,
authorized human to explicitly approve it before it executes.

Built to demonstrate three specific patterns: a **Reflexion-style self-correction loop**, disciplined
**loop engineering** (every run ends in a named terminal state, nothing loops or hangs indefinitely),
and a **human-in-the-loop approval gate** that is enforced structurally — not by trusting the model's
judgment, but by making the write database credential unreachable from anywhere except one
role-gated, separation-of-duties-checked endpoint.

## Why this exists

Most "AI agent" portfolio projects stop at "it calls an LLM and does a thing." This one is about what
happens *around* that call: what happens when the model is wrong, what happens when a request is
risky, and what happens when someone tries to trick it. All three are tested, not assumed — see
[`benchmarks/results.json`](benchmarks/results.json) for real results and
[`LEARNINGS.md`](LEARNINGS.md) for the bugs and vulnerabilities found and fixed along the way,
including a real prompt-injection vulnerability caught by the project's own adversarial benchmark.

## Architecture

```
User request (authenticated)
      │
      ▼
  Planner  ──▶  Codegen  ──▶  Risk Classifier  ──┬──▶  LOW risk  ──▶  Sandbox Executor  ──▶  Verifier
                    ▲                             │                                             │
                    │                             │                                       pass ◀─┴─▶ fail
                    └──────── Critic (retry, max 3) ◀───────────────────────────────────────────┘
                                                    │
                                              HIGH risk
                                                    │
                                                    ▼
                                          Approval Gate (writes audit
                                          record, execution stops here)
                                                    │
                                                    ▼
                                    Human approver reviews + decides
                                    (separate person from requester,
                                     enforced server-side)
                                                    │
                                        approve ──▶ Sandbox Executor (write role)
                                        reject  ──▶ logged, nothing executes
```

**Key design decisions:**

- **Risk classification runs after Codegen, on the real generated SQL — never on the user's phrasing
  or the model's self-reported metadata about its own output.** An earlier version trusted Codegen's
  self-labeled `operation` field; the adversarial benchmark found this could be fooled (a write
  smuggled inside SQL self-labeled `"SELECT"`). Fixed by scanning the real SQL text directly and
  rejecting multi-statement queries outright. Full writeup: [`LEARNINGS.md`](LEARNINGS.md).
- **Two separate Postgres roles** — `sentinel_reader` (SELECT only) and `sentinel_writer` (full
  access) — enforced by the database itself, not application logic. Proven directly: the reader role
  cannot execute a write no matter what SQL reaches it, confirmed by deliberately trying.
- **The write credential is reachable from exactly one code path in the entire system** — the
  `/approvals/{id}/approve` endpoint, gated by role (`approver` only) and separation of duties
  (an approver can never approve their own request, enforced server-side).
- **Every stop-rule is documented explicitly** in [`LOOP.md`](LOOP.md) — retry caps, dual timeouts,
  what happens on model refusal, and why the approval gate is a true stop, not a delay.

## Real results (not projected — from an actual benchmark run)

40-case benchmark: 20 read, 15 write, 5 adversarial. Full results in
[`benchmarks/results.json`](benchmarks/results.json).

| Metric | Result |
|---|---|
| Read first-pass success rate | 18/20 (90%) |
| Read success including retries | 19/20 (95%) |
| Write requests correctly gated (never auto-executed) | 15/15 (100%) |
| Adversarial cases where the safety boundary held | 5/5 (100%) — after one real fix, see below |
| Judge-vs-human agreement (independently graded sample) | 14/15 (93%) |

**One real vulnerability was found and fixed via this benchmark, not assumed away:** an adversarial
prompt smuggled a write inside SQL that Codegen self-labeled as a `SELECT`. The original risk
classifier trusted that label and would have routed it toward autonomous execution; it only failed to
run because the malformed multi-statement string errored out during execution — an accident, not a
guarantee. Fixed by classifying risk from the real SQL text, independent of any model-reported label,
and rejecting multi-statement queries outright. Verified fixed by re-running the adversarial suite.
Full details: [`LEARNINGS.md`](LEARNINGS.md).

## Stack

LangGraph · FastAPI · PostgreSQL (Neon) · Docker (local sandbox execution) · Gemini API /
local Llama via Ollama (swappable) · Pydantic · JWT auth · Streamlit (approval dashboard)

## Running it locally

```bash
pip install -r requirements.txt
# set up .env — see .env.example
python create_tables.py
python seed_data.py
uvicorn app.main:app --reload        # backend, in one terminal
streamlit run dashboard/app.py       # dashboard, in another
```

## Known limitations (stated honestly, not hidden)

- The Docker sandbox provides process/resource isolation, not full network isolation — it must reach
  the database, so true network isolation was never achievable; the real safety boundary is the
  database role separation, proven independently. Documented in `LOOP.md`.
- The deployed (Render) version runs without Docker-in-Docker and falls back to direct execution;
  the database-role security boundary is identical, only the container isolation layer differs.
- If the Planner refuses a request in plain language, that refusal is currently passed to Codegen as
  if it were an instruction, and Codegen has been observed to hallucinate an unrelated action rather
  than also refusing. The safety boundary held in testing regardless (the hallucinated action was
  still correctly classified and blocked) — but this is a known correctness gap, not yet fixed.
- Self-serve signup only creates `requester` accounts; `approver` accounts are provisioned separately
  by design (a self-serve path to an approval-granting role would undermine the point of the gate).

See [`LEARNINGS.md`](LEARNINGS.md) for the full build journal, and [`LOOP.md`](LOOP.md) for every
termination condition in the system.
