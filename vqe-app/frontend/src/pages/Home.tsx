import { useCallback, useEffect, useState } from "react";
import {
  api,
  type AnsatzName,
  type JobSnapshot,
  type Molecule,
  type ProviderStatus,
  type VQERunStatus,
} from "../api/client";
import { EnergyChart } from "../components/EnergyChart";

const MOLECULES: { value: Molecule; label: string; description: string }[] = [
  { value: "LiH", label: "LiH", description: "Lithium hydride (frozen core)" },
  { value: "H2", label: "H₂", description: "Molecular hydrogen (full space)" },
];

const ANSATZES: { value: AnsatzName; label: string }[] = [
  { value: "UCCSD", label: "UCCSD (chemistry-standard)" },
  { value: "EfficientSU2", label: "EfficientSU2 (hardware-efficient)" },
];

export function Home() {
  const [molecule, setMolecule] = useState<Molecule>("LiH");
  const [provider, setProvider] = useState<string>("qiskit");
  const [ansatz, setAnsatz] = useState<AnsatzName>("UCCSD");
  const [maxIter, setMaxIter] = useState(80);
  const [useRealHardware, setUseRealHardware] = useState(false);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [run, setRun] = useState<VQERunStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .getProviders()
      .then((p) => {
        setProviders(p);
        if (p.length > 0 && !p.find((x) => x.slug === provider)) {
          setProvider(p[0].slug);
        }
      })
      .catch((e: Error) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!run || run.state === "succeeded" || run.state === "failed") return;
    const id = run.id;
    const handle = setInterval(async () => {
      try {
        setRun(await api.getRun(id));
      } catch (e) {
        setError((e as Error).message);
      }
    }, 750);
    return () => clearInterval(handle);
  }, [run]);

  const handleSubmit = useCallback(async () => {
    setError(null);
    setSubmitting(true);
    try {
      const status = await api.startRun({
        molecule,
        provider,
        ansatz,
        max_iter: maxIter,
        use_real_hardware: useRealHardware,
      });
      setRun(status);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [molecule, provider, ansatz, maxIter, useRealHardware]);

  const providerStatus = providers.find((p) => p.slug === provider);

  return (
    <>
      <h1>Run VQE</h1>
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}

      <div className="grid cols-3">
        <section className="card" aria-labelledby="config-heading">
          <h2 id="config-heading">Configuration</h2>
          <div className="field">
            <label htmlFor="molecule">Molecule</label>
            <select
              id="molecule"
              value={molecule}
              onChange={(e) => setMolecule(e.target.value as Molecule)}
            >
              {MOLECULES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label} — {m.description}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="provider">Provider</label>
            <select
              id="provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              {providers.map((p) => (
                <option key={p.slug} value={p.slug}>
                  {p.display_name}
                </option>
              ))}
            </select>
            {providerStatus && <ProviderBadge status={providerStatus} />}
          </div>
          <div className="field">
            <label htmlFor="ansatz">Ansatz</label>
            <select
              id="ansatz"
              value={ansatz}
              onChange={(e) => setAnsatz(e.target.value as AnsatzName)}
            >
              {ANSATZES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="max-iter">Max optimizer iterations</label>
            <input
              id="max-iter"
              type="number"
              min={1}
              max={2000}
              value={maxIter}
              onChange={(e) => setMaxIter(Number(e.target.value))}
            />
          </div>

          <div className="checkbox-row">
            <input
              id="real-hardware"
              type="checkbox"
              checked={useRealHardware}
              onChange={(e) => setUseRealHardware(e.target.checked)}
            />
            <label htmlFor="real-hardware" style={{ margin: 0 }}>
              Use real hardware
              <div className="field-help">
                Default is simulator. Real hardware consumes provider
                credits and may queue for minutes to hours.
              </div>
            </label>
          </div>

          <div style={{ marginTop: "1rem" }}>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || run?.state === "running"}
            >
              {submitting ? "Submitting…" : "Run VQE"}
            </button>
          </div>
        </section>

        <section className="card span-2" aria-labelledby="trace-heading">
          <h2 id="trace-heading">Energy trace</h2>
          <EnergyChart iterations={run?.iterations ?? []} />
          <RunSummary run={run} />
        </section>

        <section className="card span-2" aria-labelledby="job-heading">
          <h2 id="job-heading">Quantum job lifecycle</h2>
          <JobLifecyclePanel snapshot={run?.last_job_snapshot ?? null} state={run?.current_job_state ?? null} />
        </section>

        <section className="card" aria-labelledby="pipeline-heading">
          <h2 id="pipeline-heading">Pipeline</h2>
          <dl className="kv">
            <dt>Classical</dt>
            <dd>PySCF · qiskit-nature · SciPy COBYLA · OpenTelemetry</dd>
            <dt>Quantum</dt>
            <dd>Provider Estimator primitive (sim/real)</dd>
            <dt>Telemetry</dt>
            <dd>OTLP → Dynatrace qof78400</dd>
          </dl>
        </section>
      </div>
    </>
  );
}

