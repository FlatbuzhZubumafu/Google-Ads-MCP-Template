"""Declares the singleton FastMCP instance shared by all tool modules.

Tool modules register themselves against this instance with `@mcp.tool`
annotations, so importing a tool module is what makes its tools available.

Authentication modes for the MCP endpoint itself:

1. Google OAuth (recommended for remote deployments): set
   GOOGLE_ADS_MCP_OAUTH_CLIENT_ID and GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET.
   Every connecting user signs in with their own Google account and their
   token is used for Google Ads API calls. This is what claude.ai custom
   connectors expect.

2. No endpoint auth (local stdio use): leave the OAuth variables unset and
   provide Google Ads credentials via GOOGLE_ADS_REFRESH_TOKEN /
   Application Default Credentials instead. Never expose this mode on a
   public network.
"""

import os

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware

ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


class LoginCustomerMiddleware(Middleware):
    """Tells the Google Ads client which account each tool call targets.

    Without this, every request carries the single GOOGLE_ADS_LOGIN_CUSTOMER_ID
    from the environment. That breaks any account the user can access directly
    rather than through that manager: Google answers "User doesn't have
    permission to access customer" even though the user is an admin on it.

    Reading customer_id off the in-flight call lets utils.resolve_login_
    customer_id() decide per account, so one deployment can address both
    manager-mediated and standalone accounts.
    """

    async def on_call_tool(self, context, call_next):
        import ads_mcp.utils as utils

        args = getattr(context.message, "arguments", None) or {}
        customer_id = args.get("customer_id")
        utils.set_target_customer_id(
            customer_id if isinstance(customer_id, str) else None
        )
        try:
            return await call_next(context)
        finally:
            utils.set_target_customer_id(None)


def _build_auth():
    client_id = os.environ.get("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET")
    if not (client_id and client_secret):
        return None

    from fastmcp.server.auth.providers.google import GoogleProvider

    base_url = os.environ.get(
        "GOOGLE_ADS_MCP_BASE_URL", "http://localhost:8080"
    )
    return GoogleProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            ADS_SCOPE,
        ],
    )


mcp = FastMCP("Google Ads", auth=_build_auth())
mcp.add_middleware(LoginCustomerMiddleware())
