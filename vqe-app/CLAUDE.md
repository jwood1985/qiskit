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
- For React frontends, use this color schema where possible: #0D1B99, #FF7F27, #060242, and #C7C7C7
- For React frontends, the UI(s) shall focus on simplicity, consistency, high contrast, and accessibility to enhance user experience
- The UI(s) shall employ an "F" pattern for how the content is tracked over the page
- All errors shall be gracefully handled and logged, where appropriate
- All exposed API endpoints must have tests

# Goal

- This is a project with two components: (1) a React UI for tracking telemetry for variational quantum eigensolvers (VQEs) across different providers (i.e., Qiskit, Braket, etc.); and (2) API calls to those quantum providers for calculating the ground state for the molecule LiH using VQE.

# Guardrails

- Coding shall not be done in violation of the principles outlined in this document.
- Plans must be approved by me prior to proceeding.
- Justify your work - why you do something is as important as the how.

# Tasks

- Produce a user-friendly React-based UI for connecting to the quantum API providers. 
- The VQE ground state shall be calculated for LiH.
- Determine what is nedeed both for classical compute and quantum compute for the VQE approach.
- Encode the quantum portion in an ansantz.
- Add OpenTelemetry signals for the classical optimizer portion, sending to qof78400.
- There shall be a Settings page for the API providers used (Qiskit, Braket, etc.), any API endpoints that need exposing, any API tokens that need persistence and security, etc.
- The main page will allow you to select a molecule for ground state energy calculations. Choices are LiH (default) and H2, for now.
- There shall be a top navbar that is fixed with other navigation options (i.e., Settings, etc.).

# Persistence

- Every 2000 tokens, persist your progress to `CLAUDE.md`.
- Persist to `CLAUDE.md` before compactification.

# Documentation

- Document this project to a `README.md` file.
- Documentation should be clean and easy to understand.
- The README.md file should have a Quick Start section, if relevant.
- Documentation should be performed before every major change.

# Progress

Initial build complete (single session). Plan approved up front via the four
clarifying questions:

- OTel target: `qof78400.live.dynatrace.com` (Dynatrace OTLP /api/v2/otlp)
- Execution: real provider credentials required, no simulator fallback
- Token storage: Fernet-encrypted file at `~/.vqe-app/secrets.enc`
- Layout: subfolder `vqe-app/` inside the Qiskit repo

Delivered:

- `backend/` — FastAPI app (`app.main`) with three routers:
  `/api/settings`, `/api/providers`, `/api/vqe`. VQE pipeline =
  PySCF/qiskit-nature Hamiltonian → Jordan–Wigner → UCCSD (or
  EfficientSU2) ansatz → SciPy COBYLA driving a Qiskit Estimator
  primitive. OTel signals: span per run, counter per iteration, gauge
  for current energy → Dynatrace OTLP exporter. Token store is Fernet
  with atomic writes and `0600` key file.
- `backend/tests/` — 13 pytest cases covering all exposed endpoints,
  redaction of stored tokens, encrypted-on-disk persistence, run
  lifecycle (pending → running → succeeded/failed), and request
  validation. All passing.
- `frontend/` — Vite + React + TypeScript. Fixed top navbar (Home,
  Settings). Home page: molecule selector (LiH default, H2), provider
  selector with live status badge, ansatz selector, max-iter input,
  live energy-vs-iteration SVG chart. Settings page: forms for Qiskit
  (token, instance, channel), Braket (access key, secret, region,
  device), and Dynatrace (token). Theme.css applies the four-colour
  palette and F-pattern layout with high-contrast focus rings.
- README.md, Makefile, .gitignore.