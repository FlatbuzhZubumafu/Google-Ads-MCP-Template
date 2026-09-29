# Complete Setup Guide

Everything a new user needs to go from zero to an AI assistant managing
Google Ads through this server. Follow the parts in order — each builds
on the previous one.

**The pieces you'll end up with:**

```
Google Ads manager account (MCC)  ──►  developer token
Google Cloud project              ──►  OAuth client + APIs + Cloud Run hosting
This repo deployed on Cloud Run   ──►  your MCP server URL
claude.ai / Claude Code connector ──►  Claude runs your ads
```

---

## Part 1 — Google Ads: manager account and developer token

1. **Create a manager account (MCC)** if you only have a regular ads
   account: [ads.google.com/home/tools/manager-accounts](https://ads.google.com/home/tools/manager-accounts/).
   It's free, holds no ads or billing, and doesn't affect running
   campaigns.
2. **Link your ads account(s) under it**: in the manager account,
   Accounts → Sub-account settings → **+** → *Link existing account* →
   enter the 10-digit customer ID → accept the invite from inside the
   regular account. Do this **before** applying for a token — Google's
   review verifies the advertisers under your manager account.
3. **Apply for the developer token**: from the manager account, open
   the [API Center](https://ads.google.com/aw/apicenter) (Tools &
   Settings → API Center), complete the access form, accept the terms.
   The token string is visible immediately.
4. **Access levels**: a new token may start at "Test account" level
   (works only against test accounts). Request **Basic access** from the
   same page for production use. Reviews can take days; you can test
   against [test accounts](https://developers.google.com/google-ads/api/docs/best-practices/test-accounts)
   while you wait.
5. Note your **manager account ID** — you'll use it as
   `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, **digits only, no dashes**
   (123-456-7890 → 1234567890).

## Part 2 — Google Cloud Console: project, APIs, OAuth client

1. **Create a project** at [console.cloud.google.com](https://console.cloud.google.com)
   (top bar → project picker → New project).
2. **Enable billing** on the project (Billing → Link a billing
   account). Required for Cloud Run's build pipeline even though a small
   server like this typically costs $0–1/month. The deploy fails with
   `Billing account ... not found` without it.
3. **Enable the Google Ads API**: APIs & Services → Library → search
   "Google Ads API" → Enable. (Cloud Run/Cloud Build/Artifact Registry
   get enabled automatically during your first deploy.)
4. **Configure the OAuth consent screen** (APIs & Services → OAuth
   consent screen, a.k.a. Google Auth Platform):
   - User type **External** (or **Internal** if you have Google
     Workspace — that skips verification concerns entirely).
   - App name, support email, developer contact.
   - **Add every user who will connect as a Test user.** Missing this
     causes `access_denied: app is in testing mode` at sign-in.
   - Publishing status: **Testing** is fine to start, but Google expires
     sign-ins/refresh tokens after **7 days** in Testing. Once things
     work, click **Publish app** — you'll get an "unverified app"
     warning at sign-in (click Advanced → continue), but sessions stop
     expiring.
5. **Create the OAuth client**: APIs & Services → Credentials → Create
   credentials → OAuth client ID → type **Web application**.
   - Add redirect URI `http://localhost:8085/` (for the local
     refresh-token script).
   - You'll add the Cloud Run callback URI after Part 3 (chicken-and-egg
     is expected; redirect URIs are editable anytime).
   - Copy the **Client ID** (ends in `.apps.googleusercontent.com`) and
     **Client secret** (starts `GOCSPX-`) — Google shows the secret only
     at creation.

## Part 3 — Deploy the server to Cloud Run

