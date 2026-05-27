# VQE Telemetry App

A two-component project for running Variational Quantum Eigensolver (VQE)
ground-state energy calculations of small molecules across multiple
quantum providers, with full OpenTelemetry instrumentation of the
hybrid classical–quantum workflow.

- **Backend** — FastAPI service that runs VQE for LiH / H₂ on Qiskit
  IBM Runtime or AWS Braket, exposes provider configuration, and emits
  span hierarchies (`vqe.run → vqe.iteration → quantum.job`) to a
  Dynatrace OTLP endpoint.
- **Frontend** — React + TypeScript dashboard with a fixed top navbar,
  left sidebar nav, a Home page for launching runs and watching the
  live job lifecycle, a Settings page for provider credentials, and a
  GAPS dashboard that renders the observability-gaps inventory.

## Quick Start

Prerequisites: Python 3.10+, Node 18+. **No credentials are required to
get started** — VQE runs default to local simulators (Qiskit Aer for
Qiskit, Braket LocalSimulator for Braket). Real hardware is an explicit,
opt-in checkbox in the UI.

```bash
# 1. Backend
cd vqe-app/backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# 2. Frontend (second terminal)
cd vqe-app/frontend
npm install
npm run dev
```

Open <http://localhost:5173>. On Home, pick a molecule (LiH default, H₂
alternative), pick a provider, and click **Run VQE**. The energy trace
and the live quantum-job lifecycle panel update as the optimizer
iterates.

To use real hardware:

1. Click **Settings**.
2. Enter the provider tokens you want to use plus the Dynatrace API
   token (used as the `Authorization: Api-Token` header for OTLP
   export). Forms are rendered dynamically from each provider's
   declared schema; tokens are persisted to
   `~/.vqe-app/secrets.enc` (Fernet-encrypted; see `GAPS.md §5.1` for
   the deviation from the OS-keychain rule).
3. Return to Home, tick **Use real hardware** (which carries a
   credit-burn warning), and run.

## VQE Pipeline

| Stage | Tool | Notes |
| --- | --- | --- |
| Electronic structure | PySCF via `qiskit-nature` | RHF reference. LiH uses a frozen-core active space; H₂ is full. |
| Qubit mapping | Jordan–Wigner | Default. |
| Ansatz | UCCSD (default) or `EfficientSU2` | UCCSD is chemistry-standard; HEA is shallower for noisy backends. |
| Optimizer | SciPy COBYLA | Gradient-free, robust to shot noise. |
| Quantum execution | Qiskit AerSimulator / IBM Runtime, or Braket LocalSimulator / AWS device | Provider chosen at submit; simulator vs hardware chosen by the `use_real_hardware` flag. |
| Telemetry | OpenTelemetry → Dynatrace OTLP | `vqe.run → vqe.iteration → quantum.job` span hierarchy; per-job state, queue time, execution time, shots, error mitigation, calibration metadata where exposed. |

## Provider interface

`app/providers/base.py` defines a `Provider` Protocol; each
implementation lives in its own file in `app/providers/` and calls
`register(...)` at import time. **Adding a new provider** (Azure, IonQ,
…) requires only:

1. Create `app/providers/<name>_provider.py` implementing `Provider`.
2. Import the module from `app/providers/__init__.py` so registration
   runs.

No edits to routes, models, or the frontend client are needed — the
Settings page renders the new provider's form from its declared
`settings_schema`, the Home page lists it in the provider dropdown,
and the `/api/providers`, `/api/settings`, and `/api/vqe` endpoints
all pick it up via the registry.

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness check. |
| `GET` | `/api/providers` | List configured providers, connection status, and form schema. |
| `GET` | `/api/settings` | Return non-secret view of stored settings. |
| `PUT` | `/api/settings` | Persist provider tokens / extras (Fernet-encrypted). |
| `POST` | `/api/vqe/run` | Start a VQE run. Body: `{molecule, provider, ansatz, max_iter, use_real_hardware}`. |
| `GET` | `/api/vqe/runs/{id}` | Poll status and live job lifecycle. |
| `GET` | `/api/gaps` | Return `GAPS.md` body for the in-app dashboard. |

All endpoints are covered by `pytest` (see `backend/tests/`). Run the
suite with `make test-backend` — 22 tests pass.

## Observability gaps

The project's success criterion explicitly requires both a working app
**and** a documented inventory of observability gaps at the
classical–quantum boundary. That inventory is `GAPS.md` at the project
root, and it is rendered live in the UI under **Observability → GAPS
dashboard**.

Concrete gaps already catalogued: aggregated-only Estimator output,
hidden Braket task metadata, point-in-time calibration only, opaque
error mitigation, no queue-position telemetry, broken `traceparent`
propagation, divergent job-state vocabularies between providers, and
the project's own conscious Fernet-vs-keychain deviation.

## Security

- Tokens are written to disk only as Fernet ciphertext.
- The Settings endpoint never returns raw tokens — only a redacted
  fingerprint (`••••last4`).
- Errors are logged via the standard `logging` module and surfaced to
  the UI as a non-revealing message.
- Deviation from CLAUDE.md's OS-keychain rule: see `GAPS.md §5.1` and
  `AGENT-MEMORY.md` D2 for the rationale.

## Project documents

| File | Purpose |
| --- | --- |
| `CLAUDE.md` | Behavioural guidelines + project-specific rules. |
| `AGENT-MEMORY.md` | Task-by-task progress journal, decisions, blockers. |
| `GAPS.md` | First-class deliverable — observability gaps inventory. |
| `README.md` | This file. |

## Layout

```
vqe-app/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint
│   │   ├── config.py
│   │   ├── secrets_store.py   # Fernet-encrypted token store
│   │   ├── telemetry.py       # OTel → Dynatrace setup
│   │   ├── models.py
│   │   ├── vqe/               # Hamiltonian, ansatz, runner
│   │   ├── providers/         # base + registry + per-provider files
│   │   └── routes/            # settings, providers, vqe, gaps
│   └── tests/
└── frontend/
    └── src/
        ├── App.tsx            # Shell: navbar + sidebar + main
        ├── theme.css          # Dashboard-grid color schema
        ├── components/        # Navbar, Sidebar, EnergyChart
        └── pages/             # Home, Settings, GapsDashboard
```
