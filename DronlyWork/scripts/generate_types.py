"""Generate TypeScript types from DronlyWork/asyncapi.yaml."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
ASYNCAPI_PATH = ROOT / "asyncapi.yaml"
OUTPUT_PATH = ROOT / "types.ts"


def pointer_part(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def pascal_case(value: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", value)
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def ts_string(value: str) -> str:
    return json.dumps(value)


def ts_literal(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return ts_string(str(value))


def ts_prop_name(value: str) -> str:
    if re.match(r"^[A-Za-z_$][0-9A-Za-z_$]*$", value):
        return value
    return ts_string(value)


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def load_doc() -> dict[str, Any]:
    with ASYNCAPI_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


DOC = load_doc()


def resolve_ref(ref: str) -> Any:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local refs are supported: {ref}")
    current: Any = DOC
    for raw_part in ref[2:].split("/"):
        current = current[pointer_part(raw_part)]
    if isinstance(current, dict) and "$ref" in current:
        return resolve_ref(current["$ref"])
    return current


def ref_to_type(ref: str, context_name: str) -> str:
    if ref.startswith("#/$defs/"):
        return context_name + pascal_case(pointer_part(ref.rsplit("/", 1)[1]))
    if ref.startswith("#/components/schemas/"):
        parts = [pointer_part(part) for part in ref.removeprefix("#/components/schemas/").split("/")]
        if len(parts) >= 3 and parts[1] == "$defs":
            return parts[0] + pascal_case(parts[2])
        return parts[0]
    raise ValueError(f"Unsupported schema ref: {ref}")


def union(types: list[str]) -> str:
    cleaned = unique([item for item in types if item])
    if not cleaned:
        return "unknown"
    if len(cleaned) == 1:
        return cleaned[0]
    return " | ".join(cleaned)


def schema_to_ts(schema: dict[str, Any] | None, context_name: str) -> str:
    if not schema:
        return "unknown"

    if "$ref" in schema:
        return ref_to_type(schema["$ref"], context_name)

    if "const" in schema:
        return ts_literal(schema["const"])

    if "enum" in schema:
        return union([ts_literal(item) for item in schema["enum"]])

    if "anyOf" in schema:
        return union([schema_to_ts(item, context_name) for item in schema["anyOf"]])

    if "oneOf" in schema:
        return union([schema_to_ts(item, context_name) for item in schema["oneOf"]])

    if "allOf" in schema:
        items = [schema_to_ts(item, context_name) for item in schema["allOf"]]
        return " & ".join(unique(items)) if items else "unknown"

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return union([schema_to_ts({**schema, "type": item}, context_name) for item in schema_type])

    if schema_type == "null":
        return "null"
    if schema_type == "boolean":
        return "boolean"
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "string":
        return "string"
    if schema_type == "array":
        item_type = schema_to_ts(schema.get("items"), context_name)
        return f"({item_type})[]" if " | " in item_type or " & " in item_type else f"{item_type}[]"

    if schema_type == "object" or "properties" in schema:
        return inline_object(schema, context_name)

    if schema.get("additionalProperties") is True:
        return "Record<string, unknown>"
    if isinstance(schema.get("additionalProperties"), dict):
        return f"Record<string, {schema_to_ts(schema['additionalProperties'], context_name)}>"

    return "unknown"


def object_members(schema: dict[str, Any], context_name: str, indent: str = "  ") -> list[str]:
    members: list[str] = []
    additional = schema.get("additionalProperties")
    if additional is True:
        members.append(f"{indent}[key: string]: unknown;")
    elif isinstance(additional, dict):
        members.append(f"{indent}[key: string]: {schema_to_ts(additional, context_name)};")

    required = set(schema.get("required", []))
    for name, property_schema in (schema.get("properties") or {}).items():
        optional = "" if name in required else "?"
        members.append(f"{indent}{ts_prop_name(name)}{optional}: {schema_to_ts(property_schema, context_name)};")
    return members


def inline_object(schema: dict[str, Any], context_name: str) -> str:
    if not schema.get("properties"):
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {schema_to_ts(additional, context_name)}>"
        return "Record<string, unknown>"
    members = object_members(schema, context_name, "  ")
    return "{\n" + "\n".join(members) + "\n}"


def render_schema(name: str, schema: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for def_name, def_schema in (schema.get("$defs") or {}).items():
        lines.extend(render_schema(name + pascal_case(def_name), def_schema))
        lines.append("")

    if schema.get("type") == "object" or "properties" in schema:
        lines.append(f"export interface {name} {{")
        lines.extend(object_members(schema, name, "  "))
        lines.append("}")
    else:
        lines.append(f"export type {name} = {schema_to_ts(schema, name)};")
    return lines


def message_from_operation(operation: dict[str, Any]) -> dict[str, Any] | None:
    messages = operation.get("messages") or []
    if not messages:
        return None
    first = messages[0]
    if "$ref" in first:
        return resolve_ref(first["$ref"])
    return first


def payload_type(message: dict[str, Any], extension_name: str | None = None) -> str:
    payload = message.get(extension_name) if extension_name else message.get("payload")
    if not payload:
        return "undefined"
    return schema_to_ts(payload, "")


def collect_events(action: str) -> list[tuple[str, str, str]]:
    events: list[tuple[str, str, str]] = []
    for operation in (DOC.get("operations") or {}).values():
        if operation.get("action") != action:
            continue
        message = message_from_operation(operation)
        if not message or not message.get("name"):
            continue
        name = message["name"]
        events.append((name, payload_type(message), payload_type(message, "x-ack")))
    return events


def render_event_union(type_name: str, names: list[str]) -> list[str]:
    if not names:
        return [f"export type {type_name} = never;"]
    return [f"export type {type_name} = " + " | ".join(ts_string(name) for name in names) + ";"]


def render_event_map(interface_name: str, events: list[tuple[str, str, str]], index: int) -> list[str]:
    lines = [f"export interface {interface_name} {{"]
    for event in events:
        lines.append(f"  {ts_prop_name(event[0])}: {event[index]};")
    lines.append("}")
    return lines


def main() -> None:
    schemas = DOC.get("components", {}).get("schemas", {})
    client_events = collect_events("receive")
    server_events = collect_events("send")

    lines: list[str] = [
        "// Generated from DronlyWork/asyncapi.yaml",
        "// Do not edit by hand. Run `npm run generate:types` after changing api_schema.py.",
        "",
    ]

    for name, schema in schemas.items():
        lines.extend(render_schema(name, schema or {}))
        lines.append("")

    client_names = unique([event[0] for event in client_events])
    server_names = unique([event[0] for event in server_events])

    lines.extend(render_event_union("SocketEventName", client_names))
    lines.append("")
    lines.extend(render_event_map("SocketEvents", client_events, 1))
    lines.append("")
    lines.extend(render_event_map("SocketEventAcks", client_events, 2))
    lines.append("")
    lines.extend(render_event_union("SocketServerEventName", server_names))
    lines.append("")
    lines.extend(render_event_map("SocketServerEvents", server_events, 1))
    lines.append("")
    lines.extend(
        [
            "export type SocketPayload<T extends SocketEventName> = SocketEvents[T];",
            "export type SocketAck<T extends SocketEventName> = SocketEventAcks[T];",
            "export type SocketServerPayload<T extends SocketServerEventName> = SocketServerEvents[T];",
            "",
        ]
    )

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
