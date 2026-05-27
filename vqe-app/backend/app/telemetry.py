"""OpenTelemetry instrumentation, exporting to Dynatrace OTLP/HTTP.

Dynatrace ingests OTLP at ``https://<env-id>.live.dynatrace.com/api/v2/otlp/``
authenticated with an ``Authorization: Api-Token <token>`` header. We
configure the SDK once at startup; subsequent calls to :func:`get_tracer`
and :func:`get_meter` return ready-to-use instruments.

The Dynatrace API token is stored as a secret under the ``dynatrace`` key
in the encrypted store; when it is absent, the exporter is configured
with a no-op pipeline so the rest of the app still works (errors during
export are logged, not raised).
"""
from __future__ import annotations

import logging
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import get_config
from .secrets_store import get_store

logger = logging.getLogger(__name__)

_initialised = False


def configure_telemetry() -> None:
    """Idempotently configure tracer + meter providers.

    Re-reads the Dynatrace token from the secrets store each call so that
    saving a new token in Settings takes effect on the next VQE run.
    """
    global _initialised
    if _initialised:
        return
    cfg = get_config()
    token = _dynatrace_token()
    headers = {"Authorization": f"Api-Token {token}"} if token else {}

    resource = Resource.create({"service.name": cfg.service_name})

    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(
        endpoint=f"{cfg.otlp_endpoint.rstrip('/')}/v1/traces",
        headers=headers,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(
        endpoint=f"{cfg.otlp_endpoint.rstrip('/')}/v1/metrics",
        headers=headers,
    )
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)],
    )
    metrics.set_meter_provider(meter_provider)

    _initialised = True
    if not token:
        logger.warning(
            "Dynatrace token absent — OTLP exporter configured without auth. "
            "Configure it under Settings → Dynatrace before running VQE."
        )


def _dynatrace_token() -> str | None:
    try:
        record = get_store().get("dynatrace") or {}
    except Exception:  # pragma: no cover — secrets store unavailable
        return None
    return record.get("token")


def get_tracer(name: str = "vqe-app") -> Any:
    if not _initialised:
        configure_telemetry()
    return trace.get_tracer(name)


def get_meter(name: str = "vqe-app") -> Any:
    if not _initialised:
        configure_telemetry()
    return metrics.get_meter(name)
