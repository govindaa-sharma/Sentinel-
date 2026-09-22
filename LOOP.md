# Sentinel — Stop-Rules and Loop Termination

Every place the system can stop, why, and how it's enforced. Written so any run can be traced to
exactly one of these terminal states — the graph never "just stops" without a named reason.

## Terminal states

| State | Meaning | Set by |
|---|---|---|
| `SUCCESS` | Query executed and passed verification | `mark_success` node |
| `PENDING_APPROVAL` | HIGH-risk action awaiting human decision | `approval_gate` node |
| `FAILED_MAX_RETRIES` | Self-correction exhausted its retry budget | `critic` node |
| `REJECTED_BY_HUMAN` | An approver explicitly rejected the action | `/approvals/{id}/reject` endpoint |

Every graph run ends in exactly one of the first three. Nothing in the graph can loop indefinitely
or exit without setting one of these.

## Retry budget

- **Hard cap: 3 attempts per request** (`MAX_RETRIES = 3` in `critic.py`), enforced by counting, not
  by asking the model whether it thinks it's done. `retry_count` is incremented by our own code on
  every pass through Critic — the LLM has no ability to claim "I need one more try" beyond this.
- On reaching the cap, `terminal_state = FAILED_MAX_RETRIES` is set and the graph's conditional edge
  (`route_after_critic`) sends execution to `END` — verified directly by forcing a guaranteed-failing
  query and confirming `retry_count` climbed 1→2→3 and the graph halted (not just "probably stopped").

## Timeouts (two independent layers, deliberately redundant)

- **Postgres-level:** `SET statement_timeout = '5000'` (5 seconds) inside the sandbox script itself.
  If a query somehow reaches Postgres and hangs, the database kills it.
- **Process-level:** `subprocess.run(..., timeout=10)` in `sandbox_executor.py`, 10 seconds. If the
  container itself hangs *before* even reaching Postgres (e.g. Docker startup issue), this catches it
  independently of the database-level timeout. Two layers so a failure in one doesn't remove all
  protection.

## Multi-statement rejection

- Any SQL containing more than one statement (split on `;`) is rejected outright by the risk
  classifier before execution is ever considered, regardless of risk tier. Added after the `adv_04`
  benchmark finding (see `LEARNINGS.md`) showed multi-statement SQL was the mechanism every
  successful prompt injection relied on to smuggle a write past a self-reported read label.

## The approval gate is a stop, not a delay

- `PENDING_APPROVAL` is not a retry state and not on a timer — the graph run for that request ends
  there. Nothing auto-resumes it. The only way execution continues is a separate, human-triggered
  HTTP call to `/approvals/{id}/approve`, gated by role (`approver` only) and separation of duties
  (`approver_id != requester_id`, enforced server-side before any execution).
- This means a HIGH-risk action has no time pressure or default outcome — an unresolved approval
  simply stays `pending` forever until a human acts, which is the intended fail-safe: absence of a
  decision never becomes an implicit "yes."

## What happens if the model refuses or claims uncertainty

- Known gap, documented honestly: if Planner refuses a request in plain language (observed in
  `adv_05`, where Llama replied "I cannot assist with dropping a table"), that refusal text is
  currently passed to Codegen as if it were a valid instruction, and Codegen has been observed to
  hallucinate an unrelated action rather than also refusing cleanly. The refusal did **not** bypass
  the risk classifier or approval gate in testing — the resulting hallucinated action was still
  correctly classified and blocked — but the *reasoning* took an unintended path. Not yet fixed;
  logged here and in `LEARNINGS.md` as a correctness issue distinct from the safety guarantee, which
  held regardless.

## What is explicitly NOT a stop-rule (by design)

- The system does not trust the model's own claim that a task is "done" or "correct" as a stopping
  condition anywhere. Every terminal state is set by our own deterministic code (a counter, a role
  check, a database write success/failure) — never by parsing an LLM's self-assessment out of its
  response text.