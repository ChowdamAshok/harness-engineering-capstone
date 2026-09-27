# Reflection Brief — Harness Engineering Capstone

**Name:** Ashok
**Date:** 2026-09-27

**Environment**

- Model(s): `claude-haiku-4-5-20251001` for System 1; System 2 used the Anthropic model-authoritative token-counting methodology.
- OS / Python: Linux / Python 3.13.0
- Approx. API spend: System 1 recorded an estimated total cost of **$0.1135** across the eight claims. I did not capture a consolidated spend figure for Systems 2–4.

---

## Part 1 — Per-system

### System 1 — Agentic loop

1. **Loop control.** Quote the `stop_reason` sequence from one trace. Name the file and function that decides continue-vs-stop, and how.
   → In `/workspace/capstone-evidence/system-1-claims/claim_04_neighbor_injury.jsonl`, the `stop_reason` sequence is `tool_use`, `tool_use`, `tool_use`, `tool_use`, `end_turn`. The loop uses the model's `stop_reason` rather than parsing assistant text or relying on a fixed iteration count to decide whether another turn is needed. The run produced 5 turns for `claim_04_neighbor_injury`, ending when the model returned `end_turn`. The corresponding run was `20260927_054040`, recorded in `/workspace/capstone-evidence/system-1-claims/summary.md`.

2. **Anti-pattern.** Name one anti-pattern `test_antipatterns.py` checks for. What would break in your run if the loop used it?
   → One anti-pattern checks for a fixed integer-literal iteration cap in the agent loop. Another check ensures the loop does not decide from string membership in assistant text. If the loop used a fixed cap, a claim requiring more tool interactions could stop before the model returned `end_turn`, making the workflow incomplete. The anti-pattern checks are in `tests/test_antipatterns.py`, and the successful test run was **29 passed** in `/workspace/capstone-evidence/system-1-claims/pytest.txt`.

3. **Tool design.** Pick two tools with overlapping inputs. How do the descriptions prevent misrouting? What did a structured tool error let the agent do that a generic string would not?
   → Two tools in `claims_intake/tools.py` that can receive claim-related information are `record_claim_fact` and `classify_claim`. Their tool descriptions distinguish whether the operation is recording evidence or assigning a claim classification, which gives the model a clearer routing boundary. The tool interface also returns structured errors containing fields such as `error_category` and `is_retryable`. That lets the loop distinguish a retryable/transient failure from a permanent error instead of treating every failure as an opaque string.

4. **Your numbers.** Quote the turn count and cost for one claim. How does it differ from the README sample, and why?
   → For `claim_04_neighbor_injury`, the actual run recorded **5 turns** and an estimated cost of **$0.0222**, with 17,675 input tokens and 906 output tokens. The evidence is in `/workspace/capstone-evidence/system-1-claims/summary.md` and the trace in `/workspace/capstone-evidence/system-1-claims/claim_04_neighbor_injury.jsonl`. I could not verify a corresponding `claim_04_neighbor_injury` sample in the local README, so I am not inventing a numerical difference. My recorded values are therefore the authoritative numbers for my run.

### System 2 — Context strategy

5. **The reduction.** From `budget.json`: baseline tokens, assembled tokens, reduction %. Which section dominates the assembled context, and why keep it verbatim?
   → `/workspace/capstone-evidence/system-2-retail/budget.json` records a baseline of **38,708 tokens**, an assembled context of **16,867 tokens**, and a **56.43% reduction**. The `active` section dominates at **15,789 tokens**, compared with `case_facts` at 204, `resolved_refund` at 393, and `resolved_subscription` at 499. The active section is the live working context, so preserving it byte-exact avoids changing the current state while historical resolved sections can be compressed.

6. **Summarize vs preserve.** State the rule for what gets summarized vs kept byte-exact, citing your per-section token numbers.
   → The context strategy compresses resolved historical material while preserving the active working context byte-exact. In my run, `resolved_refund` was reduced to **393 tokens** and `resolved_subscription` to **499 tokens**, while `active` remained **15,789 tokens** and `case_facts` was **204 tokens**. This gives the model a much smaller historical context without rewriting the current active conversation. These values are recorded in `/workspace/capstone-evidence/system-2-retail/budget.json`.

