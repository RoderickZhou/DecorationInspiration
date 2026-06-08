import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SchemaValidationError(Exception):
    pass


TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _resolve_ref(ref: str, base_path: Optional[Path]) -> Dict[str, Any]:
    if base_path is None:
        raise SchemaValidationError(f"cannot resolve $ref '{ref}' without base path")
    if "#" in ref:
        file_part, pointer = ref.split("#", 1)
    else:
        file_part, pointer = ref, ""
    target = (base_path.parent / file_part).resolve() if file_part else base_path
    data = json.loads(target.read_text(encoding="utf-8"))
    if pointer.startswith("/"):
        for part in pointer.lstrip("/").split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            data = data[part]
    return data


def _validate(value: Any, schema: Dict[str, Any], path: str, base_path: Optional[Path], errors: List[str]) -> None:
    if not isinstance(schema, dict):
        return

    if "$ref" in schema:
        resolved = _resolve_ref(schema["$ref"], base_path)
        _validate(value, resolved, path, base_path, errors)
        return

    expected_type = schema.get("type")
    if expected_type:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(TYPE_CHECKS.get(t, lambda v: True)(value) for t in types):
            errors.append(f"{path}: expected type {types}, got {type(value).__name__}")
            return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string length {len(value)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string length {len(value)} > maxLength {schema['maxLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: array length {len(value)} < minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: array length {len(value)} > maxItems {schema['maxItems']}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{i}]", base_path, errors)

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required property '{req}'")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, val in value.items():
            if key in properties:
                _validate(val, properties[key], f"{path}.{key}", base_path, errors)
            else:
                if additional is False:
                    errors.append(f"{path}: additional property '{key}' not allowed")
                elif isinstance(additional, dict):
                    _validate(val, additional, f"{path}.{key}", base_path, errors)


def validate(value: Any, schema: Dict[str, Any], base_path: Optional[Path] = None) -> List[str]:
    errors: List[str] = []
    _validate(value, schema, "$", base_path, errors)
    return errors


def validate_or_raise(value: Any, schema: Dict[str, Any], base_path: Optional[Path] = None) -> None:
    errors = validate(value, schema, base_path)
    if errors:
        head = "; ".join(errors[:5])
        tail = f" (+{len(errors) - 5} more)" if len(errors) > 5 else ""
        raise SchemaValidationError(head + tail)


def load_schema(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def subschema(schema: Dict[str, Any], pointer: str) -> Dict[str, Any]:
    data: Any = schema
    if not pointer.startswith("/"):
        raise ValueError("pointer must start with '/'")
    for part in pointer.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        data = data[part]
    return data
