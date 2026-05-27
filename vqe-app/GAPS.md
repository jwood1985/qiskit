# GAPS.md

Inventory of observability gaps at the classical-quantum boundary that
this VQE app encountered while integrating Qiskit IBM Runtime and AWS
Braket. This file is a first-class deliverable: the project's success
criterion explicitly requires it.

Each entry: **gap**, the **workaround** in this codebase (if any), and a
**signal we wish the provider exposed**. Entries are grouped by gap
category as defined in the project guidelines.

---

## 1. Provider APIs lacking observability hooks

### 1.1 Qiskit Runtime `EstimatorV2` aggregates away per-shot statistics

`EstimatorV2` returns mean expectation values and standard errors. We
have no access to:

- Per-shot bitstring outcomes (Estimator collapses them).
- Per-circuit timing (only aggregate `usage` metrics on the job).
- Shot-level error mitigation diagnostics (e.g., what ZNE noise factor
  each shot landed at when `resilience_level >= 2`).

**Workaround:** record only the aggregate values exposed via
`job.metrics()` and `job.usage()`. We surface `usage.seconds`,
`usage.quantum_seconds`, and `metrics.timestamps` on the
`quantum.job` span.

**Wish:** Estimator returns a `shots` field per circuit and a
per-circuit timing breakdown.

### 1.2 `qiskit-braket-provider` hides Braket task metadata

When we run Braket through `qiskit-braket-provider`'s `BackendEstimator`
shim, the underlying Braket `QuantumTask` object is wrapped and not
returned. We cannot reach `task.metadata()` (which would give us
`queueInfo`, `deviceArn`, `shots`, `createdAt`/`endedAt`).

**Workaround:** when the user is on Braket we set
`backend_metadata.unavailable=true` on the span and only emit the
device name. Operators who want full visibility have to bypass the
qiskit shim and submit through the native `braket.devices` SDK.

**Wish:** the provider exposes the underlying `QuantumTask` (e.g. via
`job.raw_task()`).

### 1.3 No backend calibration API on either provider at job-submission time

Both providers ship calibration data, but as **point-in-time backend
snapshots** rather than **per-job snapshots**:

- Qiskit Runtime: `backend.target` / `backend.properties()` is the
  state at the time we acquired the backend handle. There is no
  guarantee the calibration we observe matches the one used when the
  job actually runs minutes later in a queue.
- Braket: `device.properties` is read at provider acquisition. Per-job
  calibration provenance is not exposed.

**Workaround:** we snapshot `backend.target.qubit_properties()` (T1, T2,
readout error) at `make_estimator` time and stamp it on every
`quantum.job` span emitted from that estimator. This is *temporally
inaccurate* but it is the best available approximation.

**Wish:** an API like `job.calibration_at_execution()` returning the
calibration table that was in effect when the job ran.

### 1.4 No telemetry on internal error mitigation passes

Qiskit Runtime applies error mitigation (`resilience_level`) inside the
service. We see the input flag but not what the service actually did:
how many noise scalings, whether PEC or ZNE, whether dynamical
decoupling was applied, etc.

**Workaround:** emit only the requested `resilience_level` as a span
attribute. The actual mitigation pipeline applied is opaque.

**Wish:** Estimator results include a `mitigation_trace` field listing
each pass.

### 1.5 No queue-position telemetry

Both providers report `state in {queued, running, ...}` but neither
reports **position in queue** or **estimated wait**. The user sees
"queued" for an unknown amount of time.

**Workaround:** the UI shows elapsed time since the run started; we
cannot show "12 jobs ahead, ~7 min."

**Wish:** `job.queue_position` and `job.estimated_start_time`.

---

## 2. Workarounds required to propagate trace context across the
   classical-quantum boundary

### 2.1 Neither provider accepts `traceparent` propagation headers

Both Qiskit Runtime and Braket job submission APIs reject unknown
headers (or simply do not forward them to their server-side execution
spans, even if the platform itself runs OTel). The W3C Trace Context
chain breaks at the provider boundary.

