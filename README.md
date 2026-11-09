# LaborLens MCP

An MCP (Model Context Protocol) server that exposes [LaborLens](https://laborlens.fyi) — a U.S. Department of Labor prevailing wage (PWD), PERM labor certification, and H-1B LCA search tool — as tools for Claude and other MCP-compatible AI assistants.

![LaborLens MCP in action](screenshot.png)

## Tools

| Tool | Description |
|---|---|
| `search_pwd_cases` | Search PWD cases |
| `search_perm_cases` | Search PERM labor certification cases (includes linked PWD dates) |
| `search_h1b_cases` | Search H-1B / H-1B1 / E-3 Labor Condition Applications |
| `get_case` | Fetch every disclosed field for a PWD, PERM, or H-1B case by its ID |
| `get_search_insights` | Totals, cases per year, and outcomes for any search |
| `get_available_years` | Years with data for a program |
| `search_employers` | Find employers by name, ranked by filing volume |
| `list_employers` | Browse the employer directory sorted by filings or name |
| `get_employer_profile` | Employer summary: filings per year, top jobs, wages, worksites, metros, combined names |
| `get_map_options` | Years and occupations available for the wage map |
| `get_wage_map` | Filings and median wages by state and metro area, per year and occupation |

All three case searches accept the same filters: employer name prefix (`company`), exact reported name (`employer`), employer identity (`employer_group`, the `groupId` from `search_employers` — covers every spelling and former name), employer `location`, `worksite` / `worksite_state`, `case_number`, `job_title`, decision/determination year, `received_year`, plus `sort` and pagination. By default results return immediately with `hasNextPage`; pass `exact_total: true` for `totalCount`.

## Requirements

- Python 3.15+
- [uv](https://docs.astral.sh/uv/)
- `mcp` Python SDK 2.x (uses `MCPServer`, formerly `FastMCP`)

## Setup

```bash
git clone https://github.com/blueandhack/LaborLens-MCP
cd LaborLens-MCP
uv sync
```

## Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "laborlens": {
      "command": "/opt/homebrew/bin/uv",
      "args": ["run", "--directory", "/path/to/LaborLens-MCP", "python", "server.py"],
      "env": {
        "LABORLENS_URL": "https://laborlens.fyi"
      }
    }
  }
}
```

Restart Claude Desktop after saving.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LABORLENS_URL` | `https://laborlens.fyi` | Base URL of the LaborLens API |

## Data Source

Data comes from the [U.S. Department of Labor](https://www.dol.gov/agencies/eta/foreign-labor/performance) OFLC Performance Data disclosure files.
