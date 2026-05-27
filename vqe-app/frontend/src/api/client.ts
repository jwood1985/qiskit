// Thin fetch wrapper around the FastAPI backend.

export type Molecule = "LiH" | "H2";
export type AnsatzName = "UCCSD" | "EfficientSU2";

export interface ProviderField {
  name: string;
  label: string;
  secret: boolean;
  required: boolean;
  default: string | null;
  help: string | null;
}

export interface ProviderView {
  configured: boolean;
  token_fingerprint: string | null;
  extra: Record<string, string> | null;
}

export interface SettingsView {
  providers: Record<string, ProviderView>;
  dynatrace: ProviderView;
}

export interface ProviderSecret {
  token?: string;
  extra?: Record<string, string>;
}

export interface SettingsPayload {
  providers?: Record<string, ProviderSecret>;
  dynatrace?: ProviderSecret;
}

export interface ProviderStatus {
  slug: string;
  display_name: string;
  configured: boolean;
  ready: boolean;
  detail: string;
  schema_fields: ProviderField[];
}

export interface VQEIteration {
  iteration: number;
  energy: number;
}

export interface JobSnapshot {
  state: string;
  raw_state: string | null;
  queue_time_s: number | null;
  execution_time_s: number | null;
  shots: number | null;
  backend: string | null;
  error_mitigation: Record<string, unknown> | null;
  calibration: Record<string, unknown> | null;
}

export interface VQERunStatus {
  id: string;
  state: "pending" | "running" | "succeeded" | "failed";
  molecule: Molecule;
  provider: string;
  ansatz: AnsatzName;
  iterations: VQEIteration[];
  final_energy: number | null;
  error: string | null;
  current_job_state: string | null;
  last_job_snapshot: JobSnapshot | null;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getSettings: () => call<SettingsView>("/api/settings"),
  updateSettings: (payload: SettingsPayload) =>
    call<SettingsView>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  getProviders: () => call<ProviderStatus[]>("/api/providers"),
  startRun: (req: {
    molecule: Molecule;
    provider: string;
    ansatz: AnsatzName;
    max_iter?: number;
    use_real_hardware?: boolean;
  }) =>
    call<VQERunStatus>("/api/vqe/run", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  getRun: (id: string) => call<VQERunStatus>(`/api/vqe/runs/${id}`),
  getGaps: () => call<{ markdown: string }>("/api/gaps"),
};
