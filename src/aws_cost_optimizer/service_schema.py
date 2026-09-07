"""Pydantic schema for service definition YAML files (config/services/*.yaml).

Validating against these models at load time means a malformed service
definition (missing field, wrong type, unknown key) fails immediately with
a clear file/field-level error, instead of surfacing as a KeyError deep
inside the ingest pipeline or waste analyzer at run time.
"""
from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class FieldDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: Literal["VARCHAR", "INTEGER", "DOUBLE", "BOOLEAN", "TIMESTAMP"]
    primary_key: bool = False


class WasteRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: str
    savings_formula: str
    fix_template: str
    derived_fields: dict[str, str] = Field(default_factory=dict)
    recommendation_prefix: str


class ForbiddenPatternsRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["forbidden_patterns"]
    match_keywords: list[str]
    patterns: list[str]
    compliance_status: str
    rule_id: str


class ConditionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["condition"]
    condition: str
    compliance_status: str
    rule_id: str


GuardrailRule = Union[ForbiddenPatternsRule, ConditionRule]


class ServiceDef(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    service_type: str
    table: str
    resource_id_template: str
    schema_fields: list[FieldDef] = Field(alias="schema")
    fetch_adapter: str
    raw_fallback_file: str
    waste_rule: WasteRule
    guardrail_rules: list[ForbiddenPatternsRule | ConditionRule] = Field(default_factory=list)

    @property
    def primary_key_field(self) -> str | None:
        for f in self.schema_fields:
            if f.primary_key:
                return f.name
        return None
