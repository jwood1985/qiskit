# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

# 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

# 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

# 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

# 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

# Project-Specific Guidelines

- Find existing agentic skills and use them where relevant
- The provider interface shall be abstracted such that adding a new quantum provider (Qiskit, Braket, Azure, etc.) requires only implementing a defined interface — no provider-specific code outside that boundary
- Default to simulator backends (Qiskit Aer, Braket LocalSimulator, etc.) for all development; real hardware execution must be an explicit, opt-in choice surfaced in the UI to avoid burning credits
- Quantum jobs are asynchronous and may queue for minutes to hours; the UI and optimizer loop must handle the async job lifecycle (submitted → queued → running → completed/failed) without blocking
- API tokens and secrets shall be stored via OS keychain (or equivalent platform-native secure storage), never in plaintext config files or environment variables committed to source
- For React frontends, use this color schema where possible: #0D1B99, #FF7F27, #060242, and #C7C7C7
- For React frontends, the UI(s) shall focus on simplicity, consistency, high contrast, and accessibility to enhance user experience
- The UI(s) shall employ a dashboard-grid layout appropriate for dense telemetry display — fixed top navbar, sidebar for navigation, primary content area for charts/tables, information density prioritized over whitespace
- All errors shall be gracefully handled and logged, where appropriate
- All exposed API endpoints must have tests

# Goal

- This is a project with two components: (1) a React UI for tracking telemetry across the full hybrid classical-quantum workflow for variational quantum eigensolvers (VQEs) across different providers (Qiskit, Braket, etc.); and (2) API calls to those quantum providers for calculating the ground state of the molecule LiH using VQE.
- The success criterion is not "ship a working VQE app." It is "ship a working VQE app AND produce a documented inventory of observability gaps at the classical-quantum boundary." Both deliverables matter equally.

# Guardrails

- Coding shall not be done in violation of the principles outlined in this document.
- Plans must be approved by me prior to proceeding.
- Justify your work — why you do something is as important as the how.

# Tasks

- Produce a user-friendly React-based UI for connecting to the quantum API providers.
- The VQE ground state shall be calculated for LiH.
- Determine what is needed for both classical compute and quantum compute in the VQE approach.
- Encode the quantum portion in an ansatz.
- Instrument the full hybrid workflow with OpenTelemetry, sending to Dynatrace tenant `qof78400`. Capture, at minimum:
  - Classical optimizer iteration spans (per `minimize()` step)
  - Quantum circuit submission spans (per parametrized circuit evaluation)
  - Queue time, execution time, and shot count per job
  - Error mitigation method and configuration in use
  - Backend calibration metadata exposed by the provider at job submission time
  - Trace context propagation across the classical-quantum boundary (classical span → quantum job → result handling)
- Maintain a `GAPS.md` file at the repo root documenting:
  - Every place a provider API lacks observability hooks (e.g., no way to retrieve calibration data, no shot-level telemetry)
  - Every workaround required to propagate trace context across the classical-quantum boundary
  - Every telemetry signal that would be valuable but is not exposed by the provider
  - Every place provider APIs behave differently from each other in ways that complicate uniform instrumentation
  This file is a first-class deliverable, not an afterthought.
- There shall be a Settings page for the API providers used (Qiskit, Braket, etc.), any API endpoints that need exposing, and secure storage of API tokens (per the secret management guideline above).
- The main page will allow selection of a molecule for ground state energy calculations. Choices are LiH (default) and H2, for now.
- There shall be a fixed top navbar with other navigation options (Settings, GAPS dashboard, etc.).

# Persistence

- Maintain a separate `AGENT-MEMORY.md` file at the repo root for progress state. Do NOT persist progress into this `CLAUDE.md` file — `CLAUDE.md` is for guidelines and task definitions only.
- Persist to `AGENT-MEMORY.md` after each completed task (task-based trigger), not on token counts.
- `AGENT-MEMORY.md` should capture: completed tasks, in-progress task and current step, blockers encountered, decisions made and their justifications, and pointers to where work lives in the codebase.

# Documentation

- Document this project in a `README.md` file.
- Update `README.md` when public interface contracts, setup instructions, or supported providers change — documentation follows code, not the other way around.
- Documentation should be clean and easy to understand.
- The `README.md` file should have a Quick Start section.