function ProviderBadge({ status }: { status: ProviderStatus }) {
  if (!status.configured) {
    return (
      <div className="field-help">
        <span className="pill bad">not configured</span> {status.detail}
      </div>
    );
  }
  return (
    <div className="field-help">
      <span className={status.ready ? "pill ok" : "pill warn"}>
        {status.ready ? "ready" : "configured"}
      </span>{" "}
      {status.detail}
    </div>
  );
}

function stateClass(state: string | null | undefined): string {
  if (state === "succeeded" || state === "completed") return "ok";
  if (state === "failed") return "bad";
  if (state === "running" || state === "queued") return "warn";
  return "info";
}

function RunSummary({ run }: { run: VQERunStatus | null }) {
  if (!run) {
    return <p className="field-help">No active run. Configure and click <em>Run VQE</em>.</p>;
  }
  return (
    <dl className="kv" style={{ marginTop: "0.5rem" }}>
      <dt>Run</dt>
      <dd>
        <code>{run.id.slice(0, 12)}…</code>{" "}
        <span className={`pill ${stateClass(run.state)}`}>{run.state}</span>
      </dd>
      <dt>Iterations</dt>
      <dd>{run.iterations.length}</dd>
      <dt>Latest energy</dt>
      <dd>
        {run.iterations.length > 0
          ? `${run.iterations[run.iterations.length - 1].energy.toFixed(6)} Ha`
          : "—"}
      </dd>
      {run.final_energy !== null && (
        <>
          <dt>Final energy</dt>
          <dd>
            <strong>{run.final_energy.toFixed(6)} Ha</strong>
          </dd>
        </>
      )}
      {run.error && (
        <>
          <dt>Error</dt>
          <dd style={{ color: "var(--color-error)" }}>{run.error}</dd>
        </>
      )}
    </dl>
  );
}

function JobLifecyclePanel({
  state,
  snapshot,
}: {
  state: string | null;
  snapshot: JobSnapshot | null;
}) {
  if (!snapshot && !state) {
    return (
      <p className="field-help">
        Per-circuit submission state appears here as the optimizer iterates.
        Each quantum job emits a span event on every transition through
        submitted → queued → running → completed.
      </p>
    );
  }
  return (
    <dl className="kv">
      <dt>Current state</dt>
      <dd>
        <span className={`pill ${stateClass(state)}`}>{state ?? "—"}</span>
      </dd>
      <dt>Raw provider state</dt>
      <dd>{snapshot?.raw_state ?? "—"}</dd>
      <dt>Backend</dt>
      <dd>{snapshot?.backend ?? "—"}</dd>
      <dt>Queue time</dt>
      <dd>
        {snapshot?.queue_time_s !== null && snapshot?.queue_time_s !== undefined
          ? `${snapshot.queue_time_s.toFixed(2)} s`
          : "—"}
      </dd>
      <dt>Execution time</dt>
      <dd>
        {snapshot?.execution_time_s !== null && snapshot?.execution_time_s !== undefined
          ? `${snapshot.execution_time_s.toFixed(2)} s`
          : "—"}
      </dd>
      <dt>Shots</dt>
      <dd>{snapshot?.shots ?? "—"}</dd>
    </dl>
  );
}