**Workaround:** we stamp `vqe.run.id` and `vqe.iteration.idx` on every
`quantum.job` span on the client side, and we record the
**provider job id** as an attribute on the `quantum.job` span so an
operator with access to provider-side logs can correlate manually.

**Wish:** providers accept and propagate the standard `traceparent`
header into their server-side execution telemetry, completing the
distributed trace.

### 2.2 Async polling means the parent span ends before the child does

Optimizer iterations are sequential but each iteration's quantum job
can queue for hours. To avoid holding a long-lived
`vqe.iteration` span (and hitting OTel SDK limits), we end the parent
iteration span at `submit()` time and use a span **link** from the
child `quantum.job` span back to the iteration span when it eventually
completes. This is a divergence from "child-of" parenting and is worth
calling out.

**Workaround:** OTel `Span.add_link()` from the child to the (already
ended) parent's `SpanContext`, captured at submit time.

**Wish:** standard distributed-tracing tooling that handles long-lived
async parents natively. (Not really a provider gap — an OTel ecosystem
gap.)

---

## 3. Valuable telemetry signals not exposed by any provider

| Signal | Why we want it | What we use instead |
| --- | --- | --- |
| Per-shot bitstring counts | Detect mid-job decoherence, identify outlier shots | Aggregate expectation only |
| Pulse-level execution timing | Correlate optimizer divergence with backend recalibration | Coarse `job.usage` totals |
| Crosstalk / coupling-map deviations during execution | Explain anomalous variance | Static backend metadata only |
| Gate-level error rate during the job window | Compare to optimizer's noisy gradient signal | Pre-job calibration only |
| Real-time queue position | Surface to the user | Elapsed time since submit |

---

## 4. Cross-provider behavioural differences that complicate uniform
   instrumentation

### 4.1 Job state vocabulary

- Qiskit Runtime job states: `INITIALIZING`, `QUEUED`, `VALIDATING`,
  `RUNNING`, `COMPLETED`, `CANCELLED`, `FAILED`, `ERROR`.
- Braket task states: `CREATED`, `QUEUED`, `RUNNING`, `COMPLETED`,
  `FAILED`, `CANCELLED`.

We normalise both to our canonical `submitted | queued | running |
completed | failed` set in `app/providers/base.py`. Mapping
imperfections (e.g. Qiskit's `VALIDATING` is collapsed into our
`queued`) are noted on the span as `provider.raw_state`.

### 4.2 Result objects expose different metric shapes

- Qiskit Runtime `EstimatorV2.run().result()` → `PrimitiveResult`
  with per-pub `metadata.shots` and `metadata.target_precision`.
- Braket via `BackendEstimator` → bare `EstimatorResult` with `values`
  and `metadata` (mostly empty under the shim).

**Workaround:** we only emit attributes that exist in both — the union
ends up being device name and (sometimes) shots. Provider-specific
extras are recorded as opaque attributes.

### 4.3 Authentication primitives are different

- Qiskit Runtime: single API token, optionally `instance` and
  `channel`.
- Braket: AWS credentials triple (access key id + secret + optional
  session token) plus region and device name.

The provider abstraction's `settings_schema` advertises field names per
provider so the UI can render the correct form. Adding Azure (Pauli
authentication, Quantum workspace, etc.) will only require declaring
its own schema.

---

## 5. Project deviations from CLAUDE.md policy

These are not provider gaps, but they belong in this file because they
are deliberate departures from the project's own observability /
security policy that future readers must be able to find.

### 5.1 Fernet file storage instead of OS keychain

CLAUDE.md (Project-Specific Guidelines, bullet 4) requires OS keychain
storage for tokens. The user explicitly chose to keep the existing
Fernet-encrypted file at `~/.vqe-app/secrets.enc` instead. Rationale
and justification are recorded in `AGENT-MEMORY.md` D2. This deviation
is intentional and approved; it is logged here so operators can audit
the secret-handling story without having to read the agent's progress
journal.
