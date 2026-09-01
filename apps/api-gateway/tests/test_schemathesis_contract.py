"""Property-based contract validation generated from the live OpenAPI document."""

import schemathesis
from contextlib import asynccontextmanager

from app.main import app


schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@asynccontextmanager
async def no_external_lifespan(_app):
    yield


app.router.lifespan_context = no_external_lifespan


@schema.include(path_regex=r"^/health$").parametrize()
def test_public_api_contract(case):
    response = case.call()
    case.validate_response(response)
