# CLAUDE.md

Guidance for AI coding agents working in this repository.

## What this is

A remote MCP server exposing the Google Ads API to MCP-capable AI assistants.
It extends the architecture of Google's official read-only
[googleads/google-ads-mcp](https://github.com/googleads/google-ads-mcp) with
write/management tools and canned reports.

## Safety rules that must not be weakened

These exist because this server can spend money.

- New campaigns and ads are created **PAUSED**. Never change a default to enabled.
- Every write tool must keep its `validate_only` parameter.
- `GOOGLE_ADS_MCP_READ_ONLY=true` must continue to hide every mutation tool.
- A mutate response is not proof of a change. Where a write can be silently
  ignored by the API, read the resource back and surface the real state.

## Conventions

- Tools live in `ads_mcp/tools/`, one module per resource area.
- Account ids are digits only. `utils.normalize_customer_id` strips hyphens.
- Coerce list-typed parameters defensively: some MCP clients deliver arrays as
  JSON strings mid-session.
- Tests use fake account ids. Never commit a real one.
