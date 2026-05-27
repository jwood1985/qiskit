"""Pydantic request/response models.

The provider boundary (see ``app/providers/base.py``) means provider
identifiers are free-form slugs validated at the route layer against
the registry — there is no enum to update when a new provider is added.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .providers.base import ProviderField


class Molecule(str, Enum):
    LIH = "LiH"
    H2 = "H2"


class AnsatzName(str, Enum):
    UCCSD = "UCCSD"
    HARDWARE_EFFICIENT = "EfficientSU2"


# ---------- Settings ----------


class ProviderSecret(BaseModel):
    """Inbound payload — raw secret material, never echoed back unredacted."""

    token: str | None = None
    extra: dict[str, str] | None = None


class SettingsPayload(BaseModel):
    """All-providers-and-dynatrace update payload.

    ``providers`` is a dict keyed by provider slug so the surface area
    stays stable when new providers are added.
    """

    providers: dict[str, ProviderSecret] | None = None
    dynatrace: ProviderSecret | None = None


class ProviderView(BaseModel):
    """Outbound — redacted fingerprint only."""

    configured: bool
    token_fingerprint: str | None = None
    extra: dict[str, str] | None = None


class SettingsView(BaseModel):
    providers: dict[str, ProviderView]
    dynatrace: ProviderView


# ---------- Providers ----------


class ProviderStatus(BaseModel):
    """Combined identity + status + form schema so the UI can render
    everything it needs from a single endpoint."""

    slug: str
    display_name: str
    configured: bool
    ready: bool
    detail: str
    schema_fields: list[ProviderField] = Field(default_factory=list)


# ---------- VQE ----------


class VQERunRequest(BaseModel):
    molecule: Molecule = Molecule.LIH
    provider: str = "qiskit"
    ansatz: AnsatzName = AnsatzName.UCCSD
    max_iter: int = Field(default=80, ge=1, le=2000)
    # Simulator is the dev/test default. Real hardware is opt-in and
    # surfaced in the UI with a credit-burn warning.
    use_real_hardware: bool = False


class VQEIteration(BaseModel):
    iteration: int
    energy: float


class VQERunStatus(BaseModel):
    id: str
    state: Literal["pending", "running", "succeeded", "failed"]
    molecule: Molecule
    provider: str
    ansatz: AnsatzName
    iterations: list[VQEIteration] = Field(default_factory=list)
    final_energy: float | None = None
    error: str | None = None
