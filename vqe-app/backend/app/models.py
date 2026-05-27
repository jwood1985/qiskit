"""Pydantic request/response models."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Molecule(str, Enum):
    LIH = "LiH"
    H2 = "H2"


class ProviderName(str, Enum):
    QISKIT = "qiskit"
    BRAKET = "braket"


class AnsatzName(str, Enum):
    UCCSD = "UCCSD"
    HARDWARE_EFFICIENT = "EfficientSU2"


# ---------- Settings ----------


class ProviderSecret(BaseModel):
    """Inbound payload — raw secrets, never echoed back unredacted."""

    token: str | None = None
    extra: dict[str, str] | None = None


class SettingsPayload(BaseModel):
    qiskit: ProviderSecret | None = None
    braket: ProviderSecret | None = None
    dynatrace: ProviderSecret | None = None


class ProviderView(BaseModel):
    """Outbound — redacted fingerprint only."""

    configured: bool
    token_fingerprint: str | None = None
    extra: dict[str, str] | None = None


class SettingsView(BaseModel):
    qiskit: ProviderView
    braket: ProviderView
    dynatrace: ProviderView


# ---------- Providers ----------


class ProviderStatus(BaseModel):
    name: ProviderName
    configured: bool
    ready: bool
    detail: str


# ---------- VQE ----------


class VQERunRequest(BaseModel):
    molecule: Molecule = Molecule.LIH
    provider: ProviderName = ProviderName.QISKIT
    ansatz: AnsatzName = AnsatzName.UCCSD
    max_iter: int = Field(default=80, ge=1, le=2000)


class VQEIteration(BaseModel):
    iteration: int
    energy: float


class VQERunStatus(BaseModel):
    id: str
    state: Literal["pending", "running", "succeeded", "failed"]
    molecule: Molecule
    provider: ProviderName
    ansatz: AnsatzName
    iterations: list[VQEIteration] = Field(default_factory=list)
    final_energy: float | None = None
    error: str | None = None