7. **Facts block.** Compare `eval.jsonl` to `eval_control.jsonl`. Which question regressed, and what does that prove?
   → All six questions passed in `/workspace/capstone-evidence/system-2-retail/eval.jsonl`. In `/workspace/capstone-evidence/system-2-retail/eval_control.jsonl`, **Q6 failed**: the control response did not provide the required structured status token, while the assembled-context evaluation returned `in_progress`. This shows that preserving the structured facts/status block protects information that can be lost when context is handled without the designed facts block. The evidence is the difference between the evaluation and control artifacts.

### System 3 — Claude Code config

8. **Path-scoped rules.** Quote the glob frontmatter from one rule file. Why is it better than a directory-level CLAUDE.md for cross-cutting conventions?
   → The React rule uses `paths: ["src/components/**/*", "src/pages/**/*"]` in `.claude/rules/react.md`. This scopes the React conventions to the files where they apply instead of applying them broadly to unrelated files. Path-scoped rules are better than a directory-wide `CLAUDE.md` when the same repository contains different technologies or conventions, because each rule activates only for matching files.

9. **Forked skill.** Quote the `context: fork` and `allowed-tools` lines. What does running forked + read-only buy you? What breaks without it?
   → `.claude/skills/deploy-check/SKILL.md` contains `context: fork` and an `allowed-tools` list consisting of `Read`, `Grep`, `Glob`, and read-only Git/GitHub commands such as `git status`, `git diff`, `git log`, and `gh pr view`. Forking keeps verbose discovery work out of the main session and returns a concise result, while the allowlist prevents the skill from modifying files, pushing changes, or deploying. Without the fork, the main context would receive the discovery noise; without the read-only allowlist, the validation task would have a larger modification/deployment blast radius. The validator result for this configuration was **OK**, in `/workspace/capstone-evidence/system-3-claude-config/validator.txt`.

10. **Scope.** From the validator output: project-level vs user-level scope. Give one example of each from this config.
    → The project-level example is `.claude/skills/deploy-check/`, which belongs to the repository configuration. The user-level example documented by the configuration is `~/.claude/skills/deploy-check-strict/`. The same distinction is used for project and user command configurations, with the project `/review` command under `.claude/commands/review.md`. The configuration passed the validator with `OK`, recorded in `/workspace/capstone-evidence/system-3-claude-config/validator.txt`.

### System 4 — Orchestration

11. **Push work down.** Defects the SQL query returned vs warm-tier total. Name the indexed query. Why does the model never see the full history?
    → The warm database contained **40 total defects**, while the SQL query for the current shift window returned **0** for the timestamp used in my live check. The query is `SELECT * FROM defects WHERE ts > ? ORDER BY ts DESC LIMIT ?`, implemented by `defects_since()` in `shift_monitor/warm.py`, with indexes on `shift, ts` and `ts`. The filtering and limit happen in SQL, so the model receives only the relevant bounded result rather than the complete warm-tier history. The live check and database are recorded in `/workspace/capstone-evidence/system-4-shift-monitor/warm.sqlite`.

12. **Crash recovery.** The resume-vs-fresh decision and its staleness threshold (`recovery.py`). Why is a fresh start with an injected summary sometimes more reliable than resuming?
    → `recovery.py` defines `STALE_RESUME_THRESHOLD_MINUTES = 30`. An incomplete run is resumed only when its latest step is no more than 30 minutes old; otherwise the decision is `fresh`. A fresh run with the previous findings captured as a summary avoids depending on potentially stale or partially corrupted working state while still preserving the important conclusions. The recovery logic was exercised by the **33-test** System 4 suite.

13. **Small state.** Byte size of your `hot_state.json`. Why does the budget matter for a system run once per shift, indefinitely?
    → My `/workspace/capstone-evidence/system-4-shift-monitor/hot_state.json` is only **643 bytes**. Keeping hot state small matters because the system runs repeatedly across shifts, so state can otherwise grow without bound and eventually become expensive or difficult to reason about. A bounded state representation makes each new shift start from a predictable amount of durable context. The recorded 643-byte artifact demonstrates that the state remained far below the intended small-state budget.

---

