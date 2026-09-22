# Sentinel — Build Journal

A running log of real decisions, bugs, and honest limitations hit while building this project.
Updated as we go, not reconstructed from memory at the end — so detail stays accurate.

---

## Design decisions (and why)

**Risk classification runs after Codegen, not before.**
Originally considered having the Planner classify READ vs WRITE from the user's natural-language
phrasing. Rejected: intent can be misleading ("clean up old records" sounds harmless but could be
a DELETE touching thousands of rows). Risk Classifier now runs on the *actual generated SQL* via
a deterministic rule (`operation in {UPDATE, DELETE, INSERT} → HIGH`), not an LLM guess — a security
boundary should not depend on a model's judgment.

**Any write is HIGH risk, regardless of estimated row count.**
Deliberately conservative default. Could later relax (e.g. single-row UPDATE = medium risk) but
starting maximally cautious and relaxing later — with evidence — is safer than the reverse.

**Docker sandbox does not have true network isolation.**
Initially planned "no network access" for the sandbox container. Corrected once we realized the
container must reach Neon (an internet-hosted DB) to do anything at all — full isolation would
break the core function. Real isolation here is about *capability* (the container can only run
one SQL statement, nothing else) plus resource/time limits, not network denial. The actual security
boundary is the two-DB-role system, proven independently at the Postgres permission level.

**Two independent timeouts, not one.**
Postgres-level `statement_timeout` (5s, inside the sandbox script) + an outer `subprocess` timeout
(10s, in `sandbox_executor.py`). Defense in depth: if the inner timeout somehow failed to fire
(e.g. container hangs before even reaching Postgres), the outer one still guarantees the function
can't block forever.

**Verifier uses three layers, cheapest first.**
(1) Did it error — free, just reading a field. (2) Rule-based structural checks — cheap.
(3) LLM semantic sanity check — only runs if 1 and 2 pass, since it's the only one that costs
an API call. Never spend an LLM call checking something a plain `if` could catch first.

**Critic and Verifier have separate responsibilities.**
Verifier decides *is this result correct*. Critic decides *do we retry or give up*. Keeping these
separate (rather than one node doing both) makes each easier to reason about and test independently
— proven directly when we unit-tested Critic's stop-rule in complete isolation from any LLM call.

---

## Bugs caught (and how)

**Critic node had two conflicting edges to `codegen`.**
Wrote both `add_conditional_edges("critic", route_after_critic, {...})` AND a leftover
`add_edge("critic", "codegen")` unconditionally, left over from an earlier draft. This meant
critic would always proceed to another Codegen attempt even after `terminal_state` was set to
`FAILED_MAX_RETRIES` — the stop-rule would never actually stop the graph. Caught by manually
tracing execution order edge-by-edge rather than trusting that the code "looked right."
**Lesson:** always trace a new graph wiring by hand, node by node, before trusting it — a graph
that compiles without error is not the same as a graph that's logically correct.

**Missing `verifier → *` edges in one draft.**
A revision fixed the critic bug but dropped the `add_conditional_edges("verifier", ...)` block
entirely, leaving verifier with no outgoing edge at all. Same root cause as above: partial edits
to a graph file without re-tracing the whole structure afterward.

**`sentinel_reader` initially failed to connect — wrong root cause assumed twice.**
Real cause was two separate .env mistakes: (1) a placeholder password left in `.env` instead of
the real one set via `ALTER ROLE`, (2) a dropped `e` in the Neon hostname during copy-paste
(`p-green-pond...` instead of `ep-green-pond...`). Fixed by replacing fragile one-off terminal
commands with a reusable `scripts/check_roles.py` that reads from `.env` via `get_settings()`
instead of hand-typed connection strings — removed an entire class of typo bugs going forward.

---

## Honest limitations found (candidates for the eval/adversarial test set)

**Seed data makes ">10% change" too common to be a meaningful filter.**
The seed script nudges every client's risk score by up to ±15% every month, so a >10% swing is
the *common* case, not rare — one query returned 39 of 50 clients matching. Not a bug in the SQL,
but a synthetic-data realism issue. Good case study for why the Verifier's semantic sanity check
matters — high match rates against an intuitively "selective" filter should be treated as suspicious,
not immediately trusted just because the query is syntactically correct.

**Codegen sidesteps unanswerable requests instead of failing loudly.**
Asked it to "show clients from nonexistent_table_xyz" expecting a Postgres error to force a retry.
Instead it queried `information_schema.tables` to check existence and returned `{'exists': false}`
— valid SQL, technically correct, but doesn't actually answer what the user asked. The Verifier's
sanity check passed it, since the result was structurally clean. This is a real gap: technically-safe
SQL is not the same as SQL that honors user intent. Logged as a known limitation and a genuinely
good adversarial test case for the Week 4 eval benchmark, not something to quietly fix and hide.

**Self-correction mechanism proven safe, not yet proven to *improve* results.**
Deterministically confirmed: (1) Critic's retry-count/stop-rule logic works correctly in isolation,
(2) Verifier correctly detects a real Postgres error (bad column reference) and triggers retries.
Not yet directly observed in one live run: Codegen receiving `error_feedback` and producing a
genuinely corrected query. Attempts to force this via one hand-picked ambiguous prompt succeeded
on the first try (clean schema, capable model) — meaning the loop had nothing to correct. Real
evidence of correction-in-action will most likely come from the full Week 4 benchmark, not a
single contrived test. Resume claims about "improved success rate via self-correction" should be
grounded in that benchmark's actual numbers, not assumed in advance.

---

## Format for future entries

```
**Short title of the decision/bug/limitation.**
What happened, what we assumed vs. what was actually true, how it was caught, what we did about it.
```

**Approval gate: separating "propose" from "execute" into different code paths.**
The agent graph never calls the sandbox executor for HIGH-risk actions — the Approval Gate node
only writes a `PendingApproval` audit record and the graph run ends there. Execution only happens
later, from a completely separate code path (`/approvals/{id}/approve`), triggered by a human.
This means the write DB credential is reachable from exactly one function call in the entire
codebase, gated behind both a role check and a self-approval check — not a matter of the LLM
"choosing" to behave safely, but the write capability being structurally unreachable any other way.

**Authorization checks must run before the irreversible action, never after.**
In the approve endpoint, the self-approval check (`requester_id == current_user.id`) and the
already-resolved check both run *before* `run_sandboxed_query` is ever called — not after, and not
as cleanup. Proven directly: attempted self-approval on my own request → correctly rejected with
403, before any query ran. Attempted to approve an already-resolved request → correctly rejected
with 400. Both failure paths were deliberately tested, not just assumed to work from reading the code.

**Re-fetching state fresh from the DB inside each endpoint, not trusting request-time assumptions.**
Both approve/reject re-query `PendingApproval` and check `status == pending` right before acting,
rather than trusting any earlier read. This guards against (though doesn't fully solve) a race
condition where two approvers act on the same request near-simultaneously. Full protection would
need a DB-level lock or unique constraint — noted as an honest limitation, not claimed as solved.