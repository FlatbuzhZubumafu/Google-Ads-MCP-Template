# Google Ads MCP Server (template)

**A starting point you are meant to fork.** Google's official
[googleads/google-ads-mcp](https://github.com/googleads/google-ads-mcp) is
read-only and ships three tools. This template keeps that architecture and adds
the write and reporting tools you need to actually manage an account, so you can
clone it, point it at your own Google Cloud project, and cut it down to the
tools your team should be allowed to call.

Start with the [Complete Setup Guide](docs/SETUP.md), then delete what you do
not need from `ads_mcp/tools/`.

> Set `GOOGLE_ADS_MCP_READ_ONLY=true` if you want the official server's
> read-only behaviour with this server's reporting tools.

---


A remote [MCP](https://modelcontextprotocol.io) server that lets Claude (and any other MCP-capable AI assistant) **monitor and manage your Google Ads accounts**: pull performance reports, run arbitrary GAQL queries, adjust budgets, pause/enable campaigns, add keywords and negative keywords, and create new campaigns and ads.

Built on the architecture of Google's official read-only [googleads/google-ads-mcp](https://github.com/googleads/google-ads-mcp) server, extended with write/management tools and canned reports for routine (e.g. weekly) account reviews.

## Tools

### Monitoring (read-only)

| Tool | What it does |
|---|---|
| `list_accessible_customers` | Account IDs the authenticated user can access |
| `get_account_hierarchy` | Client accounts under a manager (MCC) account |
| `get_campaign_performance` | Campaign metrics + status, budget, bidding strategy |
| `get_ad_group_performance` | Ad group metrics |
| `get_keyword_performance` | Keyword metrics incl. quality score |
| `get_search_terms_report` | Actual user queries — the input for negative keyword mining |
| `get_change_history` | Who/what changed in the account recently |
| `search` | Arbitrary GAQL query against any Google Ads resource |
| `get_resource_metadata` | Field discovery for building `search` queries |
| `list_conversion_actions` | Audit what Smart Bidding optimizes toward |
| `list_campaign_criteria` | Audit a campaign's geo/schedule/device targeting |
| `suggest_geo_targets` | Resolve place names to geo target IDs |

All report tools accept predefined ranges (`LAST_7_DAYS`, `LAST_30_DAYS`, `LAST_MONTH`, …) or custom `start_date`/`end_date`.

### Management (write)

| Tool | What it does |
|---|---|
| `create_campaign_budget` / `update_campaign_budget` | Create or resize daily budgets |
| `create_campaign` | New Search/Display campaign — **always created PAUSED** |
| `set_campaign_status` | Pause / enable / remove a campaign |
| `create_ad_group` / `update_ad_group` | Create ad groups, change status or default CPC bid |
| `create_responsive_search_ad` | New RSA — **always created PAUSED** |
| `set_ad_status` | Pause / enable / remove an ad |
| `add_keywords` / `set_keyword_status` | Add or pause/enable/remove keywords |
| `add_negative_keywords` | Campaign-level negative keywords |
| `set_conversion_action_primary` | Promote/demote what bidding optimizes toward |
| `add_location_targeting` / `remove_campaign_criterion` | Manage geo targeting |
| `set_ad_schedule` | Restrict ads to staffed hours |
| `create_call_asset` / `link_asset_to_campaign` | Phone numbers on ads |
| `set_campaign_target_cpa` | Set target CPA on Maximize Conversions campaigns |

Safety rails:

- Every write tool takes `validate_only=true` to preview a change without applying it.
- New campaigns and ads are always created **paused** so nothing spends money before you review it.
- Set `GOOGLE_ADS_MCP_READ_ONLY=true` to hide all write tools entirely (monitoring-only deployments).

> **New user?** Follow the step-by-step **[Complete Setup Guide](docs/SETUP.md)** — it covers the Google Ads manager account, developer token, the whole Google Cloud Console setup (project, billing, APIs, OAuth consent screen and client), Cloud Run deployment, connecting claude.ai, and a troubleshooting table of real-world errors.

## Prerequisites

1. **A Google Ads developer token** — in a Google Ads *manager* account, go to **Tools & Settings → Setup → API Center** ([direct link](https://ads.google.com/aw/apicenter)) and apply for a token. A "Basic" access token is enough for managing your own accounts. ([docs](https://developers.google.com/google-ads/api/docs/get-started/dev-token))

   > **Only have a regular (non-manager) account?** The API Center is exclusive to manager accounts (MCC). Create a free one at [ads.google.com/home/tools/manager-accounts](https://ads.google.com/home/tools/manager-accounts/) — it's just an umbrella account with no ads or billing of its own — then link your existing account under it (Accounts → Sub-account settings → **+** → Link existing account) *before* applying, since Google's token review verifies the advertiser accounts beneath the manager. If the token is initially granted at "Test account" level, request Basic access from the same API Center page, and set `GOOGLE_ADS_LOGIN_CUSTOMER_ID` to the manager account's ID when running this server.
2. **A Google Cloud project with an OAuth 2.0 client** — in [Google Cloud Console](https://console.cloud.google.com/apis/credentials), create an OAuth client. Add your Google account as a test user on the consent screen (or publish the app) and include the scope `https://www.googleapis.com/auth/adwords`. ([docs](https://developers.google.com/google-ads/api/docs/oauth/cloud-project))

## Option 1 — Remote server for claude.ai (recommended)

This is the setup that lets claude.ai (web/mobile/desktop) connect as a **custom connector**, with each user signing in with their own Google account.

### Deploy to Cloud Run

```bash
gcloud run deploy google-ads-mcp \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_DEV_TOKEN" \
  --set-env-vars "GOOGLE_ADS_MCP_OAUTH_CLIENT_ID=YOUR_CLIENT_ID" \
  --set-env-vars "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET=YOUR_CLIENT_SECRET" \
  --set-env-vars "GOOGLE_ADS_MCP_BASE_URL=https://PLACEHOLDER"
```

Then take the service URL Cloud Run prints (e.g. `https://google-ads-mcp-xxxx-uc.a.run.app`) and:

1. Re-deploy (or update the env var) with `GOOGLE_ADS_MCP_BASE_URL` set to that URL.
2. In Google Cloud Console, add `https://YOUR_SERVICE_URL/auth/callback` to the OAuth client's **Authorized redirect URIs**.

> `--allow-unauthenticated` is required so the MCP client can reach the endpoint; actual access is protected by the Google OAuth flow the server enforces. If you use a manager account, also set `GOOGLE_ADS_LOGIN_CUSTOMER_ID`.

### Connect claude.ai

1. claude.ai → **Settings → Connectors → Add custom connector**.
2. URL: `https://YOUR_SERVICE_URL/mcp`.
3. Claude will walk you through the Google sign-in; grant the Google Ads scope.

Any other MCP client that supports streamable HTTP + OAuth (Claude Code, ChatGPT connectors, etc.) can connect the same way.

## Option 2 — Local (stdio) for Claude Code / Claude Desktop

No deployment needed; credentials come from your environment.

```bash
pipx run --spec git+https://github.com/FlatbuzhZubumafu/google-ads-mcp-template.git google-ads-mcp
```

Claude Code registration:

```bash
claude mcp add google-ads \
  -e GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_DEV_TOKEN \
  -e GOOGLE_ADS_LOGIN_CUSTOMER_ID=YOUR_MCC_ID \
  -- pipx run --spec git+https://github.com/FlatbuzhZubumafu/google-ads-mcp-template.git google-ads-mcp
```

Credentials are resolved in this order:

1. **OAuth token of the connected user** (remote mode above).
2. **Refresh token env vars**: `GOOGLE_ADS_OAUTH_CLIENT_ID`, `GOOGLE_ADS_OAUTH_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`.
3. **Application Default Credentials**:
   ```bash
   gcloud auth application-default login \
     --scopes=https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform
   ```

See [.env.example](.env.example) for every variable.

## Running your ads on a weekly cadence

A workflow that works well once connected — save it as a project instruction or scheduled prompt for Claude:

1. `get_campaign_performance` (`LAST_7_DAYS` vs the previous week) — spot cost/conversion swings.
2. `get_search_terms_report` — find wasted spend; propose negatives.
3. `get_keyword_performance` — flag low quality scores and zero-conversion spenders.
4. `get_change_history` — review everything that changed last week.
5. Apply agreed changes (`add_negative_keywords`, `update_campaign_budget`, `set_campaign_status`, …) — using `validate_only=true` first, then for real after your confirmation.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

Run locally over HTTP without OAuth (trusted networks only):

```bash
GOOGLE_ADS_MCP_TRANSPORT=http GOOGLE_ADS_DEVELOPER_TOKEN=... .venv/bin/google-ads-mcp
```

## Disclaimer

This server can spend and modify real money in your ad accounts. Review what your AI assistant proposes — especially budget changes and status changes — and prefer `validate_only` previews plus read-only mode wherever write access isn't needed. This is not an official Google product; portions are derived from [googleads/google-ads-mcp](https://github.com/googleads/google-ads-mcp) (Apache 2.0).
