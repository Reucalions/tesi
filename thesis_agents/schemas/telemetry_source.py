"""Contratto HTTP di osservazioni OTEL: selettore e policy separati dai fatti."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from .base import Identifier, Message, Text, require_unique

SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Count = Annotated[int, Field(ge=0, strict=True)]


def unix_nano(value: datetime) -> int:
    delta = value.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


class TelemetryQuery(Message):
    service_name: Identifier
    service_instance_id: Text
    package_name: Text
    start_time: AwareDatetime
    end_time: AwareDatetime

    @model_validator(mode="after")
    def bounded_window(self):
        duration = (self.end_time - self.start_time).total_seconds()
        if not 0 < duration <= 86400:
            raise ValueError("Telemetry window must be positive and at most 24 hours")
        return self


class TelemetryInput(TelemetryQuery):
    source: Literal["opentelemetry"] = "opentelemetry"
    available_capabilities: list[Text] = Field(default_factory=list)
    prohibited_actions: list[Text] = Field(default_factory=list)

    def query(self) -> TelemetryQuery:
        return TelemetryQuery.model_validate(
            self.model_dump(include=set(TelemetryQuery.model_fields))
        )


class RecordedLogReference(Message):
    """Record originale, distinto dalla sua posizione nell'export OTel."""

    file: Text
    sha256: SHA256
    line: Annotated[int, Field(ge=1, strict=True)]
    event_time_text: Text  # Ora nel body: non si assume un fuso orario mancante.


class RecordedApacheContext(Message):
    """Attribuzione documentale e inventario: non attributi runtime strumentati."""

    kind: Literal["recorded-apache-binding-v1"] = "recorded-apache-binding-v1"
    dataset_url: Literal["https://zenodo.org/records/5789064"]
    scenario: Literal["russellmitchell"]
    host: Literal["webserver"]
    fqdn: Text
    service: Literal["apache2"] = "apache2"
    # Etichetta di selezione deterministica, NON service.instance.id osservato.
    scope_id: Literal["dataset:russellmitchell:webserver:apache2"] = (
        "dataset:russellmitchell:webserver:apache2"
    )
    instance_basis: Literal["dataset-host-service-scope"] = "dataset-host-service-scope"
    export_sha256: SHA256
    binding_sha256: SHA256
    facts_file: Literal["gather/webserver/facts.json"] = "gather/webserver/facts.json"
    facts_sha256: SHA256
    facts_collected_at: AwareDatetime
    distribution: Literal["Ubuntu"]
    distribution_version: Text
    distribution_release: Text
    package_name: Literal["apache2"] = "apache2"
    package_version: Text
    package_origin: Literal["Ubuntu"]
    package_manager: Literal["apt"]
    package_pointer: Literal["/packages/apache2/0"] = "/packages/apache2/0"


class TelemetryObservation(Message):
    evidence_id: Identifier
    service_name: Identifier
    service_instance_id: Text
    package: Text
    version: Text
    observed_time_unix_nano: Annotated[int, Field(gt=0, strict=True)]
    # Nessuna assenza di attributo viene convertita in false.
    endpoint_exposed: StrictBool | None = None
    deserialization_observed: StrictBool | None = None
    identity_basis: Literal[
        "collector-self-log", "explicit-resource-attributes", "recorded-apache-startup"
    ]
    original_log: RecordedLogReference | None = None
    line: Annotated[int, Field(ge=1, strict=True)]
    pointer: str = Field(pattern=r"^/resourceLogs/\d+/scopeLogs/\d+/logRecords/\d+$")
    record_sha256: SHA256

    @model_validator(mode="after")
    def original_source_required(self):
        if (self.identity_basis == "recorded-apache-startup") != (self.original_log is not None):
            raise ValueError("Recorded Apache observations require an original log reference")
        return self


class TelemetrySnapshot(Message):
    contract: Literal["otel-observations-v1"] = "otel-observations-v1"
    backend: Literal["otel-file-gateway-v1"] = "otel-file-gateway-v1"
    source_id: Identifier
    source_sha256: SHA256
    source_size_bytes: Count
    acquisition: Literal["recorded", "collector-file", "sdk-file"]
    # L'ora di lettura non sostituisce i timestamp delle osservazioni.
    acquired_at: AwareDatetime
    query: TelemetryQuery
    request_sha256: SHA256
    file_record_count: Count
    recognized_record_count: Count
    observations: list[TelemetryObservation] = Field(max_length=100)
    recorded_context: RecordedApacheContext | None = None

    @model_validator(mode="after")
    def selected_records(self):
        if not len(self.observations) <= self.recognized_record_count <= self.file_record_count:
            raise ValueError("Inconsistent telemetry counts")
        require_unique([r.evidence_id for r in self.observations], "telemetry evidence IDs")
        context = self.recorded_context
        if context is not None and (
            self.acquisition != "recorded" or context.export_sha256 != self.source_sha256
        ):
            raise ValueError("Recorded binding must match the recorded export")
        for r in self.observations:
            if (r.identity_basis == "recorded-apache-startup") != (context is not None):
                raise ValueError("Recorded observations and context must remain together")
            if context is not None and (
                (r.service_name, r.service_instance_id, r.package)
                != (context.service, context.scope_id, "Apache")
                or r.endpoint_exposed is not None
                or r.deserialization_observed is not None
            ):
                raise ValueError("Recorded Apache identity/unknown flags do not match the binding")
            if (r.service_name, r.service_instance_id, r.package) != (
                self.query.service_name,
                self.query.service_instance_id,
                self.query.package_name,
            ) or not unix_nano(self.query.start_time) <= r.observed_time_unix_nano < unix_nano(
                self.query.end_time
            ):
                raise ValueError("Observation outside requested identity/window")
        return self


class TelemetryReference(Message):
    source: Literal["opentelemetry"] = "opentelemetry"
    source_id: Identifier
    source_sha256: SHA256
    acquisition: Literal["recorded", "collector-file", "sdk-file"]
    snapshot_file: Literal["telemetry_snapshot.json"] = "telemetry_snapshot.json"
    snapshot_sha256: SHA256
    query: TelemetryQuery
    evidence_ids: list[Identifier] = Field(min_length=1)
    recorded_context: RecordedApacheContext | None = None

    @model_validator(mode="after")
    def recorded_source(self):
        c = self.recorded_context
        if c is not None and (
            self.acquisition != "recorded"
            or self.source_sha256 != c.export_sha256
            or (self.query.service_name, self.query.service_instance_id, self.query.package_name)
            != (c.service, c.scope_id, "Apache")
        ):
            raise ValueError("Recorded context must match the telemetry reference")
        return self
