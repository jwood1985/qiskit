import { useCallback, useEffect, useState } from "react";
import { api, type SettingsView } from "../api/client";

interface FormState {
  qiskitToken: string;
  qiskitInstance: string;
  qiskitChannel: string;
  braketToken: string;
  braketAccessKey: string;
  braketRegion: string;
  braketDevice: string;
  dynatraceToken: string;
}

const EMPTY: FormState = {
  qiskitToken: "",
  qiskitInstance: "",
  qiskitChannel: "ibm_quantum",
  braketToken: "",
  braketAccessKey: "",
  braketRegion: "us-east-1",
  braketDevice: "SV1",
  dynatraceToken: "",
};

export function Settings() {
  const [view, setView] = useState<SettingsView | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getSettings().then(setView).catch((e: Error) => setMessage({ kind: "err", text: e.message }));
  }, []);

  const onSubmit = useCallback(
    async (evt: React.FormEvent) => {
      evt.preventDefault();
      setSaving(true);
      setMessage(null);
      try {
        const payload: Parameters<typeof api.updateSettings>[0] = {};
        if (form.qiskitToken || form.qiskitInstance) {
          payload.qiskit = {
            ...(form.qiskitToken ? { token: form.qiskitToken } : {}),
            extra: {
              ...(form.qiskitInstance ? { instance: form.qiskitInstance } : {}),
              channel: form.qiskitChannel,
            },
          };
        }
        if (form.braketToken || form.braketAccessKey) {
          payload.braket = {
            ...(form.braketToken ? { token: form.braketToken } : {}),
            extra: {
              ...(form.braketAccessKey ? { access_key_id: form.braketAccessKey } : {}),
              region: form.braketRegion,
              device: form.braketDevice,
            },
          };
        }
        if (form.dynatraceToken) {
          payload.dynatrace = { token: form.dynatraceToken };
        }
        const next = await api.updateSettings(payload);
        setView(next);
        setForm(EMPTY);
        setMessage({ kind: "ok", text: "Settings saved. Tokens are encrypted on disk." });
      } catch (e) {
        setMessage({ kind: "err", text: (e as Error).message });
      } finally {
        setSaving(false);
      }
    },
    [form],
  );

  const update = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }));

  return (
    <>
      <h1>Provider settings</h1>
      <p className="muted">
        Tokens are encrypted with Fernet and persisted to
        <code> ~/.vqe-app/secrets.enc</code>. The Settings API never returns
        raw token values — only a redacted fingerprint.
      </p>

      {message && (
        <div className={`alert ${message.kind === "ok" ? "success" : "error"}`} role="alert">
          {message.text}
        </div>
      )}

      <form onSubmit={onSubmit}>
        <section className="card" aria-labelledby="qiskit-heading">
          <h2 id="qiskit-heading">Qiskit IBM Runtime</h2>
          <StatusLine label="Status" view={view?.qiskit} />
          <div className="row cols-2">
            <div>
              <label htmlFor="qiskit-token">API token</label>
              <input
                id="qiskit-token"
                type="password"
                autoComplete="off"
                value={form.qiskitToken}
                onChange={update("qiskitToken")}
                placeholder="paste IBM Quantum token"
              />
            </div>
            <div>
              <label htmlFor="qiskit-instance">Instance (hub/group/project)</label>
              <input
                id="qiskit-instance"
                type="text"
                value={form.qiskitInstance}
                onChange={update("qiskitInstance")}
                placeholder="ibm-q/open/main"
              />
            </div>
            <div>
              <label htmlFor="qiskit-channel">Channel</label>
              <input
                id="qiskit-channel"
                type="text"
                value={form.qiskitChannel}
                onChange={update("qiskitChannel")}
              />
            </div>
          </div>
        </section>

        <section className="card" aria-labelledby="braket-heading">
          <h2 id="braket-heading">AWS Braket</h2>
          <StatusLine label="Status" view={view?.braket} />
          <div className="row cols-2">
            <div>
              <label htmlFor="braket-access">Access key ID</label>
              <input
                id="braket-access"
                type="text"
                autoComplete="off"
                value={form.braketAccessKey}
                onChange={update("braketAccessKey")}
                placeholder="AKIA…"
              />
            </div>
            <div>
              <label htmlFor="braket-secret">Secret access key</label>
              <input
                id="braket-secret"
                type="password"
                autoComplete="off"
                value={form.braketToken}
                onChange={update("braketToken")}
              />
            </div>
            <div>
              <label htmlFor="braket-region">Region</label>
              <input
                id="braket-region"
                type="text"
                value={form.braketRegion}
                onChange={update("braketRegion")}
              />
            </div>
            <div>
              <label htmlFor="braket-device">Device</label>
              <input
                id="braket-device"
                type="text"
                value={form.braketDevice}
                onChange={update("braketDevice")}
                placeholder="SV1"
              />
            </div>
          </div>
        </section>

        <section className="card" aria-labelledby="dynatrace-heading">
          <h2 id="dynatrace-heading">Dynatrace (OpenTelemetry)</h2>
          <StatusLine label="Status" view={view?.dynatrace} />
          <p className="muted">
            OTLP target:&nbsp;
            <code>https://qof78400.live.dynatrace.com/api/v2/otlp</code>
          </p>
          <label htmlFor="dt-token">API token</label>
          <input
            id="dt-token"
            type="password"
            autoComplete="off"
            value={form.dynatraceToken}
            onChange={update("dynatraceToken")}
            placeholder="dt0c01.…"
          />
        </section>

        <button type="submit" className="secondary" disabled={saving}>
          {saving ? "Saving…" : "Save settings"}
        </button>
      </form>
    </>
  );
}

function StatusLine({
  label,
  view,
}: {
  label: string;
  view: { configured: boolean; token_fingerprint: string | null; extra: Record<string, string> | null } | undefined;
}) {
  if (!view) return null;
  return (
    <p style={{ margin: "0 0 1rem" }}>
      <strong>{label}: </strong>
      {view.configured ? (
        <>
          <span className="pill ok">configured</span>{" "}
          <span className="muted">token {view.token_fingerprint}</span>
        </>
      ) : (
        <span className="pill bad">not set</span>
      )}
    </p>
  );
}
