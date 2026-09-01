"""Consumer-facing API contract checks generated from the FastAPI schema."""

from app.main import app


def test_openapi_identity_is_versioned():
    schema = app.openapi()
    assert schema["info"]["title"] == "Security Fabric API Gateway"
    assert schema["info"]["version"] == "1.0.0"


def test_critical_operations_remain_in_contract():
    paths = app.openapi()["paths"]
    required = {
        "/auth/token": "post",
        "/alerts": "get",
        "/alerts/{alert_id}/acknowledge": "patch",
        "/alerts/{alert_id}/resolve": "patch",
        "/telemetry/ingest": "post",
        "/health": "get",
    }
    for path, method in required.items():
        assert path in paths, f"missing API path: {path}"
        assert method in paths[path], f"missing {method.upper()} operation for {path}"


def test_authentication_scheme_remains_declared():
    schemes = app.openapi()["components"]["securitySchemes"]
    assert any(scheme.get("type") in {"http", "oauth2"} for scheme in schemes.values())


def test_alert_contract_exposes_lifecycle_audit_fields():
    schemas = app.openapi()["components"]["schemas"]
    response = schemas["AlertResponse"]["properties"]
    assert {"acknowledged_by", "acknowledged_at", "resolved_at"} <= response.keys()


async def test_invalid_telemetry_payload_has_stable_validation_contract(client, auth_headers):
    response = await client.post("/telemetry/ingest", json={}, headers=auth_headers)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert all({"loc", "msg", "type"} <= item.keys() for item in detail)

