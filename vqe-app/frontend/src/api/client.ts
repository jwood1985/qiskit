// Thin fetch wrapper around the FastAPI backend.

export type Molecule = "LiH" | "H2";
export type ProviderName = "qiskit" | "braket";
export type AnsatzName = "UCCSD" | "EfficientSU2";

export interface ProviderView {
  configured: boolean;
  token_fingerprint: string | null;
  extra: Record<string, string> | null;
}

export interface SettingsView {
  qiskit: ProviderView;
  braket: ProviderView;
  dynatrace: ProviderView;
}

export interface ProviderSecret {
  token?: string;
  extra?: Record<string, string>;
}

export interface SettingsPayload {
  qiskit?: ProviderSecret;
  braket?: ProviderSecret;
  dynatrace?: ProviderSecret;
}

export interface ProviderStatus {
  name: ProviderName;
  configured: boolean;
  ready: boolean;
  detail: string;
}

export interface VQEIteration {
  iteration: number;
  energy: number;
}

export interface VQERunStatus {
  id: string;
  state: "pending" | "running" | "succeeded" | "failed";
  molecule: Molecule;
  provider: ProviderName;
  ansatz: AnsatzName;
  iterations: VQEIteration[];
  final_energy: number | null;
  error: string | null;
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
      // ignore — keep the generic status message
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
    provider: ProviderName;
    ansatz: AnsatzName;
    max_iter?: number;
  }) =>
    call<VQERunStatus>("/api/vqe/run", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  getRun: (id: string) => call<VQERunStatus>(`/api/vqe/runs/${id}`),
};
