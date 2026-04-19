import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

BASE_URL = os.getenv("LABORLENS_URL", "https://laborlens.fyi").rstrip("/")

_http: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    assert _http is not None, "HTTP client not initialized"
    return _http


@asynccontextmanager
async def lifespan(server):
    global _http
    _http = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
    yield
    await _http.aclose()


mcp = FastMCP("LaborLens", lifespan=lifespan)


@mcp.tool()
async def search_pwd_cases(
    company: str = "",
    location: str = "",
    case_number: str = "",
    job_title: str = "",
    determination_year: int | None = None,
    received_year: int | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Search DOL Prevailing Wage Determination (PWD) cases on laborlens.fyi.

    Filters by employer name prefix, location (city or state), case number prefix,
    job title prefix, and year. Returns paginated results with wage and SOC data.
    """
    params: dict[str, Any] = {"page": page, "limit": min(limit, 100)}
    if company:
        params["company"] = company
    if location:
        params["location"] = location
    if case_number:
        params["caseNumber"] = case_number
    if job_title:
        params["jobTitle"] = job_title
    if determination_year is not None:
        params["determinationYear"] = determination_year
    if received_year is not None:
        params["receivedYear"] = received_year

    r = await _client().get("/api/search", params=params)
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def search_perm_cases(
    company: str = "",
    location: str = "",
    case_number: str = "",
    job_title: str = "",
    decision_year: int | None = None,
    received_year: int | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
    """Search DOL PERM labor certification cases on laborlens.fyi.

    Filters by employer name prefix, location (city or state), case number prefix,
    job title prefix, and year. Returns paginated results with wage and linked PWD data.
    """
    params: dict[str, Any] = {"page": page, "limit": min(limit, 100)}
    if company:
        params["company"] = company
    if location:
        params["location"] = location
    if case_number:
        params["caseNumber"] = case_number
    if job_title:
        params["jobTitle"] = job_title
    if decision_year is not None:
        params["decisionYear"] = decision_year
    if received_year is not None:
        params["receivedYear"] = received_year

    r = await _client().get("/api/search/perm", params=params)
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def get_case(case_id: str) -> dict[str, Any]:
    """Get full details for a PWD or PERM case by its ID (the _id field from search results)."""
    r = await _client().get(f"/api/cases/{case_id}")
    if r.status_code == 404:
        return {"error": "Case not found"}
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def get_pwd_years() -> list[int]:
    """Return all years available in the PWD cases collection."""
    r = await _client().get("/api/search/years")
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def get_perm_years() -> list[int]:
    """Return all years available in the PERM cases collection."""
    r = await _client().get("/api/search/perm/years")
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    mcp.run()
