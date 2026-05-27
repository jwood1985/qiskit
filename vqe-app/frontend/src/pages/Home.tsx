import { useCallback, useEffect, useState } from "react";
import {
  api,
  type AnsatzName,
  type Molecule,
  type ProviderName,
  type ProviderStatus,
  type VQERunStatus,
} from "../api/client";
import { EnergyChart } from "../components/EnergyChart";

const MOLECULES: { value: Molecule; label: string; description: string }[] = [
  { value: "LiH", label: "LiH", description: "Lithium hydride (default, frozen-core active space)" },
  { value: "H2", label: "H₂", description: "Molecular hydrogen (full space, 4 qubits)" },
];

const ANSATZES: { value: AnsatzName; label: string }[] = [
  { value: "UCCSD", label: "UCCSD (chemistry-standard)" },
  { value: "EfficientSU2", label: "EfficientSU2 (hardware-efficient)" },
];

export function Home() {
  const [molecule, setMolecule] = useState<Molecule>("LiH");
  const [provider, setProvider] = useState<ProviderName>("qiskit");
  const [ansatz, setAnsatz] = useState<AnsatzName>("UCCSD");
  const [maxIter, setMaxIter] = useState(80);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [run, setRun] = useState<VQERunStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .getProviders()
      .then(setProviders)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!run || run.state === "succeeded" || run.state === "failed") return;
    const id = run.id;
    const handle = setInterval(async () => {
      try {
        const next = await api.getRun(id);
        setRun(next);
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
      const status = await api.startRun({ molecule, provider, ansatz, max_iter: maxIter });
      setRun(status);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [molecule, provider, ansatz, maxIter]);

  const providerByName = (name: ProviderName) =>
    providers.find((p) => p.name === name);

  return (
    <>
      <h1>Ground-state energy via VQE</h1>
      <p className="muted">
        Select a molecule and a quantum provider, then run VQE. The classical
        optimizer’s iterations are streamed live and exported to Dynatrace via
        OpenTelemetry.
      </p>

      {error && <div className="alert error" role="alert">{error}</div>}

      <section className="card" aria-labelledby="config-heading">
        <h2 id="config-heading">Configuration</h2>
        <div className="row cols-2">
          <div>
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
          <div>
            <label htmlFor="provider">Provider</label>
            <select
              id="provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value as ProviderName)}
            >
              <option value="qiskit">Qiskit (IBM Runtime)</option>
              <option value="braket">AWS Braket</option>
            </select>
            <ProviderBadge status={providerByName(provider)} />
          </div>
          <div>
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
          <div>
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

      <section className="card" aria-labelledby="result-heading">
        <h2 id="result-heading">Live telemetry</h2>
        {run ? <RunPanel run={run} /> : <p className="muted">No active run.</p>}
      </section>

      <section className="card" aria-labelledby="pipeline-heading">
        <h2 id="pipeline-heading">What runs where</h2>
        <p className="muted">
          The Hamiltonian construction, Jordan–Wigner mapping, UCCSD ansatz
          compilation, and SciPy COBYLA optimizer all run on the backend
          (classical compute). The expectation-value evaluations of each
          parameter update are dispatched to the selected quantum provider.
        </p>
        <dl className="kv">
          <dt>Classical</dt>
          <dd>PySCF + qiskit-nature, SciPy COBYLA, OpenTelemetry SDK</dd>
          <dt>Quantum</dt>
          <dd>Qiskit Runtime Estimator (IBM) or Braket via qiskit-braket-provider</dd>
        </dl>
      </section>
    </>
  );
}

function ProviderBadge({ status }: { status: ProviderStatus | undefined }) {
  if (!status) {
    return <span className="pill">unknown</span>;
  }
  if (!status.configured) {
    return (
      <p style={{ marginTop: "0.5rem" }}>
        <span className="pill bad">not configured</span>{" "}
        <span className="muted">{status.detail}</span>
      </p>
    );
  }
  return (
    <p style={{ marginTop: "0.5rem" }}>
      <span className={status.ready ? "pill ok" : "pill warn"}>
        {status.ready ? "ready" : "configured"}
      </span>{" "}
      <span className="muted">{status.detail}</span>
    </p>
  );
}

function RunPanel({ run }: { run: VQERunStatus }) {
  const stateClass =
    run.state === "succeeded" ? "ok" : run.state === "failed" ? "bad" : "warn";
  return (
    <>
      <dl className="kv">
        <dt>Run ID</dt>
        <dd>
          <code>{run.id}</code>
        </dd>
        <dt>State</dt>
        <dd>
          <span className={`pill ${stateClass}`}>{run.state}</span>
        </dd>
        <dt>Iterations completed</dt>
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
      </dl>
      {run.error && (
        <div className="alert error" role="alert">
          {run.error}
        </div>
      )}
      <EnergyChart iterations={run.iterations} />
    </>
  );
}