Run from a machine with `gcloud` (or [Cloud Shell](https://shell.cloud.google.com),
which has it preinstalled and authenticated):

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

git clone https://github.com/FlatbuzhZubumafu/google-ads-mcp-template.git
cd Google-Ads-MCP

gcloud run deploy google-ads-mcp --source . --region us-central1 --allow-unauthenticated --set-env-vars GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_DEV_TOKEN,GOOGLE_ADS_MCP_OAUTH_CLIENT_ID=YOUR_CLIENT_ID,GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET=YOUR_CLIENT_SECRET,GOOGLE_ADS_LOGIN_CUSTOMER_ID=YOUR_MCC_ID_DIGITS_ONLY
```

**Replace all four `YOUR_*` values with real ones** — deploying with the
placeholder text is the most common setup mistake, and it fails later
(at Google sign-in) rather than at deploy time.

After the deploy prints your service URL
(`https://google-ads-mcp-XXXX.REGION.run.app`):

```bash
gcloud run services update google-ads-mcp --region us-central1 --update-env-vars GOOGLE_ADS_MCP_BASE_URL=https://YOUR_SERVICE_URL
```

Then back in the Cloud Console, add the callback to your OAuth client's
**Authorized redirect URIs**:

```
https://YOUR_SERVICE_URL/auth/callback
```

**Verify** from any machine — this must return JSON whose URLs all point
at your service URL (not localhost):

```bash
curl -s https://YOUR_SERVICE_URL/.well-known/oauth-authorization-server
```

## Part 4 — Connect your AI assistant

**claude.ai (web/mobile/desktop):** Settings → Connectors → Add custom
connector → `https://YOUR_SERVICE_URL/mcp` → complete the Google
sign-in. Then ask Claude: *"List my accessible Google Ads customers."*

**Claude Code:** add the server directly:

```bash
claude mcp add --transport http google-ads https://YOUR_SERVICE_URL/mcp
```

## Troubleshooting — errors we've actually hit

| Symptom | Cause | Fix |
|---|---|---|
| `The [project] resource is not properly specified` | gcloud has no default project | `gcloud config set project YOUR_PROJECT_ID` |
| `Billing account ... is not found` on deploy | No billing account linked | Console → Billing → link one (Part 2.2) |
| `Build failed ... default service account is missing required IAM permissions` | Newer projects don't grant Cloud Build perms automatically | `gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com --role=roles/cloudbuild.builds.builder`, wait ~1 min, redeploy |
| `zsh: command not found: --set-env-vars` | A backslash line-continuation got lost when editing a multi-line command | Use the single-line deploy command above |
| HTTP **403 Forbidden** (Google HTML page) on any server URL | Public access never applied | Console → Cloud Run → service → Security tab → **Allow unauthenticated invocations** → Save |
| Connector: "Couldn't register with sign-in service" | Server unreachable (403 above) or `GOOGLE_ADS_MCP_BASE_URL` unset/localhost | Fix reachability, set base URL, verify the `.well-known` JSON, delete + re-add the connector |
| Google sign-in: **Error 401: invalid_client** | Client ID env var is wrong — placeholder text, truncated, or ID/secret swapped | Console → Cloud Run → Edit & deploy new revision → Variables & Secrets → paste the real values → Deploy |
| Sign-in: `access_denied — app is in testing mode` | Your Google account isn't a Test user | Consent screen → Test users → add it |
| Sign-in: `redirect_uri_mismatch` | Callback URI missing or mistyped on the OAuth client | Add `https://YOUR_SERVICE_URL/auth/callback` exactly |
| Connector works, then breaks after ~a week | Consent screen still in Testing (7-day expiry) | Publish the app (Part 2.4) |
| API error mentioning the developer token / test accounts | Token not yet approved for Basic access | Wait for review; use test accounts meanwhile |
| `gcloud crashed ... unsupported operand type(s) for \|` | gcloud running under Python ≤3.9 | Point `CLOUDSDK_PYTHON` at Python 3.10+ (e.g. `brew install python@3.12`) or reinstall gcloud |

## Optional hardening

- Move `GOOGLE_ADS_DEVELOPER_TOKEN` and
  `GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET` into Secret Manager and reference
  them with `--set-secrets` instead of `--set-env-vars`.
- Set `GOOGLE_ADS_MCP_READ_ONLY=true` for monitoring-only deployments.
- Publish the OAuth consent screen so sessions don't expire weekly.
