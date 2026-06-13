# LLM Council Transcript — 2026-06-13 18:13

## Framed question

How do we get the A2A banking agent (gemini-3.5-flash, mandatory) to actually PASS
tasks (match the final DB hash) when it's scoring 0/5 on the test split and the
failures are mostly correctness (wrong account choices, trusting adversarial users,
dropped/mis-sequenced actions), with some timeouts and 429s? Scoring is 100% on the
final DB state (all-or-nothing; extra writes also fail; premature termination = 0;
speech is not graded). What concrete features to build, and what to stop doing?

## Advisor responses (condensed)

### The Contrarian
The prompt rules are theater — gemini-3.5-flash ignores advisory text. There is NO
mechanism to enforce the rules. Build executable constraints, not prose: pre-flight
eligibility checks, dependency/sequence enforcement, post-action state verification,
and a task-completion validator. Make the LLM a state-machine executor. Stop tuning
prompts, optimizing KB search, and adding research.

### The First Principles Thinker
This is a specification problem, not a reasoning problem. The agent's only job: call
the exact right tools in the right order with right args, then stop — producing the
gold DB state with NO extra writes. Trace the gold sequence per task, build minimal
deterministic decision logic, test tool-calls against gold. Stop: self-correction,
research multi-calls, KB-search optimization, conversation naturalness.

### The Expansionist
One deterministic decision layer removes ~70% of the decision surface and passes a
whole CLASS at once. Build a Deterministic Eligibility & Sequencing Engine the LLM
fills in (not decides): eligibility matrix (age/deposit/tenure/tier-limits/perks),
sequencing DAG (dependencies + conflict detection), post-execution verification.
Reuses the account_advisor pattern. Blocks adversarial/sequencing/eligibility/fee/
refusal failure modes simultaneously.

### The Outsider
They're trying to make the LLM smarter; they should make it dumber. Validation/
self-correction is invisible to the DB-only grade. Push logic out of the LLM into
code. Use the fee calculator for every fee question. [Also suggested collapsing to
one agent + deleting the research agent — REJECTED by chairman: violates the
mandatory compose contract.] Valid kernel: fewer LLM calls (kills 429s/timeouts);
deterministic execution; static policy lookup over LLM research.

### The Executor
Build order (smallest-change-first): (1) ensure LLM-as-judge/self-correct is OFF in
the active path; (2) deterministic eligibility gate-checker called before every
write; (3) sequence-dependency checker; (4) deterministic dispute/tier-limit checker;
(5) prefer KB/deterministic over research. Verify each cheaply. Stop: LLM-judge
validation, multi-variant research, speculative tool unlocking (extra writes).

## Peer review (chairman-consolidated)
- Strongest convergence: deterministic eligibility + sequencing + verification.
- Biggest blind spot flagged: "collapse to one agent / delete research" violates the
  contract (would disqualify) — keep architecture, make decisions deterministic.
- Missed by all: whole-DB-hash means EXTRA writes also fail → need an explicit
  "do exactly the required writes + verify before done" gate, not just "don't miss".
- Caution (from the fee-tool experience): hand-encoded rules must be KB-grounded and
  unit-tested against an oracle, or a confident-but-wrong rule is worse than none.

## Chairman verdict — build list (all implemented this session)
1. Deterministic ELIGIBILITY checker (age / min-deposit / tenure / perks) per product.
2. Deterministic OPERATION SEQUENCING planner (order-dependent dependencies + conflicts).
3. Deterministic DISPUTE-CAPACITY / per-tier-limit checker.
4. VERIFY-BEFORE-DONE: re-check state; do only required writes; don't trust tool success.
5. STOP: confirm LLM-judge/self-correct off in active (LEAN) path; prefer deterministic + KB over research.

## One thing first
Eligibility + sequencing engine (grounded + unit-tested), wired so the agent calls it
before acting — it covers the most failing trap classes at once.
