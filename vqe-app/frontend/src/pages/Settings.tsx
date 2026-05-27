import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  type ProviderField,
  type ProviderSecret,
  type ProviderStatus,
  type SettingsView,
} from "../api/client";

type DraftMap = Record<string, Record<string, string>>;

export function Settings() {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [view, setView] = useState<SettingsView | null>(null);
  const [draft, setDraft] = useState<DraftMap>({});
  const [dynatraceDraft, setDynatraceDraft] = useState("");
  const [message, setMessage] = useState<
    { kind: "ok" | "err"; text: string } | null
  >(null);
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [provs, settings] = await Promise.all([
        api.getProviders(),
        api.getSettings(),
      ]);
      setProviders(provs);
      setView(settings);
    } catch (e) {
      setMessage({ kind: "err", text: (e as Error).message });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const updateField = (slug: string, field: string, value: string) =>
    setDraft((prev) => ({
      ...prev,
      [slug]: { ...(prev[slug] ?? {}), [field]: value },
    }));

  const onSubmit = useCallback(
    async (evt: React.FormEvent) => {
      evt.preventDefault();
      setSaving(true);
      setMessage(null);
      try {
        const providerPayload: Record<string, ProviderSecret> = {};
        for (const provider of providers) {
          const entries = draft[provider.slug];
          if (!entries) continue;
          const secret: ProviderSecret = {};
          const extra: Record<string, string> = {};
          for (const field of provider.schema_fields) {
            const v = entries[field.name];
            if (v === undefined || v === "") continue;
            if (field.name === "token") secret.token = v;
            else extra[field.name] = v;
          }
          if (Object.keys(extra).length > 0) secret.extra = extra;
          if (Object.keys(secret).length > 0) providerPayload[provider.slug] = secret;
        }
        const payload: Parameters<typeof api.updateSettings>[0] = {};
        if (Object.keys(providerPayload).length > 0)
          payload.providers = providerPayload;
        if (dynatraceDraft) payload.dynatrace = { token: dynatraceDraft };

        await api.updateSettings(payload);
        setDraft({});
        setDynatraceDraft("");
        setMessage({
          kind: "ok",
          text: "Settings saved. Tokens are encrypted on disk.",
        });
        await refresh();
      } catch (e) {
        setMessage({ kind: "err", text: (e as Error).message });
      } finally {
        setSaving(false);
      }
    },
    [providers, draft, dynatraceDraft, refresh],
  );

  return (
    <>
      <h1>Settings</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        Provider forms are rendered from each provider's declared schema
        — adding a new provider in the backend surfaces here
        automatically. Tokens are Fernet-encrypted on disk at{" "}
        <code>~/.vqe-app/secrets.enc</code> (see <code>GAPS.md §5.1</code>
        for why this deviates from the OS-keychain rule).
      </p>

      {message && (
        <div
          className={`alert ${message.kind === "ok" ? "success" : "error"}`}
          role="alert"
        >
          {message.text}
        </div>
      )}

      <form onSubmit={onSubmit}>
        <div className="grid cols-2">
          {providers.map((provider) => (
            <ProviderCard
              key={provider.slug}
              provider={provider}
              view={view?.providers[provider.slug]}
              draft={draft[provider.slug] ?? {}}
              onChange={(field, value) =>
                updateField(provider.slug, field, value)
              }
            />
          ))}
          <DynatraceCard
            view={view?.dynatrace}
            value={dynatraceDraft}
            onChange={setDynatraceDraft}
          />
        </div>
        <div style={{ marginTop: "1rem" }}>
          <button type="submit" className="secondary" disabled={saving}>
            {saving ? "Saving…" : "Save settings"}
          </button>
        </div>
      </form>
    </>
  );
}

function ProviderCard({
  provider,
  view,
  draft,
  onChange,
}: {
  provider: ProviderStatus;
  view: { configured: boolean; token_fingerprint: string | null } | undefined;
  draft: Record<string, string>;
  onChange: (field: string, value: string) => void;
}) {
  return (
    <section className="card" aria-labelledby={`${provider.slug}-heading`}>
      <h2 id={`${provider.slug}-heading`}>{provider.display_name}</h2>
      <StatusBadge view={view} />
      {provider.schema_fields.map((field) => (
        <Field
          key={field.name}
          field={field}
          value={draft[field.name] ?? ""}
          onChange={(value) => onChange(field.name, value)}
        />
      ))}
    </section>
  );
}

function DynatraceCard({
  view,
  value,
  onChange,
}: {
  view: { configured: boolean; token_fingerprint: string | null } | undefined;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <section className="card" aria-labelledby="dynatrace-heading">
      <h2 id="dynatrace-heading">Dynatrace (OpenTelemetry)</h2>
      <StatusBadge view={view} />
      <p className="field-help">
        Target:&nbsp;
        <code>https://qof78400.live.dynatrace.com/api/v2/otlp</code>
      </p>
      <div className="field">
        <label htmlFor="dt-token">API token</label>
        <input
          id="dt-token"
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="dt0c01.…"
        />
      </div>
    </section>
  );
}

function StatusBadge({
  view,
}: {
  view: { configured: boolean; token_fingerprint: string | null } | undefined;
}) {
  return (
    <p style={{ margin: "0 0 0.75rem" }}>
      {view?.configured ? (
        <>
          <span className="pill ok">configured</span>{" "}
          <span className="field-help" style={{ display: "inline" }}>
            token {view.token_fingerprint}
          </span>
        </>
      ) : (
        <span className="pill bad">not set</span>
      )}
    </p>
  );
}

function Field({
  field,
  value,
  onChange,
}: {
  field: ProviderField;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useMemo(() => `field-${Math.random().toString(36).slice(2, 9)}`, []);
  return (
    <div className="field">
      <label htmlFor={id}>
        {field.label}
        {field.required ? " *" : ""}
      </label>
      <input
        id={id}
        type={field.secret ? "password" : "text"}
        autoComplete="off"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.default ?? ""}
      />
      {field.help && <div className="field-help">{field.help}</div>}
    </div>
  );
}
