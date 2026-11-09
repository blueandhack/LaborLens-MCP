import os
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

load_dotenv()

BASE_URL = os.getenv("LABORLENS_URL", "https://laborlens.fyi").rstrip("/")

Program = Literal["pwd", "perm", "h1b"]
CaseSort = Literal["event_desc", "event_asc", "received_desc", "received_asc"]
H1bSort = Literal[
    "event_desc", "event_asc", "received_desc", "received_asc", "certification_desc", "certification_asc"
]
DirectorySort = Literal["h1b_desc", "perm_desc", "pwd_desc", "name_asc", "name_desc"]

# Search path per program; PWD is the API's default program.
SEARCH_PATHS: dict[str, str] = {"pwd": "/api/search", "perm": "/api/search/perm", "h1b": "/api/search/h1b"}
# Query parameter holding each program's decision/determination year.
YEAR_PARAMS: dict[str, str] = {"pwd": "determinationYear", "perm": "decisionYear", "h1b": "decisionYear"}

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True)

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


mcp = MCPServer(
    "LaborLens",
    instructions=(
        "Search U.S. Department of Labor disclosure data on laborlens.fyi: prevailing wage determinations (PWD), "
        "PERM labor certifications, and H-1B Labor Condition Applications (LCA). To research an employer, "
        "call search_employers first, then pass its groupId as employer_group to the case search tools so every "
        "reported spelling and former name of that employer is included, or open its profile with get_employer_profile."
    ),
    lifespan=lifespan,
)


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET a LaborLens API path, returning the API's own error message on 4xx/5xx."""
    r = await _client().get(path, params=params)
    if r.is_error:
        try:
            message = r.json().get("error")
        except ValueError:
            message = None
        return {"error": message or f"LaborLens returned HTTP {r.status_code}", "status": r.status_code}
    return r.json()


