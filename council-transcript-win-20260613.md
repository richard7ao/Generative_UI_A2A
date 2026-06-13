# LLM Council Transcript — "How do we win the A2A Hackathon?" (2026-06-13)

(HTML report intentionally skipped per user instruction.)

## Framed question
We want to WIN the A2A Hackathon (tau2-bench banking). Required: a personal agent
(talks to a simulated customer, relays to CS) + a cs agent (bank tools + KB); optional
research agent. All MUST run on gemini-3.5-flash. Architecture mandatory (personal + cs
+ redis; personal->CS via CS_AGENT_URL). Scoring: 100% on final DB hash, all-or-nothing,
extra writes fail, premature termination = 0, speech not graded. FINAL MARK = 3 pairings:
50% (your personal + your CS) / 25% (your personal + held-out CS) / 25% (held-out personal
+ your CS). Marking perturbs CUSTOMER data, not our KB. META-FACT: ~655 lines of tested
deterministic tools + prompt rules + async fixes were built but NEVER deployed — every 0/X
eval graded a stale build. We've never measured an improvement. Stack is now free.

## Advisor responses (condensed)

**Contrarian:** Right code, wrong container. The 37-min build predates banking_rules.py /
account_advisor.py, so the agent free-reasons eligibility (the known failure mode).
"Tests pass" ≠ "agent uses them." Rebuild, deploy, run ONE task, watch logs to confirm the
tool is actually CALLED and the DB matches. Then 80/20 toward the CS agent. Stop prompt/
research/KB tuning until tools are proven to fire.

**First Principles:** Winning = exact deterministic execution (right tools, right order,
right args, gold DB, nothing extra, clean stop). LLM's job is routing, not deciding; the
rules engine decides. The real lever is the deployment gap. Deploy banking_rules; wire a
check-before-write; measure the delta. CS ~70% effort, personal ~20% (faithful relay),
research ~10%.

**Expansionist:** The undervalued lever is the PERSONAL agent. It's in 2 of 3 pairings
(75% of score) yet treated as a thin relay. Make it bulletproof + deterministic: faithful
context-passing (no paraphrase), pre-flight request validation, never decide eligibility it
lacks state for, handle CS "no/ineligible". A robust interface composes with ANY held-out
CS agent — that's the only lever for the 25% where a stranger's CS does the banking.

**Outsider:** Three red flags: (1) optimizing blind against a ghost system — deploy +
baseline first; (2) treating a 50/50 cross-pairing scoring symmetrically — both agents must
work with strangers' agents; stress-test cross-compatibility; (3) building for the wrong
failure mode — only DB state counts, stop polishing dialogue/reasoning chains.

**Executor:** Next-hour plan: (0:00) rebuild `docker compose up -d --build`, verify agent
card; (0:05) smoke 1 task; (0:15) run ~5 tasks to results/baseline-v1 and compare; (0:35)
if tools aren't being called, grep logs and add explicit prompt examples; (0:50) full train
only if baseline good. Stop: evals against stale containers, prompt edits without rebuild,
full splits before a 5-task baseline.

## Peer review (chairman-consolidated)
- Unanimous: DEPLOY + MEASURE is the #1 act; we've never measured our own work.
- Genuine clash resolved: "CS is 75%" (Contrarian/First-P) vs "personal is 75%"
  (Expansionist) — BOTH true; the weights are symmetric (each agent = 50% your-pair +
  25% one cross-pairing). So both matter equally.
- Blind spot caught: our deterministic tools live in OUR cs agent, so the 25% held-out-CS
  pairing gets NONE of them — the personal agent's faithful-relay robustness is the ONLY
  lever there, and it's been neglected.
- Missed by all but implied: deploying != using; must read transcripts/logs to confirm the
  model actually calls the tools, and that results generalize to perturbed customer data.

## Chairman verdict
1. DEPLOY now (done this session) and MEASURE on real tasks — confirm the tools are CALLED
   and the DB matches. Stop flying blind.
2. Both agents are ~75% of the weighted score. CS = correctness via the deterministic
   tools (built; now deployed). PERSONAL = faithful-relay robustness (the neglected lever
   for the held-out-CS 25%): pass intent verbatim, validate before relay, surface CS's
   eligibility verdicts faithfully, never invent writes.
3. STOP: prompt-only iteration without rebuild, research-agent tuning, dialogue/KB polish.
4. ONE THING FIRST: rebuild + smoke a trap task (task_001 fee / task_014 adversarial /
   task_043 sequencing); read the transcript to confirm the deterministic tool fired and
   the reward flipped 0 -> 1. That single measurement tells us if the whole approach works.
