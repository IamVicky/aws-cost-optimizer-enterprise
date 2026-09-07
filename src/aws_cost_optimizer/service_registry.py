"""Loads and validates config/services/*.yaml into ServiceDef objects.

This is the single source of truth consumed by ingest, the waste analyzer,
and the guardrails engine. Adding or changing a service should only ever
require editing a YAML file here, not the Python in those three layers.
"""
import glob
import os

import yaml
from pydantic import ValidationError

from aws_cost_optimizer.config import SERVICES_CONFIG_DIR
from aws_cost_optimizer.service_schema import ServiceDef


class ServiceConfigError(RuntimeError):
    """Raised when a service definition YAML fails schema validation."""


def load_services(config_dir: str = None) -> dict[str, ServiceDef]:
    """Loads every *.yaml file in config_dir into a validated ServiceDef,
    keyed by service_type. Raises ServiceConfigError naming the offending
    file if any definition is malformed."""
    config_dir = config_dir or SERVICES_CONFIG_DIR
    services: dict[str, ServiceDef] = {}

    for path in sorted(glob.glob(os.path.join(config_dir, "*.yaml"))):
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        try:
            service_def = ServiceDef.model_validate(raw)
        except ValidationError as e:
            raise ServiceConfigError(f"Invalid service definition in {path}:\n{e}") from e

        if service_def.service_type in services:
            raise ServiceConfigError(
                f"Duplicate service_type '{service_def.service_type}' in {path} "
                f"(already defined by another file in {config_dir})"
            )
        services[service_def.service_type] = service_def

    return services


if __name__ == "__main__":
    for name, svc in load_services().items():
        print(f"[OK] {name} -> table={svc.table}, fields={len(svc.schema_fields)}, "
              f"guardrail_rules={len(svc.guardrail_rules)}")