## Part 2 — Synthesis

14. **Three layers.** Point to a file/artifact for each layer and justify.
    → **Model:** `/workspace/capstone-evidence/system-1-claims/summary.md` records the model as `claude-haiku-4-5-20251001`; this is the reasoning component making tool-use decisions.
    → **Harness:** `/workspace/capstone-evidence/system-2-retail/budget.json` shows the harness controlling context assembly, token budgets, compression, and preservation rules.
    → **Orchestration:** `/workspace/capstone-evidence/system-4-shift-monitor/hot_state.json` and the shift-run artifact show durable state and scheduled/shift-level coordination outside a single model turn. Together these separate model reasoning, execution/context controls, and long-lived workflow state.

15. **Deterministic vs prompt.** Cite one behavior guaranteed in code (terminal tool, read-only allowlist, atomic write, byte budget) and one guided by prompt. When is each right?
    → System 3 provides a deterministic example: the `deploy-check` skill's `allowed-tools` list restricts it to read-only operations, so the restriction is enforced by configuration rather than merely requested in prose. A prompt/tool description provides a softer control: System 1's tool descriptions guide the model toward the appropriate claim operation. Deterministic enforcement is appropriate for safety-critical boundaries such as write access, while prompts are useful for semantic choices such as which available tool best matches the task.

16. **Context, two faces.** Compare context management in System 2 (intra-session) and System 4 (cross-session) with cited numbers from both. Same principle, different mechanism — how?
    → System 2 reduced an intra-session context from **38,708 to 16,867 tokens**, a **56.43% reduction**, while preserving the **15,789-token active** section. System 4 handled cross-session state by keeping `hot_state.json` at only **643 bytes** and querying the warm database with SQL-side filtering rather than exposing all **40** stored defects. Both systems apply the same principle of keeping the model's working context bounded and relevant, but System 2 uses summarization/preservation within a conversation while System 4 uses durable state, time-window queries, and recovery rules across runs.

17. **Reliability you can't see in one run.** Name one behavior a test guarantees that a single successful run would not reveal. Why does it matter before shipping?
    → System 1's `test_antipatterns.py` checks that the loop does not rely on a fixed integer iteration cap or string matching against assistant text. A single successful run could still pass even if one of those fragile mechanisms existed because the particular claim might finish before exposing it. The **29 passed** test result in `/workspace/capstone-evidence/system-1-claims/pytest.txt` therefore provides evidence about the implementation's behavior beyond one successful example.

18. **Blast radius.** Pick one system. What's the blast radius if it misbehaves, and what's the kill switch? Ground it in that system's tools, enforcement points, and state.
    → For System 3, a bad shared Claude Code rule or skill could affect developers using the repository configuration, so the blast radius is broader than one model turn. The `deploy-check` skill limits itself to `Read`, `Grep`, `Glob`, and read-only Git/GitHub commands, which prevents the skill itself from modifying files, pushing changes, or deploying. The practical kill switch is to stop invoking the project skill/command while the configuration is corrected; the validator and **35 passing tests** provide enforcement before the configuration is relied upon.

---

## Part 3 — Honest assessment

19. **What broke.** One thing that failed first try in your environment, and how you fixed it. (If nothing, what you checked to be sure.)
    → During System 4 verification, I initially tried to use a `WarmDB` class name, but the implementation actually defines `WarmStore` in `shift_monitor/warm.py`. I checked the implementation and changed the verification to use the actual `WarmStore` class and its `defects_since()` method. After correcting that mismatch, the System 4 suite completed with **33 passed**, and the warm database verification showed **40 total defects**. This was a useful reminder to inspect the implementation rather than assume a class name from memory.

20. **What you'd change.** One architectural decision you'd make differently, grounded in what you observed.
    → I would make the reference time for a shift run explicit and injectable. In my System 4 run, the recorded fixture summary described defects for the replayed shift, while the live `defects_since()` query using the current timestamp returned **0** because the stored timestamps were older than that live window. Making the run's clock/reference timestamp explicit would make replayed fixtures and live time-window queries deterministic and easier to compare. The relevant evidence is `/workspace/capstone-evidence/system-4-shift-monitor/run-shift.txt` and the warm database/query verification.