def _search_params(
    program: str,
    *,
    company: str,
    employer: str,
    employer_group: str,
    location: str,
    worksite: str,
    worksite_state: str,
    case_number: str,
    job_title: str,
    year: int | None,
    received_year: int | None,
    sort: str,
    page: int,
    limit: int,
    exact_total: bool,
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": max(page, 1), "limit": max(1, min(limit, 100)), "sort": sort}
    for key, value in {
        "company": company,
        "employer": employer,
        "employerGroup": employer_group,
        "location": location,
        "worksite": worksite,
        "worksiteState": worksite_state,
        "caseNumber": case_number,
        "jobTitle": job_title,
    }.items():
        if value:
            params[key] = value
    if year is not None:
        params[YEAR_PARAMS[program]] = year
    if received_year is not None:
        params["receivedYear"] = received_year
    # Deferred counting returns results immediately with hasNextPage instead of
    # waiting for an exact total, which is slow (and can be refused) for broad searches.
    if not exact_total:
        params["count"] = "deferred"
    return params


SEARCH_ARGS_DOC = """
    Filters (all optional, combined with AND):
      company: employer name prefix, punctuation/case-insensitive (e.g. "google").
      employer: one exact reported employer name, as it appears in results.
      employer_group: employer identity id (groupId from search_employers) — matches every reported
        spelling and former name of that employer. Preferred for employer research.
      location: employer's city prefix or state (code or name).
      worksite: worksite city prefix or state; with worksite_state, a worksite city prefix only.
      worksite_state: exact worksite state, postal code or name (e.g. "CA", "Texas").
      case_number: case number prefix.
      job_title: job title prefix.
      received_year: year the application was received.
    sort: "event_desc" (newest decision first, default), "event_asc", "received_desc", "received_asc".
    page / limit: 1-based page; limit is capped at 100.
    exact_total: compute totalCount/totalPages (slower for broad searches). By default the response
      returns hasNextPage and totalCount may be null.
    Each case includes EMPLOYER_PROFILE_SLUG for get_employer_profile; pass _id to get_case for all fields.
"""


PWD_CASES_DOC = (
    "Search DOL Prevailing Wage Determination (PWD) cases. Returns wage rate, OES wage level, SOC code, "
    "worksite and dates. determination_year filters by determination date.\n" + SEARCH_ARGS_DOC
)


@mcp.tool(description=PWD_CASES_DOC, annotations=READ_ONLY)
async def search_pwd_cases(
    company: str = "",
    employer: str = "",
    employer_group: str = "",
    location: str = "",
    worksite: str = "",
    worksite_state: str = "",
    case_number: str = "",
    job_title: str = "",
    determination_year: int | None = None,
    received_year: int | None = None,
    sort: CaseSort = "event_desc",
    page: int = 1,
    limit: int = 20,
    exact_total: bool = False,
) -> dict[str, Any]:
    params = _search_params(
        "pwd", company=company, employer=employer, employer_group=employer_group, location=location,
        worksite=worksite, worksite_state=worksite_state, case_number=case_number, job_title=job_title,
        year=determination_year, received_year=received_year, sort=sort, page=page, limit=limit,
        exact_total=exact_total,
    )
    return await _get(SEARCH_PATHS["pwd"], params)



PERM_CASES_DOC = (
    "Search DOL PERM labor certification cases. Returns offered wage range, SOC code, worksite, and the "
    "linked PWD case's determination/expiration dates. decision_year filters by decision date.\n" + SEARCH_ARGS_DOC
)


@mcp.tool(description=PERM_CASES_DOC, annotations=READ_ONLY)
async def search_perm_cases(
    company: str = "",
    employer: str = "",
    employer_group: str = "",
    location: str = "",
    worksite: str = "",
    worksite_state: str = "",
    case_number: str = "",
    job_title: str = "",
    decision_year: int | None = None,
    received_year: int | None = None,
    sort: CaseSort = "event_desc",
    page: int = 1,
    limit: int = 20,
    exact_total: bool = False,
) -> dict[str, Any]:
    params = _search_params(
        "perm", company=company, employer=employer, employer_group=employer_group, location=location,
        worksite=worksite, worksite_state=worksite_state, case_number=case_number, job_title=job_title,
        year=decision_year, received_year=received_year, sort=sort, page=page, limit=limit,
        exact_total=exact_total,
    )
    return await _get(SEARCH_PATHS["perm"], params)



H1B_CASES_DOC = (
    "Search DOL H-1B / H-1B1 / E-3 Labor Condition Application (LCA) cases. Returns wage offered, SOC code, "
    "worksite, worker positions, and employment begin/end dates. decision_year filters by the LCA's last "
    "action date. Extra sorts: \"certification_desc\" / \"certification_asc\" order by original certification "
    "date (distinct from a later withdrawal).\n" + SEARCH_ARGS_DOC
)


@mcp.tool(description=H1B_CASES_DOC, annotations=READ_ONLY)
async def search_h1b_cases(
    company: str = "",
    employer: str = "",
    employer_group: str = "",
    location: str = "",
    worksite: str = "",
    worksite_state: str = "",
    case_number: str = "",
    job_title: str = "",
    decision_year: int | None = None,
    received_year: int | None = None,
    sort: H1bSort = "event_desc",
    page: int = 1,
    limit: int = 20,
    exact_total: bool = False,
) -> dict[str, Any]:
    params = _search_params(
        "h1b", company=company, employer=employer, employer_group=employer_group, location=location,
        worksite=worksite, worksite_state=worksite_state, case_number=case_number, job_title=job_title,
        year=decision_year, received_year=received_year, sort=sort, page=page, limit=limit,
        exact_total=exact_total,
    )
    return await _get(SEARCH_PATHS["h1b"], params)



@mcp.tool(annotations=READ_ONLY)
async def get_case(case_id: str) -> dict[str, Any]:
    """Get every disclosed field for a PWD, PERM, or H-1B case by its _id from search results.

    The response's _PROGRAM says which program the case belongs to.
    """
    return await _get(f"/api/cases/{case_id}")


@mcp.tool(annotations=READ_ONLY)
async def get_search_insights(
    program: Program,
    company: str = "",
    employer: str = "",
    employer_group: str = "",
    location: str = "",
    worksite: str = "",
    worksite_state: str = "",
    case_number: str = "",
    job_title: str = "",
    year: int | None = None,
    received_year: int | None = None,
) -> dict[str, Any]:
    """Summarize all cases matching a search: total count, cases per year, and case outcomes (statuses).

    Takes the same filters as the search tools (year is the determination year for PWD and the decision
    year for PERM/H-1B). Broad searches may be refused as too slow; narrow them with an employer or year.
    """
    params = _search_params(
        program, company=company, employer=employer, employer_group=employer_group, location=location,
        worksite=worksite, worksite_state=worksite_state, case_number=case_number, job_title=job_title,
        year=year, received_year=received_year, sort="event_desc", page=1, limit=20, exact_total=True,
    )
    for key in ("page", "limit", "sort"):
        params.pop(key)
    return await _get(SEARCH_PATHS[program] + "/insights", params)


@mcp.tool(annotations=READ_ONLY)
async def get_available_years(program: Program) -> dict[str, Any]:
    """Return the years with data for a program: "pwd", "perm", or "h1b"."""
    years = await _get(SEARCH_PATHS[program] + "/years")
    return years if isinstance(years, dict) else {"program": program, "years": years}


@mcp.tool(annotations=READ_ONLY)
async def search_employers(query: str) -> dict[str, Any]:
    """Find employers by name (at least 2 characters), ranked by filing volume — up to 8 matches.

    Each employer is an identity that combines its reported spellings (and reviewed former names).
    Returns its groupId (use as employer_group in case searches), slug (for get_employer_profile),
    headquarters location, and filing counts per program.
    """
    return await _get("/api/employers", {"q": query})


@mcp.tool(annotations=READ_ONLY)
async def list_employers(query: str = "", sort: DirectorySort = "h1b_desc", page: int = 1) -> dict[str, Any]:
    """Browse the employer directory, 24 employers per page.

    sort: "h1b_desc" / "perm_desc" / "pwd_desc" (most filings in that program first), "name_asc", "name_desc".
    query optionally restricts to employer names starting with that text. Use hasNextPage to paginate.
    """
    return await _get("/api/employers", {"directory": "1", "q": query, "sort": sort, "page": max(page, 1)})


@mcp.tool(annotations=READ_ONLY)
async def get_employer_profile(slug: str, max_places: int = 15) -> dict[str, Any]:
    """Get an employer's profile by slug (e.g. "google-llc--09621dc6378334b0dd9f4428").

    For each program it filed in (pwd, perm, h1b), summaries include: totalCount, filings per year
    (timeline), statuses, top job titles, employer and worksite locations, wage ranges by pay unit,
    recent cases, and places (states and metro areas with filing counts and median wages, limited to
    the top max_places of each). Also lists the reported names combined into this employer and why.
    If ready is false, the summary is still being computed — retry shortly.
    """
    profile = await _get(f"/api/employers/{slug}")
    if not isinstance(profile, dict) or "error" in profile:
        return profile
    for summary in profile.get("summaries", {}).values():
        # Source-file URLs are bulky and not useful for answering questions.
        summary.pop("sources", None)
        places = summary.get("places")
        if isinstance(places, dict):
            places["states"] = places.get("states", [])[:max_places]
            places["metros"] = [
                {k: v for k, v in metro.items() if k not in ("x", "y")}
                for metro in places.get("metros", [])[:max_places]
            ]
    return profile


@mcp.tool(annotations=READ_ONLY)
async def get_map_options(program: Program = "h1b") -> dict[str, Any]:
    """List the years and occupations (SOC codes with titles and counts) available for get_wage_map."""
    return await _get("/api/map/options", {"program": program})


@mcp.tool(annotations=READ_ONLY)
async def get_wage_map(
    program: Program = "h1b",
    year: int | None = None,
    occupation: str = "",
    max_metros: int = 25,
) -> dict[str, Any]:
    """Geographic breakdown of filings by state and metro area: counts, median annual wage, share of senior
    (level III/IV) wages, and filings per capita.

    year: a fiscal year, or omit for all years. occupation: a 6-digit SOC code like "15-1252"
    (see get_map_options), or omit for all occupations. Metros are sorted by filing count and limited
    to max_metros; all states are returned.
    """
    params: dict[str, Any] = {"program": program, "year": year if year is not None else "all"}
    if occupation:
        params["occupation"] = occupation
    result = await _get("/api/map", params)
    if not isinstance(result, dict) or "error" in result:
        return result
    metros = sorted(result.get("metros", []), key=lambda m: m.get("count", 0), reverse=True)
    result["metros"] = [{k: v for k, v in m.items() if k not in ("x", "y")} for m in metros[:max_metros]]
    return result


if __name__ == "__main__":
    mcp.run()
