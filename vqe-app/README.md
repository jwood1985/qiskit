# VQE Telemetry App

A two-component project for running Variational Quantum Eigensolver (VQE)
ground-state energy calculations of small molecules across multiple quantum
providers, with OpenTelemetry instrumentation for the classical optimizer.

- **Backend** — FastAPI service that exposes provider configuration, runs VQE
  for LiH and H2 via Qiskit Nature and Amazon Braket, and emits OpenTelemetry
  signals to a Dynatrace OTLP endpoint.
- **Frontend** — React + TypeScript single-page app with a fixed top navbar,
  a Home page for launching VQE runs, and a Settings page for managing
  provider credentials.

## Quick Start

Prerequisites: Python 3.10+, Node 18+, and valid credentials for at least
one provider (IBM Quantum / IBM Cloud token for Qiskit Runtime, or AWS
credentials with Braket access). The app requires real provider credentials
to run — there is no local simulator fallback.

```bash
# 1. Backend
cd vqe-app/backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000

# 2. Frontend (in a second terminal)
cd vqe-app/frontend
npm install
npm run dev
```

Then open <http://localhost:5173>. First-time setup:

1. Click **Settings** in the top navbar.
2. Enter your provider tokens (Qiskit IBM Quantum, AWS Braket) and the
   Dynatrace API token used for OTel export.
3. Save. Tokens are persisted, encrypted with Fernet, to
   `~/.vqe-app/secrets.enc`.
4. Return to **Home**, pick a molecule (LiH default, H2 alternative), pick a
   provider, and click **Run VQE**. The energy-vs-iteration trace updates
   live; OpenTelemetry spans / metrics flow to
   `https://qof78400.live.dynatrace.com/api/v2/otlp/`.

## VQE Pipeline

| Stage | Tool | Notes |
| --- | --- | --- |
| Electronic structure | PySCF via `qiskit-nature` | RHF reference for LiH (active space) and H2 (full). |
| Qubit mapping | Jordan–Wigner | Default; Parity supported through Qiskit Nature. |
| Ansatz | UCCSD (default) or hardware-efficient `EfficientSU2` | UCCSD is chemistry-standard; HEA is shallower for noisy backends. |
| Optimizer | SciPy COBYLA | Gradient-free, robust to shot noise. |
| Quantum execution | Qiskit Runtime `Estimator` or Braket `LocalSimulator`/device | Selected by provider in Settings. |
| Telemetry | OpenTelemetry → Dynatrace OTLP | Span per VQE run, counter per iteration, gauge for current energy. |

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/providers` | List configured providers and connection status. |
| `GET` | `/api/settings` | Return non-secret view of stored settings. |
| `PUT` | `/api/settings` | Persist provider tokens / endpoints (Fernet-encrypted). |
| `POST` | `/api/vqe/run` | Start a VQE run. Body: `{molecule, provider, ansatz}`. |
| `GET` | `/api/vqe/runs/{id}` | Poll status and (when finished) the energy trace. |

All endpoints are covered by `pytest` (see `backend/tests/`).

## Security

- Tokens are written to disk only as Fernet ciphertext. The key is derived
  from `VQE_APP_SECRET` (env var); if absent, a key is generated on first
  run and stored next to the ciphertext with `0600` permissions.
- The Settings endpoint never returns raw tokens — only a redacted
  fingerprint (`••••last4`).
- Errors are logged via the standard `logging` module and surfaced to the
  UI as a non-revealing message.

## Layout

```
vqe-app/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint
│   │   ├── config.py          # App configuration
│   │   ├── secrets_store.py   # Fernet-encrypted token store
│   │   ├── telemetry.py       # OpenTelemetry → Dynatrace setup
│   │   ├── models.py          # Pydantic request/response models
│   │   ├── vqe/               # Hamiltonian, ansatz, runner
│   │   ├── providers/         # Qiskit Runtime + Braket adapters
│   │   └── routes/            # FastAPI routers
│   └── tests/                 # pytest coverage for endpoints
└── frontend/
    └── src/
        ├── App.tsx
        ├── theme.css          # Color schema #0D1B99/#FF7F27/#060242/#C7C7C7
        ├── components/Navbar.tsx
        └── pages/
            ├── Home.tsx       # Molecule + provider + live run
            └── Settings.tsx   # Provider tokens + Dynatrace token
```
