"""Приведение OpenAPI к фактическому контракту ошибок и заголовков."""

from typing import Any

from fastapi import FastAPI

ERROR_REF = "#/components/schemas/ErrorResponse"
STORE_SCOPED_PREFIXES = ("/inventory", "/wms", "/recommendations", "/analytics")
PROTECTED_PREFIXES = ("/stores", "/products", "/barcodes") + STORE_SCOPED_PREFIXES


def _error_response(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": {"$ref": ERROR_REF}}},
    }


def _is_protected(path: str) -> bool:
    return path.startswith(PROTECTED_PREFIXES)


def _is_store_scoped(path: str) -> bool:
    return path.startswith(STORE_SCOPED_PREFIXES)


def configure_openapi(app: FastAPI) -> None:
    original_openapi = app.openapi

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = original_openapi()
        for path, path_item in schema["paths"].items():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                responses = operation.setdefault("responses", {})
                validation = responses.get("422")
                if validation is not None:
                    validation["description"] = "Ошибка валидации запроса"
                    validation["content"] = {
                        "application/json": {"schema": {"$ref": ERROR_REF}}
                    }
                if _is_protected(path):
                    responses.setdefault(
                        "400", _error_response("Некорректный X-Store-ID")
                    )
                    responses.setdefault(
                        "403", _error_response("Нет доступа к магазину")
                    )
                if _is_store_scoped(path):
                    for parameter in operation.get("parameters", []):
                        if (
                            parameter.get("name") == "X-Store-ID"
                            and parameter.get("in") == "header"
                        ):
                            parameter["required"] = True
                            parameter["description"] = (
                                "ID магазина из списка доступных для токена"
                            )
        schemas = schema.get("components", {}).get("schemas", {})
        schemas.pop("HTTPValidationError", None)
        schemas.pop("ValidationError", None)
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
