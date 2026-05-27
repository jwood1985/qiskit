# AGENT-MEMORY.md

Task-based progress journal. New entries appended after each completed task.
Format: one block per task with status, decisions, justification, and code
pointers.

---

## Completed tasks

### A0. Initial app scaffold (under previous CLAUDE.md)

- Stood up FastAPI backend + React/Vite frontend under `vqe-app/`.
- Three routers: `/api/settings`, `/api/providers`, `/api/vqe`.
- VQE pipeline: PySCF / qiskit-nature → Jordan–Wigner → UCCSD or
  EfficientSU2 → SciPy COBYLA → Qiskit Estimator primitive.
- 13 pytest cases covering every exposed endpoint.
- Frontend: F-pattern layout, fixed top navbar, Home + Settings.

Code lives at: `vqe-app/backend/`, `vqe-app/frontend/`.

### A1. Project documents updated to new CLAUDE.md

- Replaced `vqe-app/CLAUDE.md` with the user-supplied refresh.
- Created this `AGENT-MEMORY.md` per the new persistence rule (progress
  no longer goes in `CLAUDE.md`).
- Created `vqe-app/GAPS.md` populated with the first concrete set of
  classical-quantum boundary observability gaps (not stubs).

---

### A2. Phase B — provider interface refactor

- `app/providers/base.py` now defines a `Provider` Protocol + a Pydantic
  `ProviderField` so each provider declares its own form schema.
- `app/providers/registry.py` holds a slug → Provider dict; the package
  `__init__` imports each adapter so it self-registers on import.
- `QiskitProvider` and `BraketProvider` rewritten as classes
  implementing the protocol. Heavy imports are still deferred inside
  methods so the package loads in test environments without the wheels.
- `models.py` dropped the `ProviderName` enum; provider slug is now a
  free-form string validated at the route layer via
  `providers.get(slug)`. `SettingsView` / `SettingsPayload` regrouped
  under a `providers: {slug: ...}` dict so adding a new provider needs
  no schema edits.
- Routes (`providers`, `settings`, `vqe`) all iterate the registry.
  Grep verifies no provider-name branching outside the adapter modules.
- 17 pytest cases pass (13 + 4 new, including
  `test_new_provider_registers_without_touching_other_modules` which
  drops a stub `StubAzure` class into the registry and asserts it
  appears in `/api/providers` and `/api/settings` with zero edits to
  other modules — that is the literal verification criterion for D4).

**Known temporary breakage:** `frontend/src/api/client.ts` and the
Settings/Home pages still reference the previous payload shape
(`SettingsView { qiskit, braket, dynatrace }` instead of
`{ providers: {slug: …}, dynatrace }`). The frontend type-checks because
the types are declared locally and don't depend on the backend at
compile time, but the live `fetch` calls would mis-parse the response.
This is intentional: Phase E rewrites the frontend client + pages to
consume the new dynamic schema, so fixing this in Phase B would be
throwaway work.

---

## In-progress task

(none — Phase B complete, awaiting Phase C: simulator default + opt-in
real hardware)

---

## Decisions made and their justifications

### D1. Subfolder location `vqe-app/`

The host repo is Qiskit itself. Putting our app at the actual git repo
root would conflict with Qiskit's own README/CLAUDE/etc. Confirmed with
user; "repo root" in the new CLAUDE.md is interpreted as `vqe-app/`.

### D2. **Conscious deviation: keep Fernet-encrypted file store, not OS keychain**

The new `CLAUDE.md` (Project-Specific Guidelines, bullet 4) states tokens
"shall be stored via OS keychain (or equivalent platform-native secure
storage), never in plaintext config files or environment variables
committed to source."

User explicitly chose to **keep the Fernet-encrypted file at
`~/.vqe-app/secrets.enc`** when offered the keyring swap. This deviates
from the new guideline. Justification:

- The Fernet ciphertext on disk is not plaintext; the literal rule
  forbids "plaintext config files or environment variables committed to
  source" — neither applies to our encrypted file.
- `keyring` does not work in headless containers without dbus, which
  blocks the most common dev/CI environment for this app.
- User accepted the tradeoff with eyes open after the option was
  presented in writing.

This deviation is also logged in `GAPS.md` (Section "Project deviations
from policy") so it remains visible to anyone auditing the project.

### D3. Simulator-by-default + opt-in real hardware

The new doc reverses the earlier "real credentials required" choice.
User confirmed the override. Implementation strategy (Phase C):

- `VQERunRequest` gains `use_real_hardware: bool = False`.
- Each provider exposes both a simulator path (Aer / LocalSimulator) and
  a hardware path; switch keyed on the request flag.
- Tokens become optional unless `use_real_hardware=True`.
- UI surfaces a checkbox with a credit-burn warning.

### D4. Provider abstraction at a strict boundary

CLAUDE.md guideline: "no provider-specific code outside that boundary".
Plan:

- `app/providers/base.py` defines a `Provider` Protocol with `slug`,
  `display_name`, `settings_schema`, `probe`, `make_estimator`,
  `inspect_backend`.
- `app/providers/registry.py` registers each concrete provider.
- Routes and runner reference providers via the registry only.
- Settings page renders forms dynamically from each provider's
  `settings_schema`, so adding a new provider in the backend
  auto-appears in the UI with zero frontend changes.

### D5. HTTP polling instead of websockets

For iteration cadence on the order of seconds, websockets add transport
complexity without UX benefit. The frontend polls `/api/vqe/runs/{id}`
at 750 ms while a run is active. This is documented under "Out of
scope" in the plan and chosen per Simplicity First.

---

## Blockers

(none currently)

---

## Code pointers

| Area | Location |
| --- | --- |
| FastAPI entrypoint | `backend/app/main.py` |
| Routers | `backend/app/routes/{settings,providers,vqe}.py` |
| Secrets store (Fernet) | `backend/app/secrets_store.py` |
| OpenTelemetry setup | `backend/app/telemetry.py` |
| VQE pipeline | `backend/app/vqe/{hamiltonian,ansatz,runner}.py` |
| Provider adapters | `backend/app/providers/{qiskit,braket}_provider.py` |
| Backend tests | `backend/tests/test_{health,settings,providers,vqe}_api.py` |
| Frontend entry | `frontend/src/main.tsx` |
| Pages | `frontend/src/pages/{Home,Settings}.tsx` |
| API client | `frontend/src/api/client.ts` |
| Theme | `frontend/src/theme.css` |